# -*- coding: utf-8 -*-
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from settings import settings
from jellyfin_client import JellyfinClient
from db import DB
from suggester import build_suggestions
from web import router as web_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("jellyfin-organizer")

db = DB(f"{settings.data_dir}/organizer.sqlite3")
jf = JellyfinClient(settings.jellyfin_url, settings.jellyfin_api_key)

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Started. Dry-run=%s Jellyfin=%s", settings.dry_run, settings.jellyfin_url)
    yield

app = FastAPI(title="Jellyfin Organizer", version="1.0.0", lifespan=lifespan)
app.include_router(web_router)

@app.get("/health")
def health():
    return {"ok": True, "dry_run": settings.dry_run}

@app.post("/scan")
async def scan():
    now = int(time.time())
    items = await jf.fetch_movies()

    for it in items:
        db.upsert_item(it, now)

    db.clear_suggestions()

    suggestions = build_suggestions(
        items=items,
        franchise_rules=settings.franchise_rules(),
        min_group_size=settings.min_group_size,
        enable_franchise=settings.enable_franchise,
        enable_studio=settings.enable_studio,
        enable_format=settings.enable_format,
        enable_length=settings.enable_length,
        enable_audience=settings.enable_audience,
        enable_mood=settings.enable_mood,
        studio_allowlist=settings.studio_allowlist(),
        top_studios=settings.top_studios
    )

    for s in suggestions:
        db.insert_suggestion(s)

    log.info("Scan complete: %d items, %d suggestions", len(items), len(suggestions))
    return {"items": len(items), "suggestions": len(suggestions), "dry_run": settings.dry_run}

@app.get("/suggestions")
def list_suggestions():
    return db.list_suggestions()

@app.post("/apply/{suggestion_id}")
async def apply_suggestion(suggestion_id: str):
    s = db.get_suggestion(suggestion_id)
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if s["applied"]:
        return {"ok": True, "already_applied": True, "applied_collection_id": s["applied_collection_id"]}

    # DRY RUN
    if settings.dry_run:
        if s["suggestion_type"] == "collection":
            return {
                "ok": True,
                "dry_run": True,
                "would_create_collection": s["title"],
                "would_add_items": len(s["item_ids"])
            }
        if s["suggestion_type"] == "tag":
            # Important: on your Jellyfin we will APPLY TAGS AS COLLECTIONS
            return {
                "ok": True,
                "dry_run": True,
                "would_create_collection": s["title"],
                "would_add_items": len(s["item_ids"]),
                "note": "This Jellyfin build does not support tag writes reliably; applying as a Collection instead."
            }
        return {"ok": True, "dry_run": True, "note": f"Unsupported suggestion_type={s['suggestion_type']}"}

    # APPLY FOR REAL
    if s["suggestion_type"] in ("collection", "tag"):
        # Apply BOTH as collections (tag writes are unreliable / not supported)
        created = await jf.create_collection(s["title"])
        collection_id = created.get("Id")
        if not collection_id:
            raise HTTPException(status_code=500, detail=f"Failed to create collection (no Id returned): {created}")

        add_res = await jf.add_items_to_collection(collection_id, s["item_ids"])
        if isinstance(add_res, dict) and add_res.get("ok") is False:
            raise HTTPException(status_code=500, detail=f"Failed to add items to collection: {add_res}")

        db.mark_applied(suggestion_id, collection_id)
        log.info("Applied %s as collection: %s -> %s (%d items)",
                 s["suggestion_type"], s["title"], collection_id, len(s["item_ids"]))

        return {"ok": True, "collection_id": collection_id, "added_items": len(s["item_ids"])}

    raise HTTPException(status_code=400, detail=f"Unsupported suggestion_type: {s['suggestion_type']}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, log_level=settings.log_level.lower())
