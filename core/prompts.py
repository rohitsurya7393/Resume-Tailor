# prompts.py

SYSTEM_PROMPT = (
    "You are an expert resume tailor for data engineering roles. "
    "Use ONLY the candidate's provided experience/skills (no fabrication). "
    "Preserve the core project/experience architecture; do not invent roles, companies, dates, or tools. "
    "Organize skills into exactly these buckets: Programming, Data Engineering, Cloud, Database, ML/AI, Misc. "
    "Return ONLY a single valid JSON object. No markdown, no code fences, no explanations."
)

def build_user_prompt(job_description: str, experience_text: str, skill_inventory: dict, buckets: list) -> str:
    """
    JSON-only prompt:
      - keywords: top JD terms per bucket
      - missing_skills: truly missing vs. the given skill_inventory, per bucket
      - experience_bullets: tailored bullets per Job (keep jobs separate; keys are the exact Job headers)
      - project_bullets: tailored bullets per Project (keep projects separate; keys are the exact Project headers)
    Bullet density & style constraints are explicit for longer/more detailed output.
    """
    return f"""
You will receive:
1) Job Description (JD).
2) Candidate experience text including:
   - [Skills] with bucketed lists
   - [Work Experience] sections like [Job: Title – Company (Dates)]
   - [Projects] sections like [Project: Name (Dates)]
3) A pre-parsed skill inventory grouped by buckets {buckets}.

TASKS:
A) Extract the top, high-signal JD keywords/phrases grouped by {buckets}. Keep lists concise and deduplicated.
B) Identify only the genuinely missing skills/keywords per bucket by comparing the JD to skill_inventory.
C) Generate ATS-friendly, quantifiable, and concise bullets tailored to the JD:
   - For EACH Job: produce 6–9 bullets.
   - For EACH Project: produce 4–6 bullets.
   - Target 18–28 words per bullet; start with a strong verb; weave in relevant JD terms; quantify impact where appropriate.
   - Do NOT invent employment, companies, dates, or tools; only rephrase facts to emphasize fit.
   - Avoid near-duplicates across jobs/projects; vary verbs and metrics.

OUTPUT (JSON only; no markdown/backticks/explanations):
{{
  "keywords": {{
    "Programming": [string],
    "Data Engineering": [string],
    "Cloud": [string],
    "Database": [string],
    "ML/AI": [string],
    "Misc": [string]
  }},
  "missing_skills": {{
    "Programming": [string],
    "Data Engineering": [string],
    "Cloud": [string],
    "Database": [string],
    "ML/AI": [string],
    "Misc": [string]
  }},
  "experience_bullets": {{
    "<Job: Title – Company (Dates)>": [string]
  }},
  "project_bullets": {{
    "<Project: Name (Dates)>": [string]
  }}
}}

DATA:
=== JOB DESCRIPTION ===
{job_description}

=== CANDIDATE EXPERIENCE (DO NOT CHANGE FACTS) ===
{experience_text}

=== CANDIDATE SKILL INVENTORY (BUCKETED) ===
{skill_inventory}
""".strip()