from __future__ import annotations
import json
import re
from anthropic import AsyncAnthropic
from config import get_settings
from chat.prompts import get_system_prompt
from tools.search import search_listings, search_jobs
from tools.knowledge import search_knowledge_base
from tools.geocoding import geocode_location


# Map frontend type values to our internal page_type for prompts
FRONTEND_TYPE_TO_PAGE = {
    "CAREHOME": "care_homes",
    "NURSERY": "nurseries",
    "HOMECARE": "home_care",
    "JOBS": "jobs",
}


TOOLS_LISTINGS = [
    {
        "name": "search_listings",
        "description": (
            "Search the Caretopia database for care providers. "
            "IMPORTANT: Do NOT call this tool until you have gathered: (1) a location, "
            "(2) who the care is for, and (3) at least one specific need or preference. "
            "If any of these are missing, ask the user first. Never call on greetings "
            "or vague messages. The location will be geocoded automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location name or postcode to search near.",
                },
                "radius_km": {
                    "type": "number",
                    "description": "Search radius in kilometres. Default 25.",
                    "default": 25,
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CRITICAL: Must include ALL conditions, specialisms, preferences, and requirements mentioned ANYWHERE in the entire conversation history — not just the latest message. Re-read every user message and collect every criterion. Example: if user mentioned 'dementia' earlier and now says 'garden', pass BOTH ['dementia', 'garden']. Never drop previous keywords.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return. Default 8.",
                    "default": 8,
                },
            },
            "required": ["location"],
        },
    },
]

TOOLS_JOBS = [
    {
        "name": "search_jobs",
        "description": (
            "Search the Caretopia jobs database for care sector jobs. "
            "Use this when the user wants to find a job — at minimum a location. "
            "The location will be geocoded automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location name or postcode to search near.",
                },
                "radius_km": {
                    "type": "number",
                    "description": "Search radius in kilometres. Default 25.",
                    "default": 25,
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Job role, title, or skill keywords (e.g. 'nurse', 'care assistant', 'support worker').",
                },
                "job_type": {
                    "type": "string",
                    "enum": ["FULLTIME", "PARTTIME", "TEMPORARY", "CONTRACT", "FLEXIBLE", "INTERNSHIP"],
                    "description": "Filter by job type.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return. Default 8.",
                    "default": 8,
                },
            },
            "required": ["location"],
        },
    },
]

TOOL_KNOWLEDGE = {
    "name": "search_knowledge_base",
    "description": (
        "Search the knowledge base for general care information — funding, "
        "conditions, organisations, charities, processes. Use for informational "
        "queries, NOT for finding specific providers."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The information query (e.g. 'how does care home funding work?').",
            },
        },
        "required": ["query"],
    },
}


def get_tools(frontend_type: str) -> list[dict]:
    """Return the appropriate tool set for the page type."""
    if frontend_type == "JOBS":
        return TOOLS_JOBS + [TOOL_KNOWLEDGE]
    return TOOLS_LISTINGS + [TOOL_KNOWLEDGE]


# Negative responses that clearly decline funding info
_NEGATIVE_PATTERNS = re.compile(
    r"^\s*(no|nah|nope|skip|no thanks|no thank you|just show|show me|"
    r"don\'t need|not interested|not right now|maybe later|"
    r"just search|just find|go ahead and search|search for)\b",
    re.IGNORECASE,
)


def _last_assistant_offered_funding(messages: list[dict]) -> bool:
    """Check if the last assistant message ASKED the funding question.

    Only triggers on the offer/question (contains "would you like" AND "funding"),
    NOT on the answer (contains funding info but no "would you like").
    """
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg.get("content", "")
            # Handle content that is a list of blocks (from API responses)
            if isinstance(content, list):
                text = " ".join(
                    getattr(block, "text", "") if hasattr(block, "text")
                    else block.get("text", "") if isinstance(block, dict)
                    else ""
                    for block in content
                )
            elif isinstance(content, str):
                text = content
            else:
                return False
            text_lower = text.lower()
            return "would you like" in text_lower and "funding" in text_lower
    return False


def _user_declined_funding(message: str) -> bool:
    """Check if the user explicitly declined funding info.

    Default assumption: if the user didn't clearly say no, treat it as yes.
    This is the inverse approach — block search unless user clearly declines.
    """
    return bool(_NEGATIVE_PATTERNS.search(message.strip()))


# Words that indicate "who" the care is for — relationship terms, self-references
HEALTH_CONDITIONS = [
    "dementia", "alzheimer", "mobility", "stroke", "parkinson",
    "arthritis", "disability", "wheelchair", "frail", "blind", "deaf",
    "autism", "adhd", "sen", "cancer", "diabetes", "incontinence",
    "depression", "anxiety", "mental health", "learning difficult",
]


WHO_INDICATORS = [
    # Family relationships
    "mum", "mom", "mother", "dad", "father", "parent", "parents",
    "nan", "nana", "nanny", "grandmother", "grandma", "grandad",
    "grandfather", "grandpa", "gran",
    "son", "daughter", "child", "children", "kid", "kids", "baby",
    "toddler", "boy", "girl",
    "wife", "husband", "partner", "spouse",
    "brother", "sister", "sibling",
    "uncle", "aunt", "auntie",
    "friend", "neighbour", "neighbor",
    # Self-references
    "myself", "i need care", "i'm looking for care for me",
    # Generic person references
    "year old", "years old", "yo ",
    "elderly", "loved one",
    # Possessive patterns that imply who
    "my ",  # "my mum", "my daughter", etc.
    "our ",  # "our mother"
]


def _conversation_mentions_who(messages: list[dict]) -> bool:
    """Check if any message in the conversation mentions who the care is for."""
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        text = content.lower()
        for indicator in WHO_INDICATORS:
            if indicator in text:
                return True
    return False


def _message_mentions_condition(message: str) -> bool:
    """Check if the user's message mentions a health condition."""
    text = message.lower()
    return any(cond in text for cond in HEALTH_CONDITIONS)


WELLBEING_CHECKIN = (
    "\n\nAnd how are you doing? Looking for care can be stressful "
    "— make sure you're looking after yourself too."
)


class ConversationEngine:
    def __init__(self, frontend_type: str):
        """
        Args:
            frontend_type: 'CAREHOME', 'NURSERY', or 'HOMECARE' (from frontend).
        """
        settings = get_settings()
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.fliss_model
        self.frontend_type = frontend_type
        page_type = FRONTEND_TYPE_TO_PAGE.get(frontend_type, "care_homes")
        self.system_prompt = get_system_prompt(page_type)
        self.tools = get_tools(frontend_type)

    async def chat(
        self, message: str, conversation_history: list[dict]
    ) -> dict:
        """Process a user message and return frontend-compatible response.

        Args:
            message: The user's new message.
            conversation_history: Previous messages in [{role, content}, ...] format.

        Returns:
            {
                "intent": str,
                "confidence": float,
                "answer": str,
                "results": list,
                "title": str,
                "center_lat": float | None,
                "center_lng": float | None,
            }
        """
        # Build messages for the API, injecting search context from
        # previous turns into user messages (not assistant messages) so the
        # model has cumulative criteria but never echoes the metadata.
        messages = []
        search_context = None
        for msg in conversation_history:
            content = msg["content"]
            if msg["role"] == "user" and search_context:
                content = (
                    f"[Search context for cumulative criteria — DO NOT repeat "
                    f"this text to the user: {search_context}]\n\n{content}"
                )
                search_context = None
            messages.append({"role": msg["role"], "content": content})
            # Pick up search metadata stored by main.py for the next turn
            if msg.get("filters_used"):
                f = msg["filters_used"]
                loc = f.get("location", "")
                kw = ", ".join(f.get("keywords", []))
                rad = f.get("radius_km", 25)
                search_context = f"location={loc}, keywords={kw}, radius={rad}km"

        # If the last assistant message had filters, attach context to current message
        current_content = message
        if search_context:
            current_content = (
                f"[Search context for cumulative criteria — DO NOT repeat "
                f"this text to the user: {search_context}]\n\n{message}"
            )
        messages.append({"role": "user", "content": current_content})

        # --- Funding state tracker (hard block) ---
        # If the last assistant message mentioned "funding" and the user
        # did NOT clearly decline, remove search tools so the AI physically
        # cannot search. Any response that isn't an explicit "no/skip" is
        # treated as wanting funding info. This is intentionally aggressive
        # because the AI was ignoring prompt-level instructions ~50% of the time.
        awaiting_funding = _last_assistant_offered_funding(messages)
        if awaiting_funding and not _user_declined_funding(message):
            # Strip search tools — only keep knowledge base tool
            turn_tools = [t for t in self.tools if t["name"] == "search_knowledge_base"]
            # Inject a system-level nudge so the model knows what to do
            funding_nudge = (
                "[SYSTEM: The user has asked for funding information. You MUST "
                "provide funding details from the FUNDING INFORMATION section in "
                "your instructions. Do NOT search for listings. Give them the "
                "funding guidance first, then ask if they are ready to see care options.]"
            )
            messages[-1] = {
                "role": "user",
                "content": f"{funding_nudge}\n\n{current_content}",
            }
        else:
            turn_tools = self.tools

        search_performed = False
        filters_used = None
        listings_results = []
        center_lat = None
        center_lng = None

        # Tool-calling loop
        while True:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=turn_tools,
                messages=messages,
            )

            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        if block.name == "search_listings":
                            # GUARD: Block search if "who" hasn't been mentioned
                            if not _conversation_mentions_who(messages):
                                result_json = json.dumps({
                                    "error": "BLOCKED: Cannot search yet. You must first ask the user who the care is for. Ask a clarifying question like 'And who are you looking for care for?' before searching.",
                                    "action": "ask_who",
                                })
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result_json,
                                })
                                continue
                            result_json, raw_results, geo = await self._handle_search(block.input)
                            search_performed = True
                            listings_results = raw_results
                            filters_used = {
                                "location": block.input.get("location"),
                                "keywords": block.input.get("keywords", []),
                                "radius_km": block.input.get("radius_km", 25),
                            }
                            if geo:
                                center_lat = geo["latitude"]
                                center_lng = geo["longitude"]
                        elif block.name == "search_jobs":
                            result_json, raw_results, geo = await self._handle_job_search(block.input)
                            search_performed = True
                            listings_results = raw_results
                            filters_used = {
                                "location": block.input.get("location"),
                                "keywords": block.input.get("keywords", []),
                                "radius_km": block.input.get("radius_km", 25),
                            }
                            if geo:
                                center_lat = geo["latitude"]
                                center_lng = geo["longitude"]
                        elif block.name == "search_knowledge_base":
                            results = await search_knowledge_base(query=block.input["query"])
                            result_json = json.dumps(results, default=str)
                        else:
                            result_json = json.dumps({"error": f"Unknown tool: {block.name}"})

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_json,
                        })

                messages.append({"role": "user", "content": tool_results})
                # After processing tool results, restore full tools for
                # any subsequent iterations (e.g. knowledge base follow-up)
                turn_tools = self.tools
            else:
                # Extract final text
                text_parts = [
                    block.text for block in assistant_content if block.type == "text"
                ]
                answer = "\n".join(text_parts)

                # --- RULE 1: Condition acknowledgement guard ---
                # If the user mentioned a health condition but the AI
                # skipped straight to the funding question, block the
                # response and force the AI to acknowledge the condition
                # first.
                if (
                    _message_mentions_condition(message)
                    and "would you like" in answer.lower()
                    and "funding" in answer.lower()
                ):
                    condition_nudge = (
                        "[SYSTEM: The user just mentioned a health condition. "
                        "You MUST first acknowledge their condition with 2-3 "
                        "helpful sentences about what to look for in care for "
                        "that condition. Do NOT ask about funding yet. Respond "
                        "about their condition first, then in your NEXT message "
                        "ask about funding.]"
                    )
                    # Strip search tools so AI focuses on the condition
                    turn_tools = [
                        t for t in self.tools
                        if t["name"] == "search_knowledge_base"
                    ]
                    # Replace last assistant message with nothing (discard)
                    messages.pop()
                    # Re-inject the user message with the condition nudge
                    messages[-1] = {
                        "role": "user",
                        "content": f"{condition_nudge}\n\n{current_content}",
                    }
                    continue  # Re-run the API call

                # Auto-recovery: if AI wrote results-like text without calling
                # the search tool, extract location and force a search so the
                # frontend gets listing cards to display.
                if not search_performed and any(
                    phrase in answer.lower()
                    for phrase in [
                        "take a look at the options",
                        "here are some",
                        "i've found some",
                        "i found some",
                        "check out the options",
                        "options below",
                    ]
                ):
                    location = self._extract_location_from_history(messages)
                    if location:
                        import logging
                        logging.warning(
                            f"[Fliss] AI wrote results text without calling search tool. "
                            f"Auto-recovering with location={location}, type={self.frontend_type}"
                        )
                        keywords = self._extract_keywords_from_history(messages)
                        tool_input = {"location": location, "keywords": keywords, "limit": 8}
                        result_json, raw_results, geo = await self._handle_search(tool_input)
                        if raw_results:
                            search_performed = True
                            listings_results = raw_results
                            filters_used = {
                                "location": location,
                                "keywords": keywords,
                                "radius_km": 25,
                            }
                            if geo:
                                center_lat = geo["latitude"]
                                center_lng = geo["longitude"]

                # --- RULE 2: Wellbeing check-in after results ---
                if search_performed:
                    answer += WELLBEING_CHECKIN

                # Determine intent (matching existing system's values)
                if search_performed:
                    intent = "listings"
                    confidence = 1.0
                elif any(kw in answer.lower() for kw in [
                    "funding", "organisation", "charity", "cqc", "ofsted",
                    "allowance", "nhs", "council", "salary", "interview",
                ]):
                    intent = "info"
                    confidence = 0.9
                else:
                    intent = "clarify"
                    confidence = 0.8

                # Build title
                if search_performed and filters_used:
                    location = filters_used.get("location", "")
                    if self.frontend_type == "JOBS":
                        title = f"Jobs near {location}" if location else "Job results"
                    else:
                        title = f"Results near {location}" if location else "Search results"
                else:
                    title = ""

                return {
                    "intent": intent,
                    "confidence": confidence,
                    "answer": answer,
                    "results": listings_results,
                    "title": title,
                    "center_lat": center_lat,
                    "center_lng": center_lng,
                    "filters_used": filters_used,
                }

    def _extract_location_from_history(self, messages: list[dict]) -> str | None:
        """Extract the most recent location from conversation history.

        Checks filters_used from previous searches first, then falls back
        to the search context injected into user messages.
        """
        # Check if a previous search had a location in filters_used
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                filters = msg.get("filters_used")
                if filters and filters.get("location"):
                    return filters["location"]
        # Fall back to search context metadata injected into user messages
        for msg in messages:
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue
            # Look for location in search context
            match = re.search(r'"location":\s*"([^"]+)"', content)
            if match:
                return match.group(1)
        return None

    def _extract_keywords_from_history(self, messages: list[dict]) -> list[str]:
        """Extract keywords from conversation history."""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                filters = msg.get("filters_used")
                if filters and filters.get("keywords"):
                    return filters["keywords"]
        return []

    async def _handle_search(self, tool_input: dict) -> tuple:
        """Execute search_listings with location-first fallback.

        Strategy:
        1. Try search with keywords if provided
        2. If keywords return 0 results, retry with location only
        3. Flag whether keyword filtering was applied or fell back

        Returns (json_str, raw_results, geo_dict).
        """
        location = tool_input["location"]
        geo = await geocode_location(location)

        latitude = geo["latitude"] if geo else None
        longitude = geo["longitude"] if geo else None

        # Default 25km radius — if nothing found, prompt user to expand
        radius = tool_input.get("radius_km", 25)
        keywords = tool_input.get("keywords")
        limit = tool_input.get("limit", 8)

        # First try: with keywords (if any)
        results = await search_listings(
            page_type=self.frontend_type,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius,
            keywords=keywords,
            limit=limit,
        )

        keyword_match = True

        # Fallback: if keywords returned nothing, retry location-only
        if not results and keywords:
            keyword_match = False
            results = await search_listings(
                page_type=self.frontend_type,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius,
                keywords=None,
                limit=limit,
            )

        # Build response JSON with metadata about the search
        response_data = {
            "results": results,
            "keyword_match": keyword_match,
            "keywords_requested": keywords or [],
            "location": location,
            "result_count": len(results),
        }

        return json.dumps(response_data, default=str), results, geo

    async def _handle_job_search(self, tool_input: dict) -> tuple:
        """Execute search_jobs with keyword fallback.

        Returns (json_str, raw_results, geo_dict).
        """
        location = tool_input["location"]
        geo = await geocode_location(location)

        latitude = geo["latitude"] if geo else None
        longitude = geo["longitude"] if geo else None

        radius = tool_input.get("radius_km", 25)
        keywords = tool_input.get("keywords")
        job_type = tool_input.get("job_type")
        limit = tool_input.get("limit", 8)

        # First try: with keywords (if any)
        results = await search_jobs(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius,
            keywords=keywords,
            job_type=job_type,
            limit=limit,
        )

        keyword_match = True

        # Fallback: if keywords returned nothing, retry location-only
        if not results and keywords:
            keyword_match = False
            results = await search_jobs(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius,
                keywords=None,
                job_type=job_type,
                limit=limit,
            )

        response_data = {
            "results": results,
            "keyword_match": keyword_match,
            "keywords_requested": keywords or [],
            "location": location,
            "result_count": len(results),
        }

        return json.dumps(response_data, default=str), results, geo
