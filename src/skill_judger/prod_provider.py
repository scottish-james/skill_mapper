"""GenAI Gateway path. Uses auth.py's JWT, model_config.yaml's models list,
and per-model rate limiting/rotation to call the real gateway, following the
request/response contract proven in old_code.py: POST {messages,
temperature} with a Bearer token, OpenAI-shaped response."""
import json

import requests

from skill_judger.auth import authenticate
from skill_judger.config import load_model_config
from skill_judger.grader import StopGrading
from skill_judger.rate_limiter import ModelRotator

DEFAULT_TIMEOUT_SECONDS = 60
COOLDOWN_SECONDS_429 = 60
COOLDOWN_SECONDS_ERROR = 10

_cached_token = None
_rotator = None
_total_tokens_used = 0


def get_token() -> str:
    """Fetch and cache the JWT for this process. Call this once upfront
    before a run starts, so a bad credential fails fast instead of being
    retried 3x per row by grader.py's retry logic."""
    global _cached_token
    if _cached_token is None:
        _cached_token = authenticate()
    return _cached_token


def _get_rotator(config: dict) -> ModelRotator:
    global _rotator
    if _rotator is None:
        models = [
            m for m in config.get("models", [])
            if m.get("type") == "chat" and m.get("enabled", True)
        ]
        _rotator = ModelRotator(models, config["limits"])
    return _rotator


def _check_daily_budget(config: dict) -> None:
    limits = config["limits"]
    budget = limits["max_token_per_day"] - limits["daily_token_buffer"]
    if _total_tokens_used >= budget:
        raise StopGrading(
            f"Daily token budget reached: {_total_tokens_used:,}/{budget:,}"
        )


def classify_row(prompt_config: dict, row: dict) -> dict:
    """Send one CSV row to the gateway and return the parsed JSON dict."""
    global _total_tokens_used

    config = load_model_config()
    _check_daily_budget(config)

    timeout = config.get("http", {}).get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    rotator = _get_rotator(config)
    model = rotator.pick_model()
    print(f"  Using model: {model['id']}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_token()}",
    }
    payload = {
        "messages": [
            {"role": "system", "content": prompt_config["system_prompt"]},
            {"role": "user", "content": prompt_config["user_template"].format(**row)},
        ],
        "temperature": 0,
    }

    try:
        response = requests.post(model["url"], headers=headers, json=payload, timeout=timeout)
    except requests.RequestException:
        rotator.record_cooldown(model["id"], COOLDOWN_SECONDS_ERROR)
        raise

    if response.status_code == 429:
        rotator.record_cooldown(model["id"], COOLDOWN_SECONDS_429)
    elif response.status_code >= 500:
        rotator.record_cooldown(model["id"], COOLDOWN_SECONDS_ERROR)

    response.raise_for_status()

    result = response.json()
    tokens_used = result.get("usage", {}).get("total_tokens", 0)
    rotator.record_success(model["id"], tokens_used)
    _total_tokens_used += tokens_used

    reply = result["choices"][0]["message"]["content"]
    return json.loads(reply)
