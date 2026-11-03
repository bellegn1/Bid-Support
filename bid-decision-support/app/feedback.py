"""
Append one row per estimator decision to data/feedback_log.csv.
This is the raw material for the model feedback loop described in the deck.
"""

import os
from datetime import datetime

import pandas as pd

FEEDBACK_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "feedback_log.csv")

COLUMNS = [
    "timestamp",
    "job_type",
    "property_type",
    "quote",
    "total_cost",
    "benchmark_price",
    "range_low",
    "range_high",
    "deviation_pct",
    "expected_margin_pct",
    "flag_status",
    "reason_code",
    "notes",
    "manager_approved",
    "servicetitan_job_id",
]


def log_decision(
    job_type: str,
    property_type: str,
    quote: float,
    total_cost: float,
    benchmark_price: float,
    range_low: float,
    range_high: float,
    deviation_pct: float,
    expected_margin: float,
    flag_status: str,
    reason_code: str = "",
    notes: str = "",
    manager_approved: bool = False,
    servicetitan_job_id: str = "",
) -> None:
    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)

    row = pd.DataFrame(
        [
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "job_type": job_type,
                "property_type": property_type,
                "quote": round(quote, 2),
                "total_cost": round(total_cost, 2),
                "benchmark_price": round(benchmark_price, 2),
                "range_low": round(range_low, 2),
                "range_high": round(range_high, 2),
                "deviation_pct": round(deviation_pct * 100, 2),
                "expected_margin_pct": round(expected_margin * 100, 2),
                "flag_status": flag_status,
                "reason_code": reason_code,
                "notes": notes,
                "manager_approved": manager_approved,
                "servicetitan_job_id": servicetitan_job_id,
            }
        ]
    )

    file_exists = os.path.isfile(FEEDBACK_PATH)
    row.to_csv(FEEDBACK_PATH, mode="a", header=not file_exists, index=False)


def load_log() -> pd.DataFrame | None:
    if not os.path.isfile(FEEDBACK_PATH):
        return None
    return pd.read_csv(FEEDBACK_PATH)
