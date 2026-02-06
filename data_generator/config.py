"""Configuration for synthetic data generation.

Explicitly supports OpenAI GPT-5.2 (released 2025-12-11).
Ref: https://platform.openai.com/docs/models/gpt-5.2

GPT-5.2 specs:
  - API model IDs: "gpt-5.2" (latest alias), "gpt-5.2-2025-12-11" (snapshot)
  - Context window: 400,000 tokens
  - Max output tokens: 128,000
  - Pricing: $1.75 / 1M input, $14.00 / 1M output
  - Cached input: $0.175 / 1M tokens
  - Supports: Chat Completions (v1/chat/completions), Responses API,
    function calling, structured outputs, streaming
  - Reasoning effort: none (default), low, medium, high, xhigh
"""

import os
from pathlib import Path
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Page definition: 1 page = 300 words
WORDS_PER_PAGE = 300

# Per-trial page targets (Minimal Viable Dataset)
PROTOCOL_PAGES_MIN = 60
PROTOCOL_PAGES_MAX = 80
SAP_PAGES_MIN = 20
SAP_PAGES_MAX = 30
SUMMARY_TABLES_PAGES_MIN = 30
SUMMARY_TABLES_PAGES_MAX = 40

# Supported models (GPT-5.2 series)
SUPPORTED_MODELS = [
    "gpt-5.2",                # Latest alias (recommended)
    "gpt-5.2-2025-12-11",     # Pinned snapshot
]

# GPT-5.2 limits
GPT_5_2_CONTEXT_WINDOW = 400_000     # tokens
GPT_5_2_MAX_OUTPUT_TOKENS = 128_000  # tokens


@dataclass
class Config:
    """Generator configuration.

    Default model: gpt-5.2 (OpenAI GPT-5.2, Chat Completions API).
    See https://platform.openai.com/docs/models/gpt-5.2 for details.
    """

    output_dir: str = "synthetic_output"
    model: str = "gpt-5.2"
    max_completion_tokens: int = 16_384  # Per-call output limit (well within 128k max)
    delay_between_calls_sec: float = 1.0
    checkpoint_path: str = "synthetic_output/checkpoint.json"
    max_retries: int = 3
    words_per_page: int = WORDS_PER_PAGE

    # Page targets per trial
    protocol_pages_min: int = PROTOCOL_PAGES_MIN
    protocol_pages_max: int = PROTOCOL_PAGES_MAX
    sap_pages_min: int = SAP_PAGES_MIN
    sap_pages_max: int = SAP_PAGES_MAX
    summary_tables_pages_min: int = SUMMARY_TABLES_PAGES_MIN
    summary_tables_pages_max: int = SUMMARY_TABLES_PAGES_MAX

    @property
    def api_key(self) -> str:
        """OpenAI API key from environment."""
        key = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")
        if not key:
            raise ValueError(
                "Set OPENAI_API_KEY or API_KEY in environment or .env"
            )
        return key

    def protocol_words_min(self) -> int:
        return self.protocol_pages_min * self.words_per_page

    def protocol_words_max(self) -> int:
        return self.protocol_pages_max * self.words_per_page

    def sap_words_min(self) -> int:
        return self.sap_pages_min * self.words_per_page

    def sap_words_max(self) -> int:
        return self.sap_pages_max * self.words_per_page

    def summary_tables_words_min(self) -> int:
        return self.summary_tables_pages_min * self.words_per_page

    def summary_tables_words_max(self) -> int:
        return self.summary_tables_pages_max * self.words_per_page
