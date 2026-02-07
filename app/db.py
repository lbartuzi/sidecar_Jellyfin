# -*- coding: utf-8 -*-
import sqlite3
from typing import Any, Dict, List, Optional
import json
from pathlib import Path

class DB:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init()

    def _table_has_column(self, table: str, col: str) -> bool:
        cur = self.conn.execute(f"PRAGMA table_info({table});")
        return any(r[1] == col for r in cur.fetchall())

    def _add_column_if_missing(self, table: str, col: str, ddl_type: str):
        if not self._table_has_column(table, col):
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl_type};")

    def _init(self):
        # Create tables for fresh installs
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            name TEXT,
            year INTEGER,
            path TEXT,
            provider_ids TEXT,
            genres TEXT,
            tags TEXT,
            studios TEXT,
            runtime_ticks INTEGER,
            rating REAL,
            official_rating TEXT,
            overview TEXT,
            taglines TEXT,
            updated_at INTEGER
        );
        """)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            suggestion_id TEXT PRIMARY KEY,
            suggestion_type TEXT,
            title TEXT,
            confidence REAL,
            item_ids TEXT,
            reason TEXT,
            payload TEXT,
            created_at INTEGER,
            applied INTEGER DEFAULT 0,
            applied_collection_id TEXT
        );
        """)
        self.conn.commit()

        # Migrations for older DBs
        self._add_column_if_missing("items", "official_rating", "TEXT")
        self._add_column_if_missing("items", "overview", "TEXT")
        self._add_column_if_missing("items", "taglines", "TEXT")

        self._add_column_if_missing("suggestions", "reason", "TEXT")
        self._add_column_if_missing("suggestions", "payload", "TEXT")

        self.conn.commit()

    def upsert_item(self, item: Dict[str, Any], now_ts: int):
        self.conn.execute("""
        INSERT INTO items(
            id,name,year,path,provider_ids,genres,tags,studios,
            runtime_ticks,rating,official_rating,overview,taglines,updated_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
          name=excluded.name,
          year=excluded.year,
          path=excluded.path,
          provider_ids=excluded.provider_ids,
          genres=excluded.genres,
          tags=excluded.tags,
          studios=excluded.studios,
          runtime_ticks=excluded.runtime_ticks,
          rating=excluded.rating,
          official_rating=excluded.official_rating,
          overview=excluded.overview,
          taglines=excluded.taglines,
          updated_at=excluded.updated_at
        """, (
            item.get("Id"),
            item.get("Name"),
            item.get("ProductionYear"),
            item.get("Path"),
            json.dumps(item.get("ProviderIds") or {}),
            json.dumps(item.get("Genres") or []),
            json.dumps(item.get("Tags") or []),
            json.dumps(item.get("Studios") or []),
            item.get("RunTimeTicks") or 0,
            item.get("CommunityRating") or None,
            item.get("OfficialRating") or None,
            item.get("Overview") or None,
            json.dumps(item.get("Taglines") or []),
            now_ts
        ))
        self.conn.commit()

    def clear_suggestions(self):
        self.conn.execute("DELETE FROM suggestions;")
        self.conn.commit()

    def insert_suggestion(self, suggestion: Dict[str, Any]):
        self.conn.execute("""
        INSERT INTO suggestions(
            suggestion_id,suggestion_type,title,confidence,item_ids,reason,payload,created_at,applied,applied_collection_id
        )
        VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (
            suggestion["suggestion_id"],
            suggestion["suggestion_type"],
            suggestion["title"],
            float(suggestion["confidence"]),
            json.dumps(suggestion["item_ids"]),
            suggestion.get("reason"),
            json.dumps(suggestion.get("payload")) if suggestion.get("payload") is not None else None,
            int(suggestion["created_at"]),
            1 if suggestion.get("applied") else 0,
            suggestion.get("applied_collection_id"),
        ))
        self.conn.commit()

    def list_suggestions(self) -> List[Dict[str, Any]]:
        cur = self.conn.execute("""
        SELECT suggestion_id,suggestion_type,title,confidence,item_ids,reason,payload,created_at,applied,applied_collection_id
        FROM suggestions
        ORDER BY confidence DESC, created_at DESC
        """)
        out = []
        for row in cur.fetchall():
            out.append({
                "suggestion_id": row[0],
                "suggestion_type": row[1],
                "title": row[2],
                "confidence": row[3],
                "item_ids": json.loads(row[4]),
                "reason": row[5],
                "payload": json.loads(row[6]) if row[6] else None,
                "created_at": row[7],
                "applied": bool(row[8]),
                "applied_collection_id": row[9],
            })
        return out

    def get_suggestion(self, suggestion_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute("""
        SELECT suggestion_id,suggestion_type,title,confidence,item_ids,reason,payload,created_at,applied,applied_collection_id
        FROM suggestions WHERE suggestion_id=?
        """, (suggestion_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "suggestion_id": row[0],
            "suggestion_type": row[1],
            "title": row[2],
            "confidence": row[3],
            "item_ids": json.loads(row[4]),
            "reason": row[5],
            "payload": json.loads(row[6]) if row[6] else None,
            "created_at": row[7],
            "applied": bool(row[8]),
            "applied_collection_id": row[9],
        }

    def mark_applied(self, suggestion_id: str, applied_collection_id: str):
        self.conn.execute("""
        UPDATE suggestions
        SET applied=1, applied_collection_id=?
        WHERE suggestion_id=?
        """, (applied_collection_id, suggestion_id))
        self.conn.commit()
