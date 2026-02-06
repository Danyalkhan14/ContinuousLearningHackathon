"""Generate per-trial context (indication, drug name, design) for variety."""

import random
from typing import Any, Dict, Optional

# Pools for optional per-trial variety
INDICATIONS = [
    "Type 2 Diabetes Mellitus",
    "Hypertension",
    "Major Depressive Disorder",
    "Rheumatoid Arthritis",
    "Chronic Heart Failure (NYHA II-III)",
    "Atrial Fibrillation",
    "Chronic Low Back Pain",
]

DRUG_NAMES = [
    "Metformin XR",
    "Lisinopril Plus",
    "Sertraline ER",
    "Tocilizumab SC",
    "Sacubitril/Valsartan",
    "Apixaban",
    "Duloxetine",
]

DESIGNS = [
    "randomized, double-blind, placebo-controlled, parallel-group",
    "randomized, double-blind, active-controlled, parallel-group",
    "randomized, double-blind, placebo-controlled, 2:1 allocation",
]


def get_trial_context(
    trial_index: int,
    indication: Optional[str] = None,
    drug_name: Optional[str] = None,
    design: Optional[str] = None,
    n_participants: Optional[int] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build trial context dict for prompts. If optional params are None,
    pick from pools using trial_index (and optional seed) for variety.
    """
    if seed is not None:
        rng = random.Random(seed + trial_index)
    else:
        rng = random.Random(trial_index)
    context = {
        "indication": indication or rng.choice(INDICATIONS),
        "drug_name": drug_name or rng.choice(DRUG_NAMES),
        "design": design or rng.choice(DESIGNS),
        "n_participants": n_participants or rng.randint(300, 500),
        "brief_title": None,
    }
    context["brief_title"] = (
        f"A Phase 3, {context['design']} study of {context['drug_name']} "
        f"in patients with {context['indication']}"
    )
    return context
