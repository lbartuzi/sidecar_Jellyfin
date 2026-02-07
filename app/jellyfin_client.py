# -*- coding: utf-8 -*-
import httpx
from typing import Any, Dict, List, Optional

class JellyfinClient:
    def __init__(self, base_url: str, api_key: str, user_id: str = ""):
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id or ""
        self.headers = {
            "X-Emby-Token": api_key,
            "Accept": "application/json",
        }

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url, headers=self.headers, params=params)
            r.raise_for_status()
            return r.json()

    async def post(self, path: str, json_body: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None):
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=self.headers, json=json_body, params=params)
            return r

    async def ensure_user_id(self) -> str:
        if self.user_id:
            return self.user_id
        # Try to pick the first user
        users = await self.get("/Users")
        if isinstance(users, list) and users:
            self.user_id = users[0].get("Id", "")
        return self.user_id

    async def fetch_movies(self) -> List[Dict[str, Any]]:
        params = {
            "IncludeItemTypes": "Movie",
            "Recursive": "true",
            "Fields": ",".join([
                "ProviderIds","Path","Genres","Tags","Studios",
                "ProductionYear","PremiereDate","SortName","OriginalTitle",
                "CommunityRating","RunTimeTicks",
                "OfficialRating","Overview","Taglines"
            ])
        }
        data = await self.get("/Items", params=params)
        return data.get("Items", [])

    async def create_collection(self, name: str) -> Dict[str, Any]:
        r = await self.post("/Collections", params={"Name": name})
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text}
        return r.json() if r.content else {"ok": True}

    async def add_items_to_collection(self, collection_id: str, item_ids: List[str]) -> Dict[str, Any]:
        ids = ",".join(item_ids)
        r = await self.post(f"/Collections/{collection_id}/Items", params={"Ids": ids})
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text}
        return {"ok": True}

    async def get_item_for_user(self, item_id: str) -> Dict[str, Any]:
        uid = await self.ensure_user_id()
        if not uid:
            raise RuntimeError("No Jellyfin user id available. Set JELLYFIN_USER_ID.")
        # Some Jellyfin versions want no Fields param here; fetch full and read Tags.
        return await self.get(f"/Users/{uid}/Items/{item_id}")

    async def update_item_tags_metadata(self, item_id: str, tags: List[str]) -> Dict[str, Any]:
        """
        Try metadata update endpoints. Versions differ.
        """
        payload = {"Tags": tags}
        attempts = [
            (f"/Items/{item_id}/Metadata", payload, None),
            (f"/Items/{item_id}", payload, None),
        ]

        last = None
        for path, json_body, params in attempts:
            r = await self.post(path, json_body=json_body, params=params)
            if 200 <= r.status_code < 300:
                return {"ok": True, "endpoint": path, "status": r.status_code}
            last = {"ok": False, "endpoint": path, "status": r.status_code, "body": r.text}

        return {"ok": False, "error": last}

    async def add_tag_to_item(self, item_id: str, tag: str) -> Dict[str, Any]:
        try:
            item = await self.get_item_for_user(item_id)
        except Exception as e:
            return {"ok": False, "step": "get_item_for_user", "error": str(e), "item_id": item_id}

        existing = item.get("Tags") or []
        if not isinstance(existing, list):
            existing = []

        if tag in existing:
            return {"ok": True, "already_present": True}

        new_tags = existing + [tag]
        return await self.update_item_tags_metadata(item_id, new_tags)
