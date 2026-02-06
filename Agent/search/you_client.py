"""
You.com web search client for term hydration.

Uses the You.com Search API (https://documentation.you.com/api-reference/search)
via the LangChain community integration to look up definitions of unfamiliar
clinical / statistical terms encountered during retrieval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from langchain_community.utilities.you import YouSearchAPIWrapper

from config import Settings

logger = logging.getLogger(__name__)


@dataclass
class WebSearchResult:
    """A single web search result."""

    query: str
    snippet: str
    url: str
    title: str


class YouSearchClient:
    """Wrapper around You.com's web search for term definition hydration."""

    def __init__(self, settings: Settings) -> None:
        self._wrapper = YouSearchAPIWrapper(
            ydc_api_key=settings.ydc_api_key,
            num_web_results=3,
        )

    def search_term(self, term: str) -> list[WebSearchResult]:
        """
        Search for a clinical / statistical term and return relevant snippets.

        Args:
            term: The term or phrase to look up (e.g. "ANCOVA", "non-inferiority margin").

        Returns:
            List of WebSearchResult with the top web results.
        """
        query = f"definition of {term} in clinical trials"
        logger.info("You.com search: '%s'", query)

        try:
            raw_results = self._wrapper.results(query)
        except Exception:
            logger.exception("You.com search failed for '%s'", query)
            return []

        results: list[WebSearchResult] = []
        if isinstance(raw_results, list):
            for item in raw_results:
                results.append(
                    WebSearchResult(
                        query=query,
                        snippet=item.get("snippet", item.get("description", "")),
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                    )
                )
        elif isinstance(raw_results, str):
            # Some wrapper versions return a single string
            results.append(
                WebSearchResult(
                    query=query,
                    snippet=raw_results,
                    url="",
                    title="",
                )
            )

        logger.info("You.com returned %d results for '%s'", len(results), term)
        return results

    def hydrate_terms(self, terms: list[str]) -> dict[str, str]:
        """
        Look up multiple terms and return a {term: definition} mapping.

        Useful for batch-hydrating all unfamiliar terms flagged by the
        evaluate node.
        """
        definitions: dict[str, str] = {}
        for term in terms:
            results = self.search_term(term)
            if results:
                # Concatenate the top snippets into a definition
                combined = " ".join(r.snippet for r in results[:2] if r.snippet)
                definitions[term] = combined
            else:
                definitions[term] = f"No definition found for '{term}'."
        return definitions
