"""
Generate synthetic job data so the project can be trained and demoed
without any real client information.

Outputs (written to data/):
  sample_jobs.csv            - job-level cost/revenue history (training input)
  sample_scored_history.csv  - historical jobs with predicted vs. actual
                               values (feeds the app's history views)

Every customer, job number, date, and dollar amount here is randomly
generated. The schema matches the field-service job export the original
pipeline was built against, so train_models.py and the app run unchanged.

Usage (from the repo root):
    python scripts/generate_sample_data.py
"""

import os
import numpy as np
import pandas as pd

SEED = 42
N_JOBS = 1500
N_CUSTOMERS = 220
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# job type -> (median total cost $, cost spread, typical GP%, GP% spread, labor share)
JOB_TYPES = {
    "Investigation/Estimate Only":       (180,   0.5, 0.45, 0.25, 0.95),
    "Secondary Stoppage":                (240,   0.5, 0.60, 0.12, 0.90),
    "Emergency Call":                    (420,   0.7, 0.55, 0.15, 0.80),
    "Fixtures":                          (310,   0.6, 0.58, 0.12, 0.60),
    "Water Repipe/Install":              (2400,  0.8, 0.48, 0.14, 0.50),
    "General Plumbing Service":          (300,   0.6, 0.56, 0.14, 0.75),
    "Backflow Testing":                  (110,   0.3, 0.68, 0.08, 0.95),
    "Hydro Jetting":                     (520,   0.5, 0.62, 0.10, 0.85),
    "Main Line Stoppage":                (380,   0.5, 0.60, 0.12, 0.88),
    "Backflow Repairs/Replacement":      (900,   0.6, 0.52, 0.12, 0.45),
    "Commercial Water Heater":           (3800,  0.6, 0.42, 0.10, 0.30),
    "Leak Detection":                    (450,   0.5, 0.58, 0.12, 0.90),
    "Video Camera Inspection":           (200,   0.4, 0.65, 0.10, 0.95),
    "Toilet":                            (380,   0.5, 0.55, 0.12, 0.55),
    "Tankless Water Heater":             (2900,  0.5, 0.44, 0.10, 0.35),
    "Ejection Pump System":              (3200,  0.7, 0.40, 0.14, 0.40),
}
JOB_WEIGHTS = np.array([16, 13, 11, 9, 6, 5, 5, 5, 4, 3, 3, 3, 2, 2, 1, 1], dtype=float)
PROPERTY_TYPES = ["Commercial", "Multifamily / Light Commercial", "Single-family Residential"]
PROPERTY_WEIGHTS = [0.50, 0.46, 0.04]
PROPERTY_MARGIN_SHIFT = {"Commercial": 0.0, "Multifamily / Light Commercial": -0.02,
                         "Single-family Residential": 0.04}


def make_jobs(rng):
    names = list(JOB_TYPES)
    job_types = rng.choice(names, size=N_JOBS, p=JOB_WEIGHTS / JOB_WEIGHTS.sum())
    props = rng.choice(PROPERTY_TYPES, size=N_JOBS, p=PROPERTY_WEIGHTS)
    customers = [f"Customer {i:03d}" for i in rng.integers(1, N_CUSTOMERS + 1, N_JOBS)]
    start = pd.Timestamp("2025-01-01")
    dates = start + pd.to_timedelta(rng.integers(0, 365, N_JOBS), unit="D")

    rows = []
    for i, (jt, pt) in enumerate(zip(job_types, props)):
        med_cost, spread, gp, gp_sd, labor_share = JOB_TYPES[jt]
        total_cost = round(float(rng.lognormal(np.log(med_cost), spread)), 2)

        labor_share = float(np.clip(rng.normal(labor_share, 0.08), 0.1, 1.0))
        total_labor = total_cost * labor_share
        labor_burden = round(total_labor * 0.28, 2)
        labor_pay = round(total_labor - labor_burden, 2)
        material = round(total_cost - labor_pay - labor_burden, 2)

        margin = float(np.clip(rng.normal(gp + PROPERTY_MARGIN_SHIFT[pt], gp_sd), -0.4, 0.85))
        revenue = round(total_cost / (1 - margin), 2)
        # About 1 in 10 jobs is billed at $0 (warranty / callbacks), as in real exports
        if rng.random() < 0.10:
            revenue, margin = 0.0, np.nan

        has_estimate = rng.random() < 0.6 and revenue > 0
        estimate = round(revenue * float(rng.normal(1.0, 0.12)), 2) if has_estimate else 0.0

        rows.append({
            "Business Unit": "Plumbing",
            "Job #": 500000 + i,
            "Customer Name": customers[i],
            "Job Type": jt,
            "✏️ Property Type": pt,
            "Completion Date": dates[i].date().isoformat(),
            "Jobs Estimate Sales Subtotal": estimate,
            "Jobs Subtotal": revenue,
            "Labor Pay": labor_pay,
            "Labor Burden": labor_burden,
            "Material Costs": material,
            "PO/Bill Costs": 0.0,
            "Jobs Total Costs": total_cost,
            "Jobs Gross Margin": round(revenue - total_cost, 2) if revenue else -total_cost,
            "Jobs Gross Margin %": round(margin, 4) if revenue else np.nan,
        })
    return pd.DataFrame(rows)


def make_scored_history(jobs, rng):
    """Simulate what scoring history with the trained models looks like."""
    h = jobs[jobs["Jobs Subtotal"] > 0].copy()
    actual_rev = h["Jobs Subtotal"]
    actual_gp = h["Jobs Gross Margin %"]
    pred_rev = (actual_rev * rng.normal(1.0, 0.15, len(h))).round(2)
    pred_gp = (actual_gp + rng.normal(0, 0.08, len(h))).clip(-0.4, 0.9).round(4)

    return pd.DataFrame({
        "Job #": h["Job #"],
        "Customer Name": h["Customer Name"],
        "Job Type": h["Job Type"],
        "✏️ Property Type": h["✏️ Property Type"],
        "Completion Date": h["Completion Date"],
        "Predicted Revenue ($)": pred_rev,
        "Actual Revenue ($)": actual_rev,
        "Revenue Error ($)": (pred_rev - actual_rev).round(2),
        "Revenue Error %": ((pred_rev - actual_rev) / actual_rev).round(4),
        "Predicted GP%": pred_gp,
        "Actual GP%": actual_gp,
        "GP% Error (pp)": ((pred_gp - actual_gp) * 100).round(2),
        "Flag: Low Margin": actual_gp < 0.40,
        "Flag: Under-billed": actual_rev < pred_rev * 0.90,
    })


def main():
    rng = np.random.default_rng(SEED)
    os.makedirs(OUT_DIR, exist_ok=True)
    jobs = make_jobs(rng)
    scored = make_scored_history(jobs, rng)
    jobs.to_csv(os.path.join(OUT_DIR, "sample_jobs.csv"), index=False)
    scored.to_csv(os.path.join(OUT_DIR, "sample_scored_history.csv"), index=False)
    print(f"Wrote {len(jobs)} jobs and {len(scored)} scored history rows to data/")


if __name__ == "__main__":
    main()
