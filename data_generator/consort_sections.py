"""CONSORT 2025 section list and item descriptions for prompts."""

from dataclasses import dataclass
from typing import List


@dataclass
class SectionSpec:
    """A section to generate with heading and target description."""

    heading: str
    level: int  # 1 = top level
    short_description: str
    target_words: int = 800
    consort_item_ids: List[str] = None

    def __post_init__(self):
        if self.consort_item_ids is None:
            self.consort_item_ids = []


# Protocol sections (60-80 pp total; ~18-24k words)
PROTOCOL_SECTIONS: List[SectionSpec] = [
    SectionSpec(
        "1. Introduction",
        1,
        "Scientific background and rationale for the trial.",
        target_words=2000,
        consort_item_ids=["6"],
    ),
    SectionSpec(
        "2. Objectives",
        1,
        "Primary and secondary objectives (benefits and harms).",
        target_words=1500,
        consort_item_ids=["7"],
    ),
    SectionSpec(
        "3. Methods",
        1,
        "Overview of methodology.",
        target_words=500,
        consort_item_ids=["9"],
    ),
    SectionSpec(
        "3.1 Study Design",
        2,
        "Trial design type, allocation ratio, framework (e.g. parallel, double-blind).",
        target_words=2000,
        consort_item_ids=["9"],
    ),
    SectionSpec(
        "3.2 Settings and Locations",
        2,
        "Where the trial is conducted (multicentre, countries/sites).",
        target_words=1000,
        consort_item_ids=["11"],
    ),
    SectionSpec(
        "3.3 Eligibility Criteria",
        2,
        "Inclusion and exclusion criteria for participants (and sites if applicable).",
        target_words=2500,
        consort_item_ids=["12a", "12b"],
    ),
    SectionSpec(
        "3.4 Interventions",
        2,
        "Intervention and comparator with dose, route, schedule, duration.",
        target_words=2000,
        consort_item_ids=["13"],
    ),
    SectionSpec(
        "3.5 Outcomes",
        2,
        "Primary and secondary outcomes with measurement details and timepoints.",
        target_words=2000,
        consort_item_ids=["14"],
    ),
    SectionSpec(
        "3.6 Harms",
        2,
        "How harms are defined and assessed.",
        target_words=1000,
        consort_item_ids=["15"],
    ),
    SectionSpec(
        "3.7 Sample Size",
        2,
        "Sample size calculation with assumptions (power, alpha, effect size, dropout).",
        target_words=1500,
        consort_item_ids=["16a"],
    ),
    SectionSpec(
        "3.8 Randomization",
        2,
        "Who generated the sequence, method, type, restriction/stratification.",
        target_words=1500,
        consort_item_ids=["17a", "17b"],
    ),
    SectionSpec(
        "3.9 Allocation Concealment",
        2,
        "Mechanism for allocation concealment.",
        target_words=800,
        consort_item_ids=["18"],
    ),
    SectionSpec(
        "3.10 Blinding",
        2,
        "Who was blinded; how blinding was achieved; similarity of interventions.",
        target_words=1500,
        consort_item_ids=["20a", "20b"],
    ),
    SectionSpec(
        "3.11 Statistical Analysis Plan Outline",
        2,
        "Summary of statistical methods, analysis populations, missing data (full SAP separate).",
        target_words=2000,
        consort_item_ids=["21a", "21b", "21c"],
    ),
]

# SAP sections (20-30 pp total; ~6-9k words)
SAP_SECTIONS: List[SectionSpec] = [
    SectionSpec(
        "1. Introduction and Scope",
        1,
        "Scope of the SAP and relationship to protocol.",
        target_words=500,
    ),
    SectionSpec(
        "2. Analysis Populations",
        1,
        "Definition of ITT, mITT, per-protocol, safety populations.",
        target_words=1500,
        consort_item_ids=["21b"],
    ),
    SectionSpec(
        "3. Statistical Methods for Primary and Secondary Outcomes",
        1,
        "Methods for comparing groups (e.g. ANCOVA, mixed models), model details.",
        target_words=2500,
        consort_item_ids=["21a"],
    ),
    SectionSpec(
        "4. Handling of Missing Data",
        1,
        "LOCF, MMRM, multiple imputation, or other; justification.",
        target_words=1500,
        consort_item_ids=["21c"],
    ),
    SectionSpec(
        "5. Subgroup and Other Pre-specified Analyses",
        1,
        "Subgroup analyses, multiplicity adjustment.",
        target_words=1000,
        consort_item_ids=["21d"],
    ),
    SectionSpec(
        "6. Table Shells",
        1,
        "List and descriptions of planned tables (demographics, efficacy, safety).",
        target_words=2000,
    ),
]

# Summary Tables / Listings sections (30-40 pp; ~9-12k words)
SUMMARY_TABLE_SECTIONS: List[SectionSpec] = [
    SectionSpec(
        "Demographics and Baseline Characteristics",
        1,
        "Table of baseline demographics and clinical characteristics by treatment arm.",
        target_words=900,  # ~2-3 pp
    ),
    SectionSpec(
        "Disposition and Enrollment Flow",
        1,
        "CONSORT flow: assessed, excluded, randomized, allocated, analyzed.",
        target_words=900,  # ~2-3 pp
    ),
    SectionSpec(
        "Efficacy Summary Tables",
        1,
        "Primary and secondary efficacy results (change from baseline, responder rates, etc.).",
        target_words=4500,  # ~10-15 pp
    ),
    SectionSpec(
        "Adverse Events Summary",
        1,
        "Summary of AEs by SOC, severity, relationship; SAEs.",
        target_words=4500,  # ~10-15 pp
    ),
    SectionSpec(
        "Laboratory Data Summary",
        1,
        "Lab values over time; clinically significant abnormalities.",
        target_words=2250,  # ~5-10 pp
    ),
]
