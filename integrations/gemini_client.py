"""Gemini API client wrapper with retry and cost tracking."""

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai not installed — Gemini client will raise on use")

MODEL_COSTS_PER_1K_TOKENS = {
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
}


class GeminiClient:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._total_cost_usd = 0.0
        self._call_count = 0

        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-generativeai is not installed. Run: pip install google-generativeai"
            )
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

        genai.configure(api_key=self._api_key)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.8,
        max_tokens: int = 2000,
        max_retries: int = 3,
    ) -> str:
        if not GENAI_AVAILABLE:
            raise RuntimeError("Gemini API is not available")

        gemini_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )

        last_error = None
        for attempt in range(max_retries):
            try:
                response = gemini_model.generate_content(user_prompt)
                text = response.text
                self._track_usage(model, system_prompt + user_prompt, text)
                self._call_count += 1
                return text
            except Exception as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(f"Gemini API attempt {attempt + 1} failed: {e} — retrying in {wait}s")
                time.sleep(wait)

        raise RuntimeError(f"Gemini API failed after {max_retries} attempts: {last_error}")

    def _track_usage(self, model: str, prompt_text: str, output_text: str) -> None:
        costs = MODEL_COSTS_PER_1K_TOKENS.get(model, {"input": 0.001, "output": 0.002})
        input_tokens = len(prompt_text) / 4
        output_tokens = len(output_text) / 4
        cost = (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])
        self._total_cost_usd += cost
        logger.debug(f"Gemini [{model}] ~${cost:.5f} | total=${self._total_cost_usd:.4f}")

    @property
    def total_cost_usd(self) -> float:
        return self._total_cost_usd

    @property
    def call_count(self) -> int:
        return self._call_count
