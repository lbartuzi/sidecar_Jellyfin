# -*- coding: utf-8 -*-
import re
import time
import uuid
from typing import Any, Dict, List, Tuple
from collections import defaultdict, Counter

_ROMAN = {"i":1,"ii":2,"iii":3,"iv":4,"v":5,"vi":6,"vii":7,"viii":8,"ix":9,"x":10}

GENERIC_STUDIOS = {
    "amazon", "amazon studios", "netflix", "paramount", "warner bros",
    "warner bros.", "universal", "20th century fox", "fox", "sony", "columbia",
    "metro-goldwyn-mayer", "mgm", "lionsgate"
}

# Canonical mapping (feel free to extend later)
STUDIO_CANON = {
    "pixar": "Pixar",
    "walt disney": "Disney",
    "walt disney pictures": "Disney",
    "walt disney animation studios": "Disney Animation",
    "disney": "Disney",
    "marvel studios": "Marvel Studios",
    "lucasfilm": "Lucasfilm",
    "dreamworks": "DreamWorks",
    "illumination": "Illumination",
    "studio ghibli": "Studio Ghibli",
    "ghibli": "Studio Ghibli",
    "a24": "A24",
}

def _normalize_title(name: str) -> str:
    s = (name or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s:]", "", s)
    return s

def _title_core(norm: str) -> str:
    return norm.split(":", 1)[0].strip()

def _strip_sequel_suffix(core: str) -> str:
    tokens = core.split()
    if not tokens:
        return core
    if len(tokens) >= 2 and tokens[-2] == "part" and tokens[-1].isdigit():
        return " ".join(tokens[:-2]).strip()
    last = tokens[-1]
    if last.isdigit() or last in _ROMAN:
        return " ".join(tokens[:-1]).strip()
    return core

def _base_key(name: str) -> str:
    norm = _normalize_title(name)
    core = _title_core(norm)
    return _strip_sequel_suffix(core)

def _has_sequel_marker(name: str) -> bool:
    norm = _normalize_title(name)
    core = _title_core(norm)
    tokens = core.split()
    if not tokens:
        return False
    last = tokens[-1]
    if last.isdigit() or last in _ROMAN:
        return True
    if len(tokens) >= 2 and tokens[-2] == "part" and tokens[-1].isdigit():
        return True
    return False

def _list_lower(x) -> List[str]:
    if not x:
        return []
    if isinstance(x, list):
        out = []
        for v in x:
            if isinstance(v, str):
                out.append(v.lower())
            elif isinstance(v, dict) and "Name" in v:
                out.append(str(v["Name"]).lower())
            else:
                out.append(str(v).lower())
        return out
    return [str(x).lower()]

def _runtime_minutes(item: Dict[str, Any]) -> int:
    ticks = item.get("RunTimeTicks") or 0
    return int(ticks / 10_000_000 / 60) if ticks else 0

def _official_rating(item: Dict[str, Any]) -> str:
    return (item.get("OfficialRating") or "").upper().strip()

def _text_blob(item: Dict[str, Any]) -> str:
    overview = (item.get("Overview") or "")
    taglines = item.get("Taglines") or []
    if isinstance(taglines, list):
        taglines = " ".join([str(t) for t in taglines])
    else:
        taglines = str(taglines)
    return (overview + " " + taglines).lower()

def _canon_studio(name: str) -> str:
    n = (name or "").lower().strip()
    for k, v in STUDIO_CANON.items():
        if k in n:
            return v
    # fallback: title-case original-ish
    return (name or "").strip()

def _format_tag(item: Dict[str, Any]) -> str:
    genres = set(_list_lower(item.get("Genres")))
    if "documentary" in genres:
        return "format:documentary"
    if "animation" in genres:
        return "format:animation"
    return "format:live_action"

def _length_tag(item: Dict[str, Any]) -> str:
    m = _runtime_minutes(item)
    if m and m <= 75:
        return "length:short"
    if m and m <= 110:
        return "length:standard"
    if m and m <= 140:
        return "length:long"
    if m:
        return "length:epic"
    return "length:unknown"

def _audience_tag(item: Dict[str, Any]) -> str:
    r = _official_rating(item)
    genres = set(_list_lower(item.get("Genres")))
    # Strong exclusions
    if r in {"R","NC-17","TV-MA"}:
        return "audience:adults"
    # Family/kids leaning
    if r in {"G","TV-Y","TV-Y7","TV-G"}:
        return "audience:kids"
    if r == "PG":
        # if horror/thriller present, avoid "family"
        if "horror" in genres or "thriller" in genres:
            return "audience:teens"
        return "audience:family"
    if r == "PG-13":
        return "audience:teens"
    # Unknown rating: infer from genres (weak)
    if "animation" in genres or "family" in genres:
        return "audience:family"
    return "audience:general"

def _mood_tags(item: Dict[str, Any]) -> List[Tuple[str, float, str]]:
    """
    Returns list of (tag, confidence, reason). Lower confidence than other axes.
    """
    genres = set(_list_lower(item.get("Genres")))
    blob = _text_blob(item)
    r = _official_rating(item)

    out: List[Tuple[str, float, str]] = []

    def has(words: List[str]) -> bool:
        return any(w in blob for w in words)

    # Occasion
    if has(["christmas","santa","holiday","xmas","north pole","reindeer"]):
        out.append(("occasion:christmas", 0.80, "overview/tagline keywords"))
    if has(["halloween","pumpkin","witch","haunted","ghost","spooky"]):
        out.append(("occasion:halloween", 0.75, "overview/tagline keywords"))

    # Mood/tone
    if "horror" in genres or has(["terror","haunted","killer","slasher","demon"]):
        out.append(("mood:scary", 0.70, "genre/keywords"))
    if "comedy" in genres or has(["hilarious","funny","comedian","laugh"]):
        out.append(("mood:funny", 0.70, "genre/keywords"))
    if "action" in genres or has(["explosive","assassin","fight","battle","mission"]):
        out.append(("mood:action", 0.65, "genre/keywords"))
    if has(["heartwarming","friendship","gentle","cozy","wholesome","feel-good","feel good"]):
        out.append(("mood:cozy", 0.65, "keywords"))
    if has(["tearjerker","grief","loss","tragic","emotional"]):
        out.append(("mood:emotional", 0.65, "keywords"))
    if "thriller" in genres or "crime" in genres or has(["dark","corrupt","serial","noir"]):
        out.append(("mood:dark", 0.60, "genre/keywords"))

    # Safety dampener: if R/TV-MA, cozy/family-ish moods drop
    if r in {"R","TV-MA","NC-17"}:
        out = [(t,c,rsn) for (t,c,rsn) in out if t not in {"mood:cozy"}]

    return out

def _make_suggestion(s_type: str, title: str, confidence: float, item_ids: List[str], reason: str, payload: Dict[str, Any], now: int):
    return {
        "suggestion_id": str(uuid.uuid4()),
        "suggestion_type": s_type,
        "title": title,
        "confidence": float(confidence),
        "item_ids": item_ids,
        "reason": reason,
        "payload": payload,
        "created_at": now
    }

def build_suggestions(
    items: List[Dict[str, Any]],
    franchise_rules: Dict[str, List[str]],
    min_group_size: int,
    enable_franchise: bool,
    enable_studio: bool,
    enable_format: bool,
    enable_length: bool,
    enable_audience: bool,
    enable_mood: bool,
    studio_allowlist: List[str],
    top_studios: int
) -> List[Dict[str, Any]]:
    now = int(time.time())
    suggestions: List[Dict[str, Any]] = []

    # ----------------------
    # A) Franchise collections
    # ----------------------
    if enable_franchise:
        # Keyword-based franchise rules (strong)
        rule_groups = defaultdict(list)
        for it in items:
            name = it.get("Name") or ""
            norm = _normalize_title(name)
            for coll, kws in franchise_rules.items():
                if any(kw in norm for kw in kws):
                    rule_groups[coll].append(it.get("Id"))

        for coll_name, ids in rule_groups.items():
            if len(ids) >= min_group_size:
                suggestions.append(_make_suggestion(
                    "collection",
                    coll_name,
                    0.95,
                    ids,
                    "matched franchise keywords",
                    {"collection_name": coll_name},
                    now
                ))

        # Title sequel pattern (Police Academy 2: ..., Rocky II, Part 2)
        base_groups = defaultdict(list)
        sequel_flags = defaultdict(int)
        for it in items:
            name = it.get("Name") or ""
            base = _base_key(name)
            if not base:
                continue
            base_groups[base].append(it.get("Id"))
            if _has_sequel_marker(name):
                sequel_flags[base] += 1

        for base, ids in base_groups.items():
            if len(ids) < min_group_size:
                continue
            if sequel_flags[base] < 2 and len(ids) < 3:
                continue
            suggestions.append(_make_suggestion(
                "collection",
                base.title(),
                0.85,
                ids,
                "title sequel pattern (2/II/Part 2, subtitles)",
                {"collection_name": base.title()},
                now
            ))

    # ----------------------
    # B) Studio tags
    # ----------------------
    if enable_studio:
        # Count studios to choose top ones if allowlist not provided
        studio_counts = Counter()
        item_studios = {}
        for it in items:
            studs = _list_lower(it.get("Studios"))
            # Studios field can be list of dicts with Name; _list_lower handles
            canon_list = [_canon_studio(s) for s in studs if s.strip()]
            canon_list = [c for c in canon_list if c]
            item_studios[it.get("Id")] = canon_list
            for c in canon_list:
                studio_counts[c.lower()] += 1

        allowed = set([s.lower() for s in studio_allowlist if s]) if studio_allowlist else None
        if allowed is None:
            # Auto-select top studios, excluding very generic ones
            top = []
            for name_lc, cnt in studio_counts.most_common():
                if name_lc in GENERIC_STUDIOS:
                    continue
                top.append(name_lc)
                if len(top) >= top_studios:
                    break
            allowed = set(top)

        groups = defaultdict(list)
        for item_id, studios in item_studios.items():
            for st in studios:
                if st.lower() in allowed:
                    groups[st].append(item_id)

        for studio_name, ids in groups.items():
            if len(ids) >= min_group_size:
                tag = f"studio:{studio_name.lower().replace(' ', '_')}"
                suggestions.append(_make_suggestion(
                    "tag",
                    f"Studio: {studio_name}",
                    0.95,
                    ids,
                    "studio match",
                    {"tag": tag},
                    now
                ))

    # ----------------------
    # C) Format tags
    # ----------------------
    if enable_format:
        fmt_groups = defaultdict(list)
        for it in items:
            tag = _format_tag(it)
            fmt_groups[tag].append(it.get("Id"))

        fmt_titles = {
            "format:animation": "Format: Animation",
            "format:live_action": "Format: Live Action",
            "format:documentary": "Format: Documentary",
        }
        for tag, ids in fmt_groups.items():
            if len(ids) >= min_group_size and tag in fmt_titles:
                suggestions.append(_make_suggestion(
                    "tag",
                    fmt_titles[tag],
                    0.88,
                    ids,
                    "genre-based format",
                    {"tag": tag},
                    now
                ))

    # ----------------------
    # D) Length tags
    # ----------------------
    if enable_length:
        len_groups = defaultdict(list)
        for it in items:
            tag = _length_tag(it)
            len_groups[tag].append(it.get("Id"))

        len_titles = {
            "length:short": "Length: Short (≤75m)",
            "length:standard": "Length: Standard (76–110m)",
            "length:long": "Length: Long (111–140m)",
            "length:epic": "Length: Epic (>140m)",
        }
        for tag, ids in len_groups.items():
            if len(ids) >= min_group_size and tag in len_titles:
                suggestions.append(_make_suggestion(
                    "tag",
                    len_titles[tag],
                    0.80,
                    ids,
                    "runtime-based",
                    {"tag": tag},
                    now
                ))

    # ----------------------
    # E) Audience tags
    # ----------------------
    if enable_audience:
        aud_groups = defaultdict(list)
        for it in items:
            tag = _audience_tag(it)
            aud_groups[tag].append(it.get("Id"))

        aud_titles = {
            "audience:kids": "Audience: Kids",
            "audience:family": "Audience: Family",
            "audience:teens": "Audience: Teens",
            "audience:adults": "Audience: Adults",
            "audience:general": "Audience: General",
        }
        aud_conf = {
            "audience:kids": 0.85,
            "audience:family": 0.82,
            "audience:teens": 0.80,
            "audience:adults": 0.88,
            "audience:general": 0.70,
        }
        for tag, ids in aud_groups.items():
            if len(ids) >= min_group_size and tag in aud_titles:
                suggestions.append(_make_suggestion(
                    "tag",
                    aud_titles[tag],
                    aud_conf.get(tag, 0.75),
                    ids,
                    "official rating (+ genre inference if missing)",
                    {"tag": tag},
                    now
                ))

    # ----------------------
    # F) Mood/Occasion tags (can overlap; we keep them)
    # ----------------------
    if enable_mood:
        mood_groups = defaultdict(list)
        mood_reason = defaultdict(lambda: Counter())

        for it in items:
            item_id = it.get("Id")
            for tag, conf, rsn in _mood_tags(it):
                mood_groups[tag].append((item_id, conf))
                mood_reason[tag][rsn] += 1

        mood_titles = {
            "mood:cozy": "Mood: Cozy",
            "mood:funny": "Mood: Funny",
            "mood:action": "Mood: Action",
            "mood:dark": "Mood: Dark",
            "mood:emotional": "Mood: Emotional",
            "mood:scary": "Mood: Scary",
            "occasion:christmas": "Occasion: Christmas",
            "occasion:halloween": "Occasion: Halloween",
        }

        for tag, arr in mood_groups.items():
            ids = [i for (i, _) in arr]
            if len(ids) < min_group_size:
                continue
            # average confidence of contributing signals
            avg_conf = sum(c for _, c in arr) / max(1, len(arr))
            # keep conservative
            if avg_conf < 0.62:
                continue

            common_reason = mood_reason[tag].most_common(1)[0][0] if mood_reason[tag] else "keywords/genres"
            title = mood_titles.get(tag, f"Tag: {tag}")
            suggestions.append(_make_suggestion(
                "tag",
                title,
                min(0.78, avg_conf),  # cap mood confidence
                ids,
                common_reason,
                {"tag": tag},
                now
            ))

    # IMPORTANT: We do NOT dedupe across tag suggestions. Movies should get multiple tags.
    # We only keep sorting for UI readability.
    suggestions.sort(key=lambda s: (s["confidence"], len(s["item_ids"])), reverse=True)
    return suggestions
