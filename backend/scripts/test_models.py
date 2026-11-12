"""Time a tiny request against several models so you can pick a fast, available one.

Run from the backend folder (venv active):
    python scripts\\test_models.py
    python scripts\\test_models.py gemini-3.5-flash gemini-3.1-flash-lite   (your own list)
"""
import sys
import time

import httpx
from dotenv import dotenv_values

env = dotenv_values(".env")
for name in ("LLM_BASE_URL", "LLM_API_KEY"):
    if not env.get(name):
        sys.exit(f"{name} is missing in .env")

url = env["LLM_BASE_URL"].rstrip("/") + "/chat/completions"
headers = {"Authorization": "Bearer " + env["LLM_API_KEY"]}
models = sys.argv[1:] or [
    "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash",
    "gemini-3.7-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-flash-lite-latest",
]

print(f"{'model':32} {'result':10} seconds")
for m in models:
    start = time.time()
    try:
        r = httpx.post(url, headers=headers, timeout=60, json={
            "model": m, "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        })
        result = str(r.status_code)
    except httpx.HTTPError as exc:
        result = type(exc).__name__
    print(f"{m:32} {result:10} {time.time() - start:5.1f}")
print("\n200 + a low number of seconds = a good choice for LLM_MODEL. Use a different good one as LLM_FALLBACK_MODEL.")
