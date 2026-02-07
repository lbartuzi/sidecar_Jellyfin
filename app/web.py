# -*- coding: utf-8 -*-
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def index():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Jellyfin Organizer</title>
  <style>
    body { font-family: sans-serif; margin: 24px; }
    button { padding: 8px 12px; margin-right: 8px; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 12px; margin: 12px 0; }
    .muted { color: #666; font-size: 0.9em; }
    code { background: #f5f5f5; padding: 2px 4px; border-radius: 6px; }
  </style>
</head>
<body>
  <h2>Jellyfin Organizer</h2>
  <p class="muted">
    Workflow:
    <button onclick="scan()">Scan</button>
    then review suggestions below, then apply.
  </p>

  <div id="status" class="muted"></div>
  <div id="list"></div>

<script>
async function scan(){
  document.getElementById("status").innerText = "Scanning...";
  const r = await fetch("/scan", {method:"POST"});
  const j = await r.json();
  document.getElementById("status").innerText =
    "Scan complete. Items: " + j.items + ", Suggestions: " + j.suggestions + " (Dry-run: " + j.dry_run + ")";
  await load();
}

async function load(){
  const r = await fetch("/suggestions");
  const j = await r.json();
  const root = document.getElementById("list");
  root.innerHTML = "";
  for (const s of j) {
    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `
      <div><b>${s.title}</b> <span class="muted">(${s.suggestion_type})</span></div>
      <div class="muted">Confidence: ${Number(s.confidence).toFixed(2)} | Items: ${s.item_ids.length} | Applied: ${s.applied}</div>
      <div class="muted">Reason: ${s.reason || "-"}</div>
      <div class="muted">Suggestion ID: <code>${s.suggestion_id}</code></div>
      <div style="margin-top:8px;">
        <button onclick="apply('${s.suggestion_id}')" ${s.applied ? "disabled": ""}>Apply</button>
      </div>
    `;
    root.appendChild(div);
  }
}

async function apply(id){
  document.getElementById("status").innerText = "Applying " + id + "...";
  const r = await fetch("/apply/" + id, {method:"POST"});
  const j = await r.json();
  document.getElementById("status").innerText = JSON.stringify(j);
  await load();
}

load();
</script>
</body>
</html>
"""
