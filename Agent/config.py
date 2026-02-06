"""
Configuration for the CONSORT Deep Research Agent.

All settings are loaded from environment variables (or a .env file).
Uses GPT-5.2 via the OpenAI Chat Completions API.

API reference: https://platform.openai.com/docs/api-reference/chat/create
  - model: "gpt-5.2"
  - messages use "developer" role (not "system")
  - max_completion_tokens (not the deprecated max_tokens)
  - reasoning_effort: none | minimal | low | medium | high | xhigh
  - verbosity: low | medium | high
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


_PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application settings – populated from env vars / .env file."""

    # ── OpenAI ──────────────────────────────────────────────────────────
    openai_api_key: str = Field(..., description="OpenAI API key")

    # ── Qdrant (Akash-hosted) ──────────────────────────────────────────
    qdrant_url: str = Field(..., description="Qdrant REST endpoint URL")
    qdrant_api_key: Optional[str] = Field(
        default=None, description="Qdrant API key (if auth is enabled)"
    )
    qdrant_collection_name: str = Field(
        default="clinical_trial_docs",
        description="Name of the Qdrant collection",
    )

    # ── You.com Web Search ─────────────────────────────────────────────
    ydc_api_key: str = Field(..., description="You.com Data API key")

    # ── Embedding model ────────────────────────────────────────────────
    embedding_model: str = Field(
        default="text-embedding-3-large",
        description="OpenAI embedding model ID",
    )
    embedding_dimensions: int = Field(
        default=3072,
        description="Dimensionality of the embedding vectors",
    )

    # ── LLM (GPT-5.2) ─────────────────────────────────────────────────
    llm_model: str = Field(
        default="gpt-5.2",
        description="OpenAI chat model ID",
    )
    llm_max_completion_tokens: int = Field(
        default=16384,
        description="Max output tokens per Chat Completions call",
    )
    llm_reasoning_effort: str = Field(
        default="low",
        description="Reasoning effort: none | minimal | low | medium | high | xhigh",
    )

    # ── Paths ──────────────────────────────────────────────────────────
    consort_json_path: Path = Field(
        default=_PROJECT_ROOT / "consort.json",
        description="Path to the CONSORT 2025 checklist JSON",
    )

    class Config:
        env_file = str(_PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
