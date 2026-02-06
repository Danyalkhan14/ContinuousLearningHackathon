"""Orchestrator: generate Protocol, SAP, Summary Tables per trial with checkpointing."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from data_generator.config import Config
from data_generator.builders import build_protocol, build_sap, build_summary_tables
from data_generator.ctgov_generator import write_ctgov
from data_generator.trial_context import get_trial_context

logger = logging.getLogger(__name__)

CHECKPOINT_FILENAME = "checkpoint.json"


def load_checkpoint(output_dir: Path) -> Dict[str, Any]:
    """Load checkpoint if it exists."""
    path = output_dir / CHECKPOINT_FILENAME
    if not path.exists():
        return {"trials_done": [], "total_words": 0, "last_trial_id": None}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not load checkpoint: %s", e)
        return {"trials_done": [], "total_words": 0, "last_trial_id": None}


def save_checkpoint(
    output_dir: Path,
    trials_done: List[str],
    total_words: int,
    last_trial_id: Optional[str] = None,
) -> None:
    """Save checkpoint."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / CHECKPOINT_FILENAME
    with open(path, "w") as f:
        json.dump(
            {
                "trials_done": trials_done,
                "total_words": total_words,
                "last_trial_id": last_trial_id,
            },
            f,
            indent=2,
        )


def run_trial(
    trial_id: str,
    output_dir: Path,
    trial_context: Optional[Dict[str, Any]] = None,
    config: Optional[Config] = None,
    client: Optional[OpenAI] = None,
    reasoning_effort: Optional[str] = None,
) -> int:
    """
    Generate Protocol, SAP, and Summary Tables for one trial.
    Writes protocol.txt, sap.txt, summary_tables.txt under output_dir/trial_id/.

    Args:
        reasoning_effort: Optional GPT-5.2 reasoning effort
                          ("none", "low", "medium", "high", "xhigh").

    Returns total word count for this trial.
    """
    config = config or Config()
    client = client or OpenAI(api_key=config.api_key)
    trial_dir = output_dir / trial_id
    trial_dir.mkdir(parents=True, exist_ok=True)

    # Optional: write ctgov.json for CliniRepGen ingest
    if trial_context:
        nct_num = abs(hash(trial_id)) % 10**8
        nct_id = f"NCT{nct_num:08d}"
        write_ctgov(trial_dir / "ctgov.json", trial_context, trial_id=trial_id, nct_id=nct_id)

    total = 0
    total += build_protocol(
        trial_dir / "protocol.txt",
        trial_context=trial_context,
        trial_id=trial_id,
        config=config,
        client=client,
        reasoning_effort=reasoning_effort,
    )
    total += build_sap(
        trial_dir / "sap.txt",
        trial_context=trial_context,
        trial_id=trial_id,
        config=config,
        client=client,
        reasoning_effort=reasoning_effort,
    )
    total += build_summary_tables(
        trial_dir / "summary_tables.txt",
        trial_context=trial_context,
        trial_id=trial_id,
        config=config,
        client=client,
        reasoning_effort=reasoning_effort,
    )
    return total


def run(
    output_dir: str = "synthetic_output",
    num_trials: int = 1,
    resume: bool = True,
    start_index: int = 0,
    seed: Optional[int] = None,
    config: Optional[Config] = None,
    reasoning_effort: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main entry: generate Minimal Viable Dataset for num_trials (trial_001, trial_002, ...).

    Uses GPT-5.2 by default (configurable via config.model).
    If resume=True, skip trials already in checkpoint.

    Args:
        reasoning_effort: Optional GPT-5.2 reasoning effort
                          ("none", "low", "medium", "high", "xhigh").
    """
    config = config or Config()
    output_path = Path(output_dir)
    checkpoint = load_checkpoint(output_path) if resume else {}
    trials_done = checkpoint.get("trials_done", [])
    total_words = checkpoint.get("total_words", 0)
    client = OpenAI(api_key=config.api_key)

    for i in range(start_index, start_index + num_trials):
        trial_id = f"trial_{i+1:03d}"
        if trial_id in trials_done:
            logger.info("Skipping already done trial: %s", trial_id)
            continue
        trial_context = get_trial_context(i, seed=seed)
        logger.info("Starting trial %s (%s)", trial_id, trial_context.get("brief_title", "")[:60])
        try:
            words = run_trial(
                trial_id,
                output_path,
                trial_context=trial_context,
                config=config,
                client=client,
                reasoning_effort=reasoning_effort,
            )
            total_words += words
            trials_done.append(trial_id)
            save_checkpoint(output_path, trials_done, total_words, trial_id)
            pages = total_words // config.words_per_page
            logger.info(
                "Trial %s done: %s words (%s pages total so far)",
                trial_id,
                words,
                pages,
            )
        except Exception as e:
            logger.exception("Trial %s failed: %s", trial_id, e)
            raise

    return {
        "trials_done": trials_done,
        "total_words": total_words,
        "total_pages": total_words // config.words_per_page,
    }
