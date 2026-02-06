"""CLI entrypoint for synthetic trial data generation using GPT-5.2.

Usage:
    python -m data_generator --out ./synthetic_output [--model gpt-5.2] [--trials N] [--resume]

Supported models (GPT-5.2 series):
    gpt-5.2              Latest alias (recommended)
    gpt-5.2-2025-12-11   Pinned snapshot

Ref: https://platform.openai.com/docs/models/gpt-5.2
"""

import argparse
import logging
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from data_generator.config import Config, SUPPORTED_MODELS
from data_generator.orchestrator import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Minimal Viable Dataset (100-150 pp per trial) for "
            "CliniRepGen: Protocol, SAP, Summary Tables.  "
            "Uses GPT-5.2 by default (https://platform.openai.com/docs/models/gpt-5.2)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Supported models:\n"
            + "\n".join(f"  {m}" for m in SUPPORTED_MODELS)
            + "\n\nGPT-5.2 specs:\n"
            "  Context window:   400,000 tokens\n"
            "  Max output:       128,000 tokens\n"
            "  Pricing:          $1.75/1M input, $14.00/1M output\n"
            "  Reasoning effort: none (default), low, medium, high, xhigh\n"
            "\nRef: https://platform.openai.com/docs/models/gpt-5.2"
        ),
    )
    parser.add_argument(
        "--out",
        "-o",
        default="synthetic_output",
        help="Output directory (default: synthetic_output)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="gpt-5.2",
        help=(
            "OpenAI model ID (default: gpt-5.2). "
            "Supported: " + ", ".join(SUPPORTED_MODELS)
        ),
    )
    parser.add_argument(
        "--max-completion-tokens",
        type=int,
        default=16_384,
        help=(
            "Max completion tokens per API call (default: 16384). "
            "GPT-5.2 supports up to 128,000."
        ),
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh"],
        default=None,
        help=(
            "GPT-5.2 reasoning effort level. "
            "Higher values produce deeper chain-of-thought but cost more. "
            "Default: none (model default, no extra reasoning tokens)."
        ),
    )
    parser.add_argument(
        "--trials",
        "-n",
        type=int,
        default=1,
        help="Number of trials to generate (default: 1)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint (skip already completed trials)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not resume; start fresh (ignore checkpoint)",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Start trial index (trial_001 = 0) (default: 0)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for trial context variety",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API calls in seconds (default: 1.0)",
    )
    args = parser.parse_args()

    config = Config(
        output_dir=args.out,
        model=args.model,
        max_completion_tokens=args.max_completion_tokens,
        delay_between_calls_sec=args.delay,
        checkpoint_path=f"{args.out}/checkpoint.json",
    )
    resume = args.resume and not args.no_resume

    logger.info(
        "Model: %s | Max completion tokens: %s | Reasoning effort: %s",
        config.model,
        config.max_completion_tokens,
        args.reasoning_effort or "none (default)",
    )

    try:
        result = run(
            output_dir=args.out,
            num_trials=args.trials,
            resume=resume,
            start_index=args.start_index,
            seed=args.seed,
            config=config,
            reasoning_effort=args.reasoning_effort,
        )
        logger.info(
            "Done. Trials: %s, Total words: %s, Total pages: %s",
            result["trials_done"],
            result["total_words"],
            result["total_pages"],
        )
        return 0
    except Exception as e:
        logger.exception("%s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
