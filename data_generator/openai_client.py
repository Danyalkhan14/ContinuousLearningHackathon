"""OpenAI API client for section generation with retries and backoff.

Explicitly supports GPT-5.2 via the Chat Completions API (v1/chat/completions).
Ref: https://platform.openai.com/docs/models/gpt-5.2

GPT-5.2 API notes:
  - Model IDs: "gpt-5.2" (latest), "gpt-5.2-2025-12-11" (snapshot)
  - Context window: 400,000 tokens
  - Max output: 128,000 tokens per response
  - Uses ``max_completion_tokens`` (NOT the legacy ``max_tokens``)
  - Supports ``reasoning_effort``: none (default), low, medium, high, xhigh
  - Temperature is supported and useful for controlling creativity
"""

import logging
import time
from typing import Any, Dict, Optional

from openai import OpenAI

from data_generator.config import Config, SUPPORTED_MODELS
from data_generator.prompts.templates import (
    SYSTEM_PROMPT,
    build_protocol_section_prompt,
    build_sap_section_prompt,
    build_summary_tables_section_prompt,
)
from data_generator.consort_sections import SectionSpec

logger = logging.getLogger(__name__)

# Valid reasoning_effort values for GPT-5.2
VALID_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh"}


def _validate_model(model: str) -> None:
    """Warn (not error) if the model is not in the known-good list."""
    if model not in SUPPORTED_MODELS:
        logger.warning(
            "Model '%s' is not in the explicitly supported list %s. "
            "Proceeding anyway — the API will reject if the model ID is invalid.",
            model,
            SUPPORTED_MODELS,
        )


def _build_api_kwargs(
    config: Config,
    messages: list,
    reasoning_effort: Optional[str] = None,
) -> Dict[str, Any]:
    """Build keyword arguments for client.chat.completions.create().

    GPT-5.2 uses ``max_completion_tokens`` instead of the legacy ``max_tokens``.
    Reasoning effort is optionally forwarded when the caller wants deeper
    chain-of-thought from the model.
    """
    kwargs: Dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "max_completion_tokens": config.max_completion_tokens,
        "temperature": 0.3,
    }

    # Only include reasoning_effort if explicitly requested (GPT-5.2 feature).
    # Default for GPT-5.2 is "none" so we omit it unless caller overrides.
    if reasoning_effort is not None:
        if reasoning_effort not in VALID_REASONING_EFFORTS:
            logger.warning(
                "Invalid reasoning_effort '%s'; valid values: %s. Omitting.",
                reasoning_effort,
                VALID_REASONING_EFFORTS,
            )
        else:
            kwargs["reasoning_effort"] = reasoning_effort

    return kwargs


def generate_section(
    doc_type: str,
    section: SectionSpec,
    trial_context: Optional[Dict[str, Any]] = None,
    config: Optional[Config] = None,
    client: Optional[OpenAI] = None,
    reasoning_effort: Optional[str] = None,
) -> str:
    """
    Generate one section of a trial document via OpenAI Chat Completions.

    Uses GPT-5.2 by default (configurable via ``config.model``).

    Args:
        doc_type: One of "protocol", "sap", "summary_tables".
        section: SectionSpec with heading, description, target_words.
        trial_context: Optional dict with indication, drug_name, design,
                       n_participants, brief_title.
        config: Config for model and API key; uses default if None.
        client: Optional OpenAI client; creates one from config if None.
        reasoning_effort: Optional GPT-5.2 reasoning effort level
                          ("none", "low", "medium", "high", "xhigh").
                          Defaults to None (model default).

    Returns:
        Generated text (should start with the section heading).
    """
    config = config or Config()
    _validate_model(config.model)
    if client is None:
        client = OpenAI(api_key=config.api_key)

    if doc_type == "protocol":
        user_prompt = build_protocol_section_prompt(section, trial_context)
    elif doc_type == "sap":
        user_prompt = build_sap_section_prompt(section, trial_context)
    elif doc_type == "summary_tables":
        user_prompt = build_summary_tables_section_prompt(
            section, trial_context
        )
    else:
        raise ValueError(f"Unknown doc_type: {doc_type}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    api_kwargs = _build_api_kwargs(config, messages, reasoning_effort)

    last_error = None
    for attempt in range(config.max_retries):
        try:
            if config.delay_between_calls_sec and attempt > 0:
                time.sleep(config.delay_between_calls_sec)

            response = client.chat.completions.create(**api_kwargs)

            choice = response.choices[0]
            text = (choice.message.content or "").strip()
            if not text:
                raise ValueError("Empty response from API")

            # Log token usage for cost tracking
            if response.usage:
                logger.debug(
                    "Tokens — prompt: %s, completion: %s, total: %s",
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                    response.usage.total_tokens,
                )

            return text
        except Exception as e:
            last_error = e
            logger.warning(
                "OpenAI call attempt %s/%s failed: %s",
                attempt + 1,
                config.max_retries,
                e,
            )
            if attempt < config.max_retries - 1:
                time.sleep(2 ** attempt)  # exponential backoff
    raise RuntimeError(
        f"Failed after {config.max_retries} attempts: {last_error}"
    ) from last_error
