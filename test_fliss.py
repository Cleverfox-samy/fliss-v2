"""
Fliss v2 — Automated Test Suite
Runs against the live server at http://localhost:8000/api/query
"""
from __future__ import annotations
import httpx
import uuid
import sys
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 90


def send(query: str, page_type: str = "CAREHOME", session_id: str | None = None) -> dict:
    """Send a query to the Fliss API."""
    if session_id is None:
        session_id = str(uuid.uuid4())
    r = httpx.post(
        f"{BASE_URL}/api/query",
        json={
            "query": query,
            "mode": "text",
            "context": {"session_id": session_id},
            "type": page_type,
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def send_conversation(messages: list[str], page_type: str = "CAREHOME") -> list[dict]:
    """Send a multi-turn conversation, returning all responses."""
    sid = str(uuid.uuid4())
    responses = []
    for msg in messages:
        resp = send(msg, page_type, session_id=sid)
        responses.append(resp)
    return responses


def check(text: str, *terms: str, case_sensitive: bool = False) -> bool:
    """Check if ALL terms appear in text."""
    t = text if case_sensitive else text.lower()
    return all((term if case_sensitive else term.lower()) in t for term in terms)


def check_any(text: str, *terms: str) -> bool:
    """Check if ANY term appears in text."""
    t = text.lower()
    return any(term.lower() in t for term in terms)


def check_none(text: str, *terms: str) -> bool:
    """Check that NONE of the terms appear in text."""
    t = text.lower()
    return not any(term.lower() in t for term in terms)


# ── Test definitions ─────────────────────────────────────────────────────────

results_table: list[dict] = []


def record(name: str, input_text: str, expected: str, passed: bool, actual: str):
    results_table.append({
        "name": name,
        "input": input_text[:60],
        "expected": expected,
        "passed": passed,
        "actual": actual[:120],
    })
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if not passed:
        print(f"         Expected: {expected}")
        print(f"         Actual:   {actual[:200]}")


# ═══════════════════════════════════════════════════════════════════════════════
# GREETING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_greeting_hello():
    d = send("hello")
    passed = check(d["answer"], "fliss") and d["intent"] == "clarify"
    record("greeting_hello", "hello", "Introduces as Fliss, intent=clarify",
           passed, d["answer"])


def test_greeting_hi():
    d = send("hi there", "NURSERY")
    passed = check_any(d["answer"], "fliss", "help") and d["intent"] == "clarify"
    record("greeting_hi", "hi there", "Introduces self, offers help",
           passed, d["answer"])


def test_greeting_hey():
    d = send("hey", "HOMECARE")
    passed = check_any(d["answer"], "fliss", "help")
    record("greeting_hey", "hey (HOMECARE)", "Introduces self",
           passed, d["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE-INFO TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_single_location_only():
    d = send("Brighton")
    passed = check_any(d["answer"], "who", "looking for", "searching for", "help")
    record("single_location_only", "Brighton", "Asks who it's for or offers help",
           passed, d["answer"])


def test_single_who_only():
    d = send("my mum needs care")
    passed = check_any(d["answer"], "where", "location", "area", "whereabouts")
    record("single_who_only", "my mum needs care", "Asks for location",
           passed, d["answer"])


def test_single_condition_only():
    d = send("dementia care")
    passed = check_any(d["answer"], "where", "location", "area", "whereabouts", "help")
    record("single_condition_only", "dementia care", "Asks for location or offers help",
           passed, d["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-INFO EXTRACTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_extract_full_sentence():
    d = send("care home in Brighton for my 82 year old mum with dementia and mobility issues")
    passed = (
        len(d["results"]) > 0
        and check_any(d["answer"], "brighton", "mum", "mother")
    )
    record("extract_full_sentence",
           "care home in Brighton for my 82yo mum with dementia and mobility",
           "Extracts location+age+who+2 conditions, returns results",
           passed, d["answer"])


def test_extract_child_info():
    d = send("my daughter is 4 and we live in Manchester", "NURSERY")
    # Should extract who=daughter, age=4, location=Manchester
    passed = check_any(d["answer"], "manchester", "daughter", "nursery", "nurseries")
    record("extract_child_info",
           "my daughter is 4 and we live in Manchester",
           "Extracts who+age+location",
           passed, d["answer"])


def test_extract_messy_input():
    d = send("London, dementia, my nan")
    # Should extract all three from messy comma-separated input
    passed = (
        check_any(d["answer"], "london", "nan", "grandmother", "dementia")
        and (len(d["results"]) > 0 or check_any(d["answer"], "found", "search", "look"))
    )
    record("extract_messy_input",
           "London, dementia, my nan",
           "Extracts location+condition+who from messy input",
           passed, d["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# GIBBERISH / EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

def test_gibberish():
    d = send("asdfghjkl zxcvbnm qwerty")
    passed = check_any(d["answer"], "didn't quite catch", "understand", "tell me more",
                       "looking for", "help")
    record("gibberish", "asdfghjkl zxcvbnm qwerty",
           "Asks user to clarify",
           passed, d["answer"])


def test_empty_ish():
    d = send("...")
    passed = check_any(d["answer"], "help", "looking for", "catch", "tell me", "assist")
    record("empty_ish", "...", "Asks user what they need",
           passed, d["answer"])


def test_numbers_only():
    d = send("12345")
    passed = check_any(d["answer"], "help", "looking for", "postcode", "tell me", "care")
    record("numbers_only", "12345", "Handles gracefully",
           passed, d["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# WRONG CATEGORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_wrong_category_nursery_on_carehome():
    d = send("I need a nursery for my toddler", "CAREHOME")
    # Must redirect AND must NOT show results
    passed = (
        check_any(d["answer"], "nursery", "nurseries") and
        len(d["results"]) == 0
    )
    record("wrong_category_nursery_on_carehome",
           "nursery for toddler (on CAREHOME page)",
           "Redirects to nurseries page, NO results shown",
           passed, f"results={len(d['results'])}, answer={d['answer'][:100]}")


def test_wrong_category_carehome_on_nursery():
    d = send("I need a care home for my elderly father", "NURSERY")
    # Must redirect AND must NOT show results
    passed = (
        check_any(d["answer"], "care home", "care homes") and
        len(d["results"]) == 0
    )
    record("wrong_category_carehome_on_nursery",
           "care home for father (on NURSERY page)",
           "Redirects to care homes page, NO results shown",
           passed, f"results={len(d['results'])}, answer={d['answer'][:100]}")


# ═══════════════════════════════════════════════════════════════════════════════
# INFORMATIONAL QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

def test_info_funding():
    d = send("how does care home funding work?")
    passed = check_any(d["answer"], "funding", "23,250", "local authority", "self-fund",
                       "means test", "savings")
    record("info_funding", "how does care home funding work?",
           "Returns funding information",
           passed, d["answer"])


def test_info_cqc():
    d = send("what do CQC ratings mean?")
    passed = check_any(d["answer"], "outstanding", "good", "requires improvement",
                       "inadequate", "cqc", "care quality")
    record("info_cqc", "what do CQC ratings mean?",
           "Explains CQC ratings",
           passed, d["answer"])


def test_info_nursery_funding():
    d = send("how many free hours does my 3 year old get?", "NURSERY")
    passed = check_any(d["answer"], "15", "30", "free", "hours", "funded", "entitlement")
    record("info_nursery_funding",
           "how many free hours for 3yo?",
           "Explains 15/30 hour entitlement",
           passed, d["answer"])


def test_info_dementia():
    d = send("what is dementia and what types are there?")
    passed = check_any(d["answer"], "alzheimer", "vascular", "lewy", "dementia")
    record("info_dementia", "what is dementia?",
           "Explains dementia types",
           passed, d["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# VAGUE / RUDE / EMOTIONAL INPUTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_vague_help():
    d = send("I need help")
    passed = check_any(d["answer"], "help", "looking for", "care home", "what kind",
                       "tell me", "how can")
    record("vague_help", "I need help", "Asks what they need",
           passed, d["answer"])


def test_vague_care():
    d = send("I need care for someone")
    passed = check_any(d["answer"], "who", "where", "tell me more", "what kind",
                       "looking for")
    record("vague_care", "I need care for someone",
           "Asks clarifying questions",
           passed, d["answer"])


def test_rude_input():
    d = send("this is rubbish, your site is useless")
    passed = check_none(d["answer"], "rubbish", "useless") and check_any(
        d["answer"], "help", "sorry", "assist", "care", "looking for"
    )
    record("rude_input", "this is rubbish, your site is useless",
           "Stays professional, offers help",
           passed, d["answer"])


def test_emotional_input():
    d = send("my mum was just diagnosed with dementia and I'm really struggling")
    passed = (
        check_any(d["answer"], "sorry", "hear", "difficult", "tough", "understand",
                  "lot to", "must be")
        and check_any(d["answer"], "help", "care home", "find", "support", "where",
                      "location", "area")
    )
    record("emotional_input",
           "mum diagnosed with dementia, I'm struggling",
           "Empathises ONCE then moves forward",
           passed, d["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# EMPATHY NON-REPEAT TEST (multi-turn)
# ═══════════════════════════════════════════════════════════════════════════════

def test_empathy_no_repeat():
    responses = send_conversation([
        "my mum was just diagnosed with dementia and I'm really struggling",
        "she lives in Manchester",
        "she's 82 and needs full-time care",
    ])
    # First response should empathise
    r0 = responses[0]["answer"].lower()
    has_empathy_r0 = check_any(r0, "sorry", "difficult", "tough", "understand",
                               "lot to", "must be", "hear that")

    # Subsequent responses should NOT repeat empathy
    r1 = responses[1]["answer"].lower()
    r2 = responses[2]["answer"].lower()
    empathy_words = ["sorry to hear", "must be difficult", "must be tough",
                     "i understand how", "that must be"]
    no_repeat_r1 = check_none(r1, *empathy_words)
    no_repeat_r2 = check_none(r2, *empathy_words)

    passed = has_empathy_r0 and no_repeat_r1 and no_repeat_r2
    record("empathy_no_repeat",
           "3-turn emotional conversation",
           "Empathy in R0 only, not R1/R2",
           passed,
           f"R0 empathy={has_empathy_r0}, R1 no_repeat={no_repeat_r1}, R2 no_repeat={no_repeat_r2}")


# ═══════════════════════════════════════════════════════════════════════════════
# NO-REPEAT TESTS (multi-turn)
# ═══════════════════════════════════════════════════════════════════════════════

def test_no_repeat_who():
    """Send who first, then location — must NOT re-ask who."""
    responses = send_conversation([
        "it's for my mum",
        "she's in London",
    ])
    r1 = responses[1]["answer"].lower()
    # Should NOT ask who again
    passed = check_none(r1, "who is this for", "who are you searching for",
                        "who are you looking for", "who is it for")
    record("no_repeat_who",
           "Send who then location",
           "Does NOT re-ask who after location given",
           passed, responses[1]["answer"])


def test_no_repeat_location():
    """Send location first, then who — must NOT re-ask location."""
    responses = send_conversation([
        "I'm looking in Brighton",
        "it's for my dad",
    ])
    r1 = responses[1]["answer"].lower()
    # Should NOT re-ask location
    passed = check_none(r1, "where are you", "whereabouts", "which area",
                        "what location", "where do you")
    record("no_repeat_location",
           "Send location then who",
           "Does NOT re-ask location after who given",
           passed, responses[1]["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_results_count():
    d = send("care homes in London for my elderly father")
    count = len(d["results"])
    passed = 0 < count <= 8
    record("results_count",
           "care homes in London",
           "1-8 results",
           passed, f"Got {count} results")


def test_results_step5_guidance():
    d = send("find care homes in Manchester for my mum with dementia")
    answer = d["answer"].lower()
    passed = check_any(answer, "heart", "compare", "shortlist", "share")
    record("results_step5_guidance",
           "find care homes in Manchester",
           "Contains Step 5 guidance (heart/compare/share)",
           passed, d["answer"])


def test_results_step6_offer():
    d = send("care homes in London for my dad who has dementia")
    answer = d["answer"].lower()
    passed = check_any(answer, "funding", "condition", "organisation", "information",
                       "anything else", "help you with")
    record("results_step6_offer",
           "care homes in London with condition mentioned",
           "Contains Step 6 offer (funding/conditions/organisations)",
           passed, d["answer"])


def test_results_have_provider_data():
    d = send("nurseries in Essex", "NURSERY")
    if len(d["results"]) > 0:
        r = d["results"][0]
        has_name = bool(r.get("organisationName"))
        has_town = bool(r.get("townCity"))
        passed = has_name and has_town
        record("results_have_provider_data",
               "nurseries in Essex",
               "Results have organisationName and townCity",
               passed, f"name={r.get('organisationName')}, town={r.get('townCity')}")
    else:
        record("results_have_provider_data",
               "nurseries in Essex",
               "Results returned with provider data",
               False, "No results returned")


def test_results_center_coords():
    d = send("care homes in Manchester")
    passed = d["center_lat"] is not None and d["center_lng"] is not None
    record("results_center_coords",
           "care homes in Manchester",
           "Response includes center_lat and center_lng",
           passed, f"lat={d['center_lat']}, lng={d['center_lng']}")


# ═══════════════════════════════════════════════════════════════════════════════
# KEYWORD FALLBACK TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_fallback_adhd_nursery():
    d = send("nurseries in London with ADHD support", "NURSERY")
    passed = len(d["results"]) > 0
    record("fallback_adhd_nursery",
           "nurseries in London with ADHD support",
           "Returns results (location fallback) even if no ADHD keyword match",
           passed, f"{len(d['results'])} results returned")


def test_fallback_parkinsons():
    d = send("care home in Manchester for someone with Parkinson's")
    passed = len(d["results"]) > 0
    record("fallback_parkinsons",
           "care home in Manchester, Parkinson's",
           "Returns results via location fallback",
           passed, f"{len(d['results'])} results")


def test_fallback_rare_condition():
    d = send("home care in London for my wife who has motor neurone disease", "HOMECARE")
    passed = len(d["results"]) > 0
    record("fallback_rare_condition",
           "home care London, motor neurone disease",
           "Returns location results for rare condition",
           passed, f"{len(d['results'])} results")


def test_fallback_condition_still_mentioned():
    """Even with keyword fallback, the condition should be acknowledged."""
    d = send("care home in Manchester for Parkinson's")
    passed = check_any(d["answer"], "parkinson", "condition", "ask", "directly",
                       "recommend", "contact")
    record("fallback_condition_acknowledged",
           "care home Manchester Parkinson's",
           "Condition acknowledged in response even without keyword match",
           passed, d["answer"])


def test_no_dementia_filter_caveat():
    """Should NOT say 'couldn't filter for dementia' or similar."""
    d = send("care home in Brighton for my mum with dementia")
    passed = check_none(d["answer"], "couldn't specifically filter",
                        "couldn't filter for dementia", "unable to filter")
    record("no_dementia_filter_caveat",
           "care home Brighton dementia",
           "Does NOT apologise for not filtering by condition",
           passed, d["answer"])


def test_zero_results_graceful():
    d = send("care homes in Inverness")
    if len(d["results"]) == 0:
        passed = check_any(d["answer"], "wasn't able to find", "couldn't find",
                           "no results", "growing", "try", "nearby", "wider",
                           "directory")
        record("zero_results_graceful",
               "care homes in Inverness (no listings)",
               "Handles zero results gracefully",
               passed, d["answer"])
    else:
        record("zero_results_graceful",
               "care homes in Inverness",
               "Zero results handled gracefully",
               True, f"Got {len(d['results'])} results (area has coverage)")


# ═══════════════════════════════════════════════════════════════════════════════
# ALL THREE PAGE TYPES
# ═══════════════════════════════════════════════════════════════════════════════

def test_carehome_page():
    d = send("care homes in London", "CAREHOME")
    passed = d["intent"] in ("listings", "clarify") and len(d["results"]) >= 0
    record("carehome_page", "care homes in London (CAREHOME)",
           "Works on CAREHOME page",
           passed, f"intent={d['intent']}, results={len(d['results'])}")


def test_nursery_page():
    d = send("nurseries near Essex for my 3 year old", "NURSERY")
    passed = d["intent"] in ("listings", "clarify") and len(d["results"]) >= 0
    record("nursery_page", "nurseries in Essex (NURSERY)",
           "Works on NURSERY page",
           passed, f"intent={d['intent']}, results={len(d['results'])}")


def test_homecare_page():
    d = send("home care in London for my husband", "HOMECARE")
    passed = d["intent"] in ("listings", "clarify") and len(d["results"]) >= 0
    record("homecare_page", "home care in London (HOMECARE)",
           "Works on HOMECARE page",
           passed, f"intent={d['intent']}, results={len(d['results'])}")


# ═══════════════════════════════════════════════════════════════════════════════
# FULL CONVERSATION TEST (5 turns)
# ═══════════════════════════════════════════════════════════════════════════════

def test_full_conversation():
    responses = send_conversation([
        "hello",
        "I need a care home for my mum",
        "she's in Manchester and she has dementia",
        "what about funding? she has about £30,000 in savings",
        "thank you, that's all I needed",
    ])

    checks = []

    # Turn 0: greeting
    r0 = responses[0]["answer"].lower()
    checks.append(("greeting", check_any(r0, "fliss", "help")))

    # Turn 1: asks for more info
    r1 = responses[1]["answer"].lower()
    checks.append(("asks_info", check_any(r1, "where", "location", "whereabouts",
                                          "area", "searching for")))

    # Turn 2: should search and return results
    r2_results = len(responses[2]["results"])
    r2 = responses[2]["answer"].lower()
    checks.append(("has_results", r2_results > 0))
    checks.append(("mentions_manchester", "manchester" in r2))

    # Turn 3: should provide funding info
    r3 = responses[3]["answer"].lower()
    checks.append(("funding_info", check_any(r3, "23,250", "self-fund", "savings",
                                             "threshold", "local authority", "means")))

    # Turn 4: should wind down
    r4 = responses[4]["answer"].lower()
    checks.append(("wind_down", check_any(r4, "good luck", "take care", "here if",
                                          "caretopia", "wonderful day", "fliss")))

    all_passed = all(c[1] for c in checks)
    detail = ", ".join(f"{n}={'PASS' if p else 'FAIL'}" for n, p in checks)
    record("full_conversation_5_turns",
           "5-turn conversation (greeting→search→funding→close)",
           "All 5 turns behave correctly",
           all_passed, detail)


# ═══════════════════════════════════════════════════════════════════════════════
# SIGN-OFF TEST
# ═══════════════════════════════════════════════════════════════════════════════

def test_signoff_wording():
    responses = send_conversation([
        "care homes in Manchester for my mum with dementia",
        "no thanks, that's everything",
        "no I'm fine thanks, goodbye",
    ])
    # The final response should contain the sign-off
    final = responses[-1]["answer"]
    passed = check_any(final, "caretopia world", "thanks for talking",
                       "wonderful day", "fliss")
    record("signoff_wording",
           "Complete conversation to sign-off",
           "Contains approved sign-off wording",
           passed, final)


# ═══════════════════════════════════════════════════════════════════════════════
# SHOW MORE RESULTS TEST
# ═══════════════════════════════════════════════════════════════════════════════

def test_show_more_offer():
    """After showing results, should offer to show more options."""
    d = send("care homes in London for my dad")
    passed = check_any(d["answer"], "more options", "show you more", "see more",
                       "more results")
    record("show_more_offer",
           "care homes in London",
           "Offers to show more options after results",
           passed, d["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# DEEP DIVE + ORGANISATION LINKS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_deep_dive_offer():
    """After informational response, should offer to go into more detail."""
    d = send("what is dementia?")
    passed = check_any(d["answer"], "more detail", "go into more", "further",
                       "dementiauk.org", "alzheimers.org.uk")
    record("deep_dive_offer",
           "what is dementia?",
           "Offers more detail or includes org links",
           passed, d["answer"])


def test_org_links_funding():
    """Funding info should include relevant org links."""
    d = send("how does care home funding work?")
    passed = check_any(d["answer"], "gov.uk", "ageuk.org.uk", "age uk",
                       "citizensadvice.org.uk")
    record("org_links_funding",
           "how does care home funding work?",
           "Includes relevant organisation links",
           passed, d["answer"])


def test_org_links_dementia():
    """Dementia info should include dementia org links."""
    d = send("tell me about dementia care")
    passed = check_any(d["answer"], "dementiauk.org", "alzheimers.org.uk",
                       "dementia uk", "alzheimer's society")
    record("org_links_dementia",
           "tell me about dementia care",
           "Includes dementia organisation links",
           passed, d["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# NO EXTERNAL SEARCH SUGGESTION TEST
# ═══════════════════════════════════════════════════════════════════════════════

def test_no_external_search():
    """Should NEVER suggest searching externally."""
    d = send("I need childcare in Leeds", "CAREHOME")
    passed = check_none(d["answer"], "try searching for", "search for childcare",
                        "search for daycare", "search online")
    record("no_external_search",
           "childcare in Leeds (on CAREHOME page)",
           "Does NOT suggest external searching",
           passed, d["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# HOME CARE PAGE BEHAVIOUR TEST
# ═══════════════════════════════════════════════════════════════════════════════

def test_homecare_shows_homecare_first():
    """On Home Care page, should show home care results first, not redirect."""
    d = send("my nan is 85 and quite frail, she needs help at home in London", "HOMECARE")
    # Should show home care results, not redirect to care homes
    passed = (
        len(d["results"]) > 0
        and check_any(d["answer"], "home care", "care provider", "found")
    )
    record("homecare_shows_homecare_first",
           "frail 85yo nan in London (HOMECARE page)",
           "Shows home care results first, not redirect",
           passed, f"results={len(d['results'])}, answer={d['answer'][:100]}")


# ═══════════════════════════════════════════════════════════════════════════════
# WELLBEING CHECK-IN TEST
# ═══════════════════════════════════════════════════════════════════════════════

def test_wellbeing_checkin():
    """Wellbeing check-in must be offered before closing."""
    responses = send_conversation([
        "care homes in Manchester for my mum with dementia",
        "no thanks, that's all",
    ])
    # After user says they're done, should get wellbeing check-in
    final = responses[-1]["answer"]
    passed = check_any(final, "holding up", "look after yourself", "how are you",
                       "wellbeing", "self-care", "yourself too")
    record("wellbeing_checkin",
           "Conversation winds down",
           "Wellbeing check-in offered before closing",
           passed, final)


# ═══════════════════════════════════════════════════════════════════════════════
# TYPO RECOVERY TEST
# ═══════════════════════════════════════════════════════════════════════════════

def test_typo_recovery():
    """After typo correction, conversation should continue smoothly."""
    responses = send_conversation([
        "care homes in Mnchester for my mum",
        "sorry, I meant Manchester",
    ])
    # After correction, should proceed with Manchester search
    r1 = responses[1]
    passed = (
        check_any(r1["answer"], "manchester", "found", "options", "results")
    )
    record("typo_recovery",
           "Misspell then correct Manchester",
           "Continues smoothly after typo correction",
           passed, r1["answer"])


# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

ALL_TESTS = [
    # Greetings
    test_greeting_hello,
    test_greeting_hi,
    test_greeting_hey,
    # Single info
    test_single_location_only,
    test_single_who_only,
    test_single_condition_only,
    # Multi-info extraction
    test_extract_full_sentence,
    test_extract_child_info,
    test_extract_messy_input,
    # Gibberish / edge cases
    test_gibberish,
    test_empty_ish,
    test_numbers_only,
    # Wrong category
    test_wrong_category_nursery_on_carehome,
    test_wrong_category_carehome_on_nursery,
    # Informational
    test_info_funding,
    test_info_cqc,
    test_info_nursery_funding,
    test_info_dementia,
    # Vague / rude / emotional
    test_vague_help,
    test_vague_care,
    test_rude_input,
    test_emotional_input,
    # Empathy no-repeat
    test_empathy_no_repeat,
    # No-repeat
    test_no_repeat_who,
    test_no_repeat_location,
    # Results quality
    test_results_count,
    test_results_step5_guidance,
    test_results_step6_offer,
    test_results_have_provider_data,
    test_results_center_coords,
    # Keyword fallback
    test_fallback_adhd_nursery,
    test_fallback_parkinsons,
    test_fallback_rare_condition,
    test_fallback_condition_still_mentioned,
    test_no_dementia_filter_caveat,
    test_zero_results_graceful,
    # Page types
    test_carehome_page,
    test_nursery_page,
    test_homecare_page,
    # Full conversation
    test_full_conversation,
    # Sign-off
    test_signoff_wording,
    # Nathan's fixes
    test_show_more_offer,
    test_deep_dive_offer,
    test_org_links_funding,
    test_org_links_dementia,
    test_no_external_search,
    test_homecare_shows_homecare_first,
    test_wellbeing_checkin,
    test_typo_recovery,
    # Jobs
    test_jobs_greeting,
    test_jobs_search,
    test_jobs_no_location,
]


# ═══════════════════════════════════════════════════════════════════════════════
# JOBS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_jobs_greeting():
    d = send("hello", "JOBS")
    passed = check_any(d["answer"], "fliss", "help", "job", "role")
    record("jobs_greeting", "hello (JOBS page)",
           "Introduces self on jobs page",
           passed, d["answer"])


def test_jobs_search():
    d = send("care assistant jobs in London", "JOBS")
    passed = len(d["results"]) > 0 or check_any(d["answer"], "found", "job", "london")
    record("jobs_search", "care assistant jobs in London",
           "Returns job results or acknowledges search",
           passed, f"results={len(d['results'])}, answer={d['answer'][:100]}")


def test_jobs_no_location():
    d = send("I'm looking for a nursing job", "JOBS")
    passed = check_any(d["answer"], "where", "location", "area", "whereabouts")
    record("jobs_no_location", "nursing job (no location)",
           "Asks for location before searching",
           passed, d["answer"])


def main():
    # Check server is up
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        r.raise_for_status()
    except Exception:
        print("ERROR: Server not running at", BASE_URL)
        sys.exit(1)

    print(f"\nFliss v2 Test Suite — {len(ALL_TESTS)} tests")
    print(f"Server: {BASE_URL}")
    print("=" * 70)

    start = time.time()
    for test_fn in ALL_TESTS:
        try:
            test_fn()
        except Exception as e:
            record(test_fn.__name__, "ERROR", "Should not crash", False, str(e))

    elapsed = time.time() - start
    passed = sum(1 for r in results_table if r["passed"])
    failed = sum(1 for r in results_table if not r["passed"])
    total = len(results_table)

    print()
    print("=" * 70)
    print(f"RESULTS: {passed}/{total} passed, {failed} failed ({elapsed:.1f}s)")
    print("=" * 70)

    if failed > 0:
        print(f"\nFAILED TESTS ({failed}):")
        print("-" * 70)
        for r in results_table:
            if not r["passed"]:
                print(f"  {r['name']}")
                print(f"    Input:    {r['input']}")
                print(f"    Expected: {r['expected']}")
                print(f"    Actual:   {r['actual']}")
                print()


if __name__ == "__main__":
    main()
