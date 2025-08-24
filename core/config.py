# core/config.py
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def _safe_secret(key: str):
    """Return st.secrets[key] if secrets are configured; else None."""
    try:
        # Using .get still triggers parse when secrets.toml is missing.
        return st.secrets.get(key, None)  # guarded by try/except
    except Exception:
        return None

def get_experience_text() -> str:
    """
    Load fixed experience from (in order):
      1) ENV var RESUME_EXPERIENCE (via .env or exported)
      2) Streamlit secrets (RESUME_EXPERIENCE) if present
      3) local 'experience.txt'
    """
    exp = os.getenv("RESUME_EXPERIENCE")
    if not exp:
        exp = _safe_secret("RESUME_EXPERIENCE")
    if exp:
        return exp.strip()

    if os.path.exists("experience.txt"):
        return open("experience.txt", "r", encoding="utf-8").read().strip()

    return "YOUR EXPERIENCE TEXT NOT FOUND. Please set RESUME_EXPERIENCE env var or create experience.txt."

@st.cache_resource
def get_openai_client():
    from openai import OpenAI
    key = os.getenv("OPENAI_API_KEY")
    try:
        if not key:
            key = st.secrets.get("OPENAI_API_KEY")  # guarded by try/except in your setup
    except Exception:
        pass
    return OpenAI(api_key=key) if key else None