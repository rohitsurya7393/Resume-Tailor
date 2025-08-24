import streamlit as st

def call_gpt(client, system_prompt: str, user_prompt: str,
             model: str = "gpt-4o-mini", temperature: float = 0.25,
             max_tokens: int = 2800) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content