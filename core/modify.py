# core/modify.py

import re
from typing import Dict, List, Any

EM_DASH = "–"  # U+2013/2014 may appear; we'll handle both
DASH_RE = re.compile(r"[–—-]")  # em/en/hyphen
JOB_PREFIX_RE = re.compile(r"^\s*job:\s*", re.IGNORECASE)

def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items or []:
        if not isinstance(x, str):
            continue
        s = x.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out

def _norm_list(xs) -> List[str]:
    if isinstance(xs, str):
        # tolerate "$" or "," separated strings
        parts = [p.strip() for p in re.split(r"[\$,]", xs) if p.strip()]
        return _dedupe_keep_order(parts)
    if isinstance(xs, list):
        return _dedupe_keep_order([str(x).strip() for x in xs if isinstance(x, (str, int, float))])
    return []

def _get(d: Dict[str, Any], *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def _clean_role(header: str) -> str:
    """
    From headers like:
      'Job: Data Engineer – TEKsystems Global Services (Sep 2022 – Dec 2023)'
    return only:
      'Data Engineer'
    Robust to different dashes and no-company formats.
    """
    if not header:
        return ""
    h = JOB_PREFIX_RE.sub("", header.strip())
    # Split at first dash variant to separate role vs the rest
    m = DASH_RE.search(h)
    if m:
        role = h[: m.start()].strip()
    else:
        # Fallback: stop before first '(' if present
        role = h.split("(", 1)[0].strip()
    # Drop any trailing colon-like artifacts
    role = re.sub(r"[:\s]+$", "", role)
    # Collapse spaces
    role = re.sub(r"\s+", " ", role)
    return role

def json_convert(data: dict) -> dict:
    """
    Convert model JSON to the preset schema your DOCX expects.

    Input:
      data = {
        "missing_skills": {...},
        "experience_bullets": {"<Job: Title – Company (Dates)>": [bullets], ...},
        "project_bullets": {"<Project: Name (Dates)>": [bullets], ...}
      }

    Output:
      {
        "TITLE_MAIN", "TITLE_SUB", "TITLE_INTERN",
        "EXTRA_COURSEWORK",
        "EXTRA_PROGRAMMING","EXTRA_DE","EXTRA_CLOUD","EXTRA_DB","EXTRA_AI","EXTRA_MISC",
        "EXTRA_BULLETS_TEK","EXTRA_BULLETS_ASSOCIATE","EXTRA_BULLETS_INTERN",
        "EXTRA_ECOMMERCE","EXTRA_HOSPITAL"
      }
    """
    # ---------- start preset (skills from missing_skills buckets) ----------
    out = {
        "TITLE_MAIN": "",
        "TITLE_SUB": "",
        "TITLE_INTERN": "",

        "EXTRA_COURSEWORK": [],  # left empty unless you map something into it

        "EXTRA_PROGRAMMING": _norm_list(_get(data, "missing_skills", "Programming", default=[])),
        "EXTRA_DE":          _norm_list(_get(data, "missing_skills", "Data Engineering", default=[])),
        "EXTRA_CLOUD":       _norm_list(_get(data, "missing_skills", "Cloud", default=[])),
        "EXTRA_DB":          _norm_list(_get(data, "missing_skills", "Database", default=[])),
        "EXTRA_AI":          _norm_list(_get(data, "missing_skills", "ML/AI", default=[])),
        "EXTRA_MISC":        _norm_list(_get(data, "missing_skills", "Misc", default=[])),

        "EXTRA_BULLETS_TEK": [],
        "EXTRA_BULLETS_ASSOCIATE": [],
        "EXTRA_BULLETS_INTERN": [],

        "EXTRA_ECOMMERCE": [],
        "EXTRA_HOSPITAL":  [],
    }

    # ---------- map experience bullets ----------
    exp: Dict[str, List[str]] = _get(data, "experience_bullets", default={}) or {}
    main_set = False

    for header, bullets in exp.items():
        header_str = str(header or "")
        h_low = header_str.lower()
        blist = _norm_list(bullets)

        # Titles
        if "intern" in h_low:
            if not out["TITLE_INTERN"]:
                out["TITLE_INTERN"] = _clean_role(header_str)
            out["EXTRA_BULLETS_INTERN"].extend(blist)
            continue

        if "junior" in h_low or "associate" in h_low:
            if not out["TITLE_SUB"]:
                out["TITLE_SUB"] = _clean_role(header_str)
            out["EXTRA_BULLETS_ASSOCIATE"].extend(blist)
            continue

        # Treat first non-intern/non-associate as main
        if not main_set:
            out["TITLE_MAIN"] = _clean_role(header_str)
            main_set = True

        # TEK-specific (keep as per your original schema)
        if "teksystems" in h_low or "tek systems" in h_low:
            out["EXTRA_BULLETS_TEK"].extend(blist)
        else:
            # If you want separate buckets for other employers, add them here.
            out["EXTRA_BULLETS_TEK"].extend(blist)

    # Deduplicate experience bullets while preserving order
    out["EXTRA_BULLETS_TEK"]        = _dedupe_keep_order(out["EXTRA_BULLETS_TEK"])
    out["EXTRA_BULLETS_ASSOCIATE"]  = _dedupe_keep_order(out["EXTRA_BULLETS_ASSOCIATE"])
    out["EXTRA_BULLETS_INTERN"]     = _dedupe_keep_order(out["EXTRA_BULLETS_INTERN"])

    # ---------- map projects ----------
    projects: Dict[str, List[str]] = _get(data, "project_bullets", default={}) or {}
    for header, bullets in projects.items():
        header_str = str(header or "")
        h_low = header_str.lower()
        blist = _norm_list(bullets)

        if "e-commerce" in h_low or "ecommerce" in h_low:
            out["EXTRA_ECOMMERCE"].extend(blist)
        elif "hospital" in h_low:
            out["EXTRA_HOSPITAL"].extend(blist)
        else:
            # Add additional project buckets here if needed
            pass

    out["EXTRA_ECOMMERCE"] = _dedupe_keep_order(out["EXTRA_ECOMMERCE"])
    out["EXTRA_HOSPITAL"]  = _dedupe_keep_order(out["EXTRA_HOSPITAL"])

    return out