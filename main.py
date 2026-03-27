from contextlib import asynccontextmanager
from typing import Optional, List, Any
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from chat.engine import ConversationEngine
from tools.search import close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


app = FastAPI(
    title="Fliss",
    description="AI conversational search engine for Caretopia",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Frontend-compatible API contract ─────────────────────────────────────────

class QueryContext(BaseModel):
    session_id: str


class QueryRequest(BaseModel):
    query: str
    mode: str = "text"
    context: QueryContext
    type: str = "CAREHOME"  # CAREHOME | NURSERY | HOMECARE


class QueryResponse(BaseModel):
    intent: str
    confidence: float
    answer: str
    results: List[Any] = []
    title: str = ""
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None


# In-memory conversation history per session
_sessions: dict = {}


@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    session_id = req.context.session_id
    page_type = req.type

    # Get or create conversation history for this session
    session_key = f"{session_id}:{page_type}"
    if session_key not in _sessions:
        _sessions[session_key] = []
    history = _sessions[session_key]

    engine = ConversationEngine(frontend_type=page_type)
    result = await engine.chat(
        message=req.query,
        conversation_history=history,
    )

    # Append to conversation history for next turn
    history.append({"role": "user", "content": req.query})
    # Store the answer as-is — no metadata in the content
    stored_content = result["answer"]
    filters_used = result.get("filters_used")
    assistant_msg = {"role": "assistant", "content": stored_content}
    # Store search metadata separately so engine.py can inject it
    # as context without it leaking into the AI's visible response text
    if filters_used:
        assistant_msg["filters_used"] = filters_used
    if result.get("results"):
        assistant_msg["results"] = result["results"]
        assistant_msg["title"] = result.get("title", "")
        assistant_msg["center_lat"] = result.get("center_lat")
        assistant_msg["center_lng"] = result.get("center_lng")
    history.append(assistant_msg)

    return QueryResponse(**result)


# ── History endpoint ─────────────────────────────────────────────────────────

@app.get("/api/history/{session_id}")
async def history(
    session_id: str,
    page_type: str = Query(default="CAREHOME"),
    limit: int = Query(default=20, ge=1, le=100),
):
    session_key = f"{session_id}:{page_type}"
    messages = _sessions.get(session_key, [])
    return {"session_id": session_id, "page_type": page_type, "messages": messages[-limit:]}


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Test chat UI ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def test_ui():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fliss v2 — Test Chat</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; height: 100vh; display: flex; flex-direction: column; }
  .header { background: #2563eb; color: white; padding: 16px 24px; display: flex; align-items: center; gap: 16px; }
  .header h1 { font-size: 20px; font-weight: 600; }
  .header select { padding: 4px 8px; border-radius: 4px; border: none; }
  .chat { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
  .msg { max-width: 75%; padding: 12px 16px; border-radius: 12px; line-height: 1.5; white-space: pre-wrap; }
  .msg.user { background: #2563eb; color: white; align-self: flex-end; border-bottom-right-radius: 4px; }
  .msg.assistant { background: white; color: #1f2937; align-self: flex-start; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .msg.error { background: #fee2e2; color: #991b1b; align-self: center; }
  .results-card { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; margin-top: 8px; font-size: 13px; }
  .result-item { padding: 8px 0; border-bottom: 1px solid #e5e7eb; }
  .result-item:last-child { border-bottom: none; }
  .result-name { font-weight: 600; color: #1f2937; }
  .result-detail { color: #6b7280; font-size: 12px; }
  .meta { font-size: 11px; color: #6b7280; margin-top: 6px; padding: 4px 0; }
  .input-bar { display: flex; gap: 8px; padding: 16px 24px; background: white; border-top: 1px solid #e5e7eb; }
  .input-bar input { flex: 1; padding: 12px 16px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 15px; outline: none; }
  .input-bar input:focus { border-color: #2563eb; }
  .input-bar button { padding: 12px 24px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; }
  .input-bar button:disabled { opacity: 0.5; cursor: not-allowed; }
  .typing { color: #6b7280; font-style: italic; align-self: flex-start; padding: 8px 16px; }
</style>
</head>
<body>
<div class="header">
  <h1>Fliss v2</h1>
  <span style="font-weight:300;font-size:14px;">Caretopia AI Search</span>
  <select id="pageType">
    <option value="CAREHOME">Care Homes</option>
    <option value="NURSERY">Nurseries</option>
    <option value="HOMECARE">Home Care</option>
    <option value="JOBS">Jobs</option>
  </select>
</div>
<div class="chat" id="chat"></div>
<div class="input-bar">
  <input type="text" id="input" placeholder="Type your message..." autofocus>
  <button id="send" onclick="sendMessage()">Send</button>
</div>
<script>
const chatEl = document.getElementById('chat');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send');
const pageTypeEl = document.getElementById('pageType');
const sessionId = crypto.randomUUID();

inputEl.addEventListener('keydown', e => { if (e.key === 'Enter' && !sendBtn.disabled) sendMessage(); });

function addMsg(role, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function addResults(results, data) {
  if (!results || results.length === 0) return;
  const container = document.createElement('div');
  container.className = 'msg assistant';

  let html = '<div class="results-card">';
  results.forEach(r => {
    const name = r.organisationName || r.name || 'Unknown';
    const loc = [r.townCity, r.postcode].filter(Boolean).join(', ');
    const grade = r.cqcGrade || r.ofstedGrade || '';
    const dist = r.distance_km != null ? r.distance_km + ' km' : '';
    const phone = r.contactPhone || '';
    html += '<div class="result-item">';
    html += '<div class="result-name">' + name + '</div>';
    html += '<div class="result-detail">' + [loc, grade, dist, phone].filter(Boolean).join(' · ') + '</div>';
    if (r.description) html += '<div class="result-detail">' + r.description + '</div>';
    html += '</div>';
  });
  html += '</div>';
  html += '<div class="meta">Intent: ' + data.intent + ' | Title: ' + data.title + '</div>';
  container.innerHTML = html;
  chatEl.appendChild(container);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendMessage() {
  const msg = inputEl.value.trim();
  if (!msg) return;
  inputEl.value = '';
  addMsg('user', msg);
  sendBtn.disabled = true;

  const typing = document.createElement('div');
  typing.className = 'typing';
  typing.textContent = 'Fliss is thinking...';
  chatEl.appendChild(typing);

  try {
    const res = await fetch('/api/query', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        query: msg,
        mode: 'text',
        context: { session_id: sessionId },
        type: pageTypeEl.value,
      }),
    });
    typing.remove();
    const data = await res.json();

    if (!res.ok) {
      addMsg('error', 'Error: ' + (data.detail || res.statusText));
    } else {
      addMsg('assistant', data.answer);
      if (data.results && data.results.length > 0) addResults(data.results, data);
    }
  } catch (err) {
    typing.remove();
    addMsg('error', 'Network error: ' + err.message);
  }
  sendBtn.disabled = false;
  inputEl.focus();
}
</script>
</body>
</html>"""
