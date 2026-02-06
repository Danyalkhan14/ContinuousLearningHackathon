"""Optional: generate CT.gov-shaped JSON from trial context for CliniRepGen ingest."""

import json
from pathlib import Path
from typing import Any, Dict

from data_generator.trial_context import get_trial_context


def build_ctgov_from_context(
    trial_context: Dict[str, Any],
    trial_id: str = "trial_001",
    nct_id: str = "NCT00000001",
) -> Dict[str, Any]:
    """Build a minimal CT.gov-shaped dict from trial context (for CliniRepGen manifest builder)."""
    indication = trial_context.get("indication", "Condition X")
    drug = trial_context.get("drug_name", "Drug X")
    n = trial_context.get("n_participants", 400)
    return {
        "study": {
            "nct_id": nct_id,
            "brief_title": trial_context.get("brief_title", f"Phase 3 study of {drug} in {indication}"),
            "official_title": f"A Phase 3, {trial_context.get('design', 'randomized, double-blind')} study of {drug} in patients with {indication}",
            "phase": "Phase 3",
            "study_type": "Interventional",
            "enrollment": n,
            "start_date": "2024-01-15",
            "completion_date": "2025-06-30",
            "overall_status": "Completed",
            "conditions": [indication],
        },
        "interventions": [
            {"intervention_type": "Drug", "name": drug, "description": f"Active treatment; see protocol for dose and schedule"},
            {"intervention_type": "Drug", "name": "Placebo", "description": "Matching placebo"},
        ],
        "outcomes": [
            {"outcome_type": "Primary", "title": "Primary efficacy endpoint", "description": "See protocol", "time_frame": "Week 24"},
            {"outcome_type": "Secondary", "title": "Key secondary endpoint", "description": "See protocol", "time_frame": "Week 24"},
        ],
        "adverse_events": [
            {"event_type": "Other", "organ_system": "General", "adverse_event_term": "Headache", "subjects_affected": 0, "subjects_at_risk": n},
        ],
    }


def write_ctgov(
    output_path: Path,
    trial_context: Dict[str, Any],
    trial_id: str = "trial_001",
    nct_id: str = "NCT00000001",
) -> None:
    """Write ctgov.json to output_path (e.g. trial_dir/ctgov.json)."""
    data = build_ctgov_from_context(trial_context, trial_id=trial_id, nct_id=nct_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
