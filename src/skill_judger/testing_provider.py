"""Local/dev-only OpenAI path. Delete this file (and its hook in
orchestrator.py) before going to prod — it has no role there."""
import json
import os

from openai import OpenAI

OPENAI_TEST_MODEL = "gpt-4o"


def _client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in your .env")
    return OpenAI(api_key=api_key)


def run_testing():
    response = _client().chat.completions.create(
        model=OPENAI_TEST_MODEL,
        messages=[{"role": "user", "content": "Reply with 'ready' only."}],
    )
    print(f"OpenAI ({OPENAI_TEST_MODEL}) connected:", response.choices[0].message.content)


def classify_row(prompt_config: dict, row: dict) -> dict:
    """Send one CSV row to gpt-4o using prompt_config's system_prompt and
    user_template (templated with that row's fields), and return the parsed
    JSON dict. Knows nothing about specific field names — the YAML template
    defines what's expected."""
    user_content = prompt_config["user_template"].format(**row)
    response = _client().chat.completions.create(
        model=OPENAI_TEST_MODEL,
        messages=[
            {"role": "system", "content": prompt_config["system_prompt"]},
            {"role": "user", "content": user_content},
        ],
    )

    return json.loads(response.choices[0].message.content)
