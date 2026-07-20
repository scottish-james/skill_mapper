"""Local/dev-only OpenAI path. Delete this file (and its two-line hook in
orchestrator.py) before going to prod — it has no role there."""
import os

from openai import OpenAI

OPENAI_TEST_MODEL = "gpt-4o"


def run_testing():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY in your .env")
        return

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=OPENAI_TEST_MODEL,
        messages=[{"role": "user", "content": "Reply with 'ready' only."}],
    )
    print(f"OpenAI ({OPENAI_TEST_MODEL}) connected:", response.choices[0].message.content)
