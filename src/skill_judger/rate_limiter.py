"""Per-model rate limiting and rotation, ported from old_code.py's
model_state/pick_next_model/wait_for_any_model logic. Strategy: exhaust one
model until its per-minute limits are hit or it 429s, then move to the next,
returning to earlier models automatically once their rolling window resets
(pick_model always scans from the start of the list)."""
import time

ESTIMATED_TOKENS_PER_CALL = 3_500
DEFAULT_COOLDOWN_SECONDS = 60


class ModelRotator:
    def __init__(self, models: list, limits: dict):
        if not models:
            raise RuntimeError("No enabled chat models to rotate across")
        self._limits = limits
        self._state = {
            model["id"]: {
                "spec": model,
                "calls_this_minute": 0,
                "tokens_this_minute": 0,
                "minute_start": time.time(),
                "cooldown_until": 0.0,
            }
            for model in models
        }

    def _reset_minute_window_if_due(self, state: dict) -> None:
        if time.time() - state["minute_start"] >= 60:
            state["calls_this_minute"] = 0
            state["tokens_this_minute"] = 0
            state["minute_start"] = time.time()

    def _is_available(self, state: dict, estimated_tokens: int = ESTIMATED_TOKENS_PER_CALL) -> bool:
        self._reset_minute_window_if_due(state)
        if time.time() < state["cooldown_until"]:
            return False
        if state["calls_this_minute"] + 1 > self._limits["max_call_per_min"]:
            return False
        if state["tokens_this_minute"] + estimated_tokens > self._limits["max_token_per_min"]:
            return False
        return True

    def pick_model(self) -> dict:
        """Return the spec of the first available model, waiting if none are."""
        while True:
            for state in self._state.values():
                if self._is_available(state):
                    return state["spec"]
            self._wait_for_any()

    def _wait_for_any(self) -> None:
        now = time.time()
        earliest = float("inf")
        for state in self._state.values():
            if state["cooldown_until"] > now:
                earliest = min(earliest, state["cooldown_until"])
            window_end = state["minute_start"] + 60
            calls_exhausted = state["calls_this_minute"] >= self._limits["max_call_per_min"]
            tokens_exhausted = (
                state["tokens_this_minute"] + ESTIMATED_TOKENS_PER_CALL
                > self._limits["max_token_per_min"]
            )
            if window_end > now and (calls_exhausted or tokens_exhausted):
                earliest = min(earliest, window_end)

        wait_time = 5.0 if earliest == float("inf") else max(1.0, earliest - now + 0.5)
        print(f"All models are busy or cooling down. Sleeping {wait_time:.1f}s...")
        time.sleep(wait_time)

    def record_success(self, model_id: str, tokens_used: int) -> None:
        state = self._state[model_id]
        state["calls_this_minute"] += 1
        state["tokens_this_minute"] += tokens_used

    def record_cooldown(self, model_id: str, seconds: float = DEFAULT_COOLDOWN_SECONDS) -> None:
        self._state[model_id]["cooldown_until"] = time.time() + seconds
