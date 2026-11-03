"""
Train and serialize Model A (revenue consistency) and Model B (bid-time margin prediction).
Mirrors the pipeline developed in the exploratory modeling notebooks.
Run once from the repo root: python train_models.py
"""

import os
import numpy as np
import pandas as pd
import joblib
import warnings

warnings.filterwarnings("ignore")

from xgboost import XGBRegressor
from sklearn.preprocessing import LabelEncoder

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_jobs.csv")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


def load_and_clean():
    df = pd.read_csv(DATA_PATH)

    df = df[
        df["Business Unit"].notna() & (df["Business Unit"] != "Business Unit: Plumbing")
    ].copy()

    df_jobs = df[df["Business Unit"] == "Plumbing"].copy()
    print(f"Raw rows: {len(df_jobs)}")

    numeric_cols = [
        "Jobs Estimate Sales Subtotal",
        "Jobs Subtotal",
        "Labor Pay",
        "Labor Burden",
        "Material Costs",
        "PO/Bill Costs",
        "Jobs Total Costs",
        "Jobs Gross Margin",
        "Jobs Gross Margin %",
    ]
    for col in numeric_cols:
        df_jobs[col] = pd.to_numeric(df_jobs[col], errors="coerce")

    df_jobs["total_labor"] = df_jobs["Labor Pay"] + df_jobs["Labor Burden"]

    df_jobs = df_jobs[
        (df_jobs["Jobs Subtotal"] > 0)
        & (df_jobs["Jobs Gross Margin %"].notna())
        & (df_jobs["Jobs Gross Margin %"].between(-1.0, 1.1))
        & (df_jobs["Jobs Total Costs"] > 0)
    ].copy()

    print(f"Clean rows: {len(df_jobs)}")
    return df_jobs


def engineer_features(df_jobs):
    df_jobs["labor_cost_share"] = df_jobs["total_labor"] / df_jobs["Jobs Total Costs"].replace(0, np.nan)
    df_jobs["material_cost_share"] = df_jobs["Material Costs"] / df_jobs["Jobs Total Costs"].replace(0, np.nan)
    df_jobs["po_cost_share"] = df_jobs["PO/Bill Costs"] / df_jobs["Jobs Total Costs"].replace(0, np.nan)
    df_jobs["labor_to_material"] = df_jobs["total_labor"] / df_jobs["Material Costs"].replace(0, np.nan)
    df_jobs["log_revenue"] = np.log1p(df_jobs["Jobs Subtotal"])
    df_jobs["log_total_cost"] = np.log1p(df_jobs["Jobs Total Costs"])
    df_jobs["log_estimate"] = np.log1p(df_jobs["Jobs Estimate Sales Subtotal"])

    label_encoders = {}
    for col in ["Job Type", "✏️ Property Type"]:
        df_jobs[col] = df_jobs[col].fillna("Unknown")
        le = LabelEncoder()
        enc = col.replace("✏️ ", "") + "_enc"
        df_jobs[enc] = le.fit_transform(df_jobs[col].astype(str))
        label_encoders[col] = le

    df_jobs["Completion Date"] = pd.to_datetime(df_jobs["Completion Date"], errors="coerce")
    df_jobs["job_month"] = df_jobs["Completion Date"].dt.month.fillna(0).astype(int)
    df_jobs["job_quarter"] = df_jobs["Completion Date"].dt.quarter.fillna(0).astype(int)

    return df_jobs, label_encoders


def train_model_a(df_jobs):
    """Revenue consistency model — predicts actual billed revenue from cost components."""
    FEATURES_A = [
        "total_labor", "Material Costs", "PO/Bill Costs", "Jobs Total Costs",
        "labor_cost_share", "material_cost_share", "po_cost_share",
        "labor_to_material", "log_total_cost",
        "Job Type_enc", "Property Type_enc",
        "job_month", "job_quarter",
    ]
    FEATURES_A = [f for f in FEATURES_A if f in df_jobs.columns]
    TARGET_A = "Jobs Subtotal"

    model_df = (
        df_jobs[FEATURES_A + [TARGET_A]]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    model_df = model_df[model_df[TARGET_A] > 0]

    X, y = model_df[FEATURES_A], model_df[TARGET_A]

    best_params = dict(
        subsample=0.9, reg_lambda=3.0, reg_alpha=0.1, n_estimators=300,
        min_child_weight=3, max_depth=4, learning_rate=0.04, colsample_bytree=0.9,
    )
    model = XGBRegressor(**best_params, random_state=42, n_jobs=-1)
    model.fit(X, y)
    print(f"Model A trained on {len(X)} rows. Features: {FEATURES_A}")
    return model, FEATURES_A


def train_model_b(df_jobs):
    """Bid-time margin model — predicts GP% from pre-job features only."""
    FEATURES_B = [
        "Jobs Estimate Sales Subtotal", "log_estimate",
        "Job Type_enc", "Property Type_enc",
        "job_month", "job_quarter",
    ]
    FEATURES_B = [f for f in FEATURES_B if f in df_jobs.columns]
    TARGET_B = "Jobs Gross Margin %"

    model_df = (
        df_jobs[FEATURES_B + [TARGET_B]]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )

    X, y = model_df[FEATURES_B], model_df[TARGET_B]

    best_params = dict(
        subsample=0.9, reg_lambda=1.0, reg_alpha=1.0, n_estimators=200,
        min_child_weight=10, max_depth=3, learning_rate=0.06, colsample_bytree=0.9,
    )
    model = XGBRegressor(**best_params, random_state=42, n_jobs=-1)
    model.fit(X, y)
    print(f"Model B trained on {len(X)} rows. Features: {FEATURES_B}")
    return model, FEATURES_B


def build_job_type_stats(df_jobs):
    """Return per-job-type sample counts for model confidence display in the app."""
    counts = df_jobs["Job Type"].value_counts().to_dict()
    return counts


def build_margin_thresholds(df_jobs):
    """
    Compute per-job-type margin floors from historical actuals.

    Red floor  = 25th percentile GP% for that job type
    Yellow floor = median GP% for that job type

    Job types with fewer than 10 jobs fall back to the global defaults
    (0.40 Red, 0.50 Yellow) so thin data doesn't produce unstable thresholds.
    """
    GLOBAL_RED    = 0.40
    GLOBAL_YELLOW = 0.50
    MIN_FLOOR_RED = 0.15   # no job type gets a Red floor below 15%
    MIN_JOBS      = 10

    thresholds = {}
    for jt, group in df_jobs.groupby("Job Type")["Jobs Gross Margin %"]:
        clean = group.dropna()
        if len(clean) >= MIN_JOBS:
            raw_red = float(clean.quantile(0.25))
            thresholds[jt] = {
                "red":    round(max(raw_red, MIN_FLOOR_RED), 4),
                "yellow": round(float(clean.quantile(0.50)), 4),
                "std":    round(float(clean.std()), 4),
                "n":      len(clean),
            }
        else:
            thresholds[jt] = {
                "red":    GLOBAL_RED,
                "yellow": GLOBAL_YELLOW,
                "n":      len(clean),
                "fallback": True,
            }

    thresholds["__global__"] = {"red": GLOBAL_RED, "yellow": GLOBAL_YELLOW}

    # Print summary for visibility
    print("\nPer-job-type margin thresholds (Red / Yellow):")
    for jt, v in sorted(thresholds.items()):
        if jt == "__global__":
            continue
        flag = " ← fallback" if v.get("fallback") else ""
        print(f"  {jt:<55} {v['red']:.1%} / {v['yellow']:.1%}  (n={v['n']}){flag}")

    return thresholds


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)

    df_jobs = load_and_clean()
    df_jobs, label_encoders = engineer_features(df_jobs)

    job_type_le = label_encoders["Job Type"]
    prop_type_le = label_encoders["✏️ Property Type"]

    job_type_stats      = build_job_type_stats(df_jobs)
    margin_thresholds   = build_margin_thresholds(df_jobs)

    model_a, features_a = train_model_a(df_jobs)
    model_b, features_b = train_model_b(df_jobs)

    joblib.dump(model_a, os.path.join(MODELS_DIR, "model_a.pkl"))
    joblib.dump(model_b, os.path.join(MODELS_DIR, "model_b.pkl"))
    joblib.dump(
        {
            "Job Type": job_type_le,
            "Property Type": prop_type_le,
            "job_types": sorted(job_type_le.classes_.tolist()),
            "property_types": sorted(prop_type_le.classes_.tolist()),
            "job_type_counts": job_type_stats,
            "margin_thresholds": margin_thresholds,
            "features_a": features_a,
            "features_b": features_b,
        },
        os.path.join(MODELS_DIR, "encoders.pkl"),
    )

    print(f"\nSaved to {MODELS_DIR}/")
    print("  model_a.pkl  — revenue consistency model")
    print("  model_b.pkl  — bid-time margin model")
    print("  encoders.pkl — label encoders + feature lists")


if __name__ == "__main__":
    main()
