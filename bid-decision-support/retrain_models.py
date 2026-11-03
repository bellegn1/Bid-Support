"""
Retrain Model A and Model B incorporating feedback loop data.

Run this once enough decisions have been logged to data/feedback_log.csv
(recommended: at least 50 new logged bids before retraining).

Usage:
    python retrain_models.py

What it does:
  1. Loads the original training data from the Excel source
  2. Loads feedback_log.csv (submitted bids with actual outcomes)
  3. Merges them and retrains both models on the combined dataset
  4. Overwrites models/ with the updated .pkl files
  5. Prints a comparison of old vs new CV MAE

Feedback rows that are eligible to augment training:
  - Must have a quote (used as Jobs Estimate Sales Subtotal)
  - Must have total_cost > 0
  - Must have expected_margin_pct (used as proxy for Jobs Gross Margin %)
  - Flag status logged (used to weight or filter outliers)

Note: feedback data improves Model B (bid-time margin) most directly.
Model A (revenue consistency) requires actual post-job cost data and
benefits less from bid-stage feedback alone.
"""

import os
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, cross_val_score
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")

BASE_DIR      = os.path.dirname(__file__)
DATA_PATH     = os.path.join(BASE_DIR, "data", "sample_jobs.csv")
FEEDBACK_PATH = os.path.join(BASE_DIR, "data", "feedback_log.csv")
MODELS_DIR    = os.path.join(BASE_DIR, "models")
MIN_FEEDBACK_ROWS = 10  # warn if fewer than this


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_original(encoders):
    """Load and clean the original training set, reusing existing encoders."""
    df = pd.read_csv(DATA_PATH)
    df = df[df["Business Unit"].notna() & (df["Business Unit"] != "Business Unit: Plumbing")].copy()
    df = df[df["Business Unit"] == "Plumbing"].copy()

    numeric_cols = [
        "Jobs Estimate Sales Subtotal", "Jobs Subtotal",
        "Labor Pay", "Labor Burden", "Material Costs", "PO/Bill Costs",
        "Jobs Total Costs", "Jobs Gross Margin %",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["total_labor"] = df["Labor Pay"] + df["Labor Burden"]

    df = df[
        (df["Jobs Subtotal"] > 0)
        & (df["Jobs Gross Margin %"].notna())
        & (df["Jobs Gross Margin %"].between(-1.0, 1.1))
        & (df["Jobs Total Costs"] > 0)
    ].copy()

    df["✏️ Property Type"] = df["✏️ Property Type"].fillna("Unknown")
    df["Job Type"]         = df["Job Type"].fillna("Unknown")

    # Use existing encoders (don't refit — keeps encoding stable)
    df["Job Type_enc"]      = encoders["Job Type"].transform(
        df["Job Type"].map(lambda x: x if x in encoders["Job Type"].classes_ else "Unknown")
    )
    df["Property Type_enc"] = encoders["Property Type"].transform(
        df["✏️ Property Type"].map(lambda x: x if x in encoders["Property Type"].classes_ else "Unknown")
    )

    df["Completion Date"] = pd.to_datetime(df["Completion Date"], errors="coerce")
    df["job_month"]   = df["Completion Date"].dt.month.fillna(0).astype(int)
    df["job_quarter"] = df["Completion Date"].dt.quarter.fillna(0).astype(int)

    for col in ["labor_cost_share", "material_cost_share", "po_cost_share", "labor_to_material",
                "log_revenue", "log_total_cost", "log_estimate"]:
        pass  # computed below

    df["labor_cost_share"]    = df["total_labor"]      / df["Jobs Total Costs"].replace(0, np.nan)
    df["material_cost_share"] = df["Material Costs"]   / df["Jobs Total Costs"].replace(0, np.nan)
    df["po_cost_share"]       = df["PO/Bill Costs"]    / df["Jobs Total Costs"].replace(0, np.nan)
    df["labor_to_material"]   = df["total_labor"]      / df["Material Costs"].replace(0, np.nan)
    df["log_total_cost"]      = np.log1p(df["Jobs Total Costs"])
    df["log_estimate"]        = np.log1p(df["Jobs Estimate Sales Subtotal"])

    df = df.rename(columns={
        "Jobs Subtotal":               "Jobs Subtotal",
        "Jobs Gross Margin %":         "Jobs Gross Margin %",
        "Jobs Estimate Sales Subtotal": "Jobs Estimate Sales Subtotal",
        "Material Costs":              "Material Costs",
        "PO/Bill Costs":               "PO/Bill Costs",
        "Jobs Total Costs":            "Jobs Total Costs",
    })
    return df


def load_feedback(encoders):
    """Convert feedback log rows into model-compatible format for Model B augmentation."""
    if not os.path.isfile(FEEDBACK_PATH):
        return pd.DataFrame()

    fb = pd.read_csv(FEEDBACK_PATH)
    fb = fb.dropna(subset=["quote", "total_cost", "expected_margin_pct"])
    fb = fb[(fb["quote"] > 0) & (fb["total_cost"] > 0)].copy()

    if len(fb) == 0:
        return pd.DataFrame()

    fb["Jobs Estimate Sales Subtotal"] = fb["quote"]
    fb["Jobs Gross Margin %"]          = fb["expected_margin_pct"] / 100.0
    fb["log_estimate"]                 = np.log1p(fb["quote"])
    fb["timestamp"]                    = pd.to_datetime(fb["timestamp"])
    fb["job_month"]                    = fb["timestamp"].dt.month.fillna(0).astype(int)
    fb["job_quarter"]                  = fb["timestamp"].dt.quarter.fillna(0).astype(int)

    fb["job_type"]     = fb["job_type"].fillna("Unknown")
    fb["property_type"] = fb["property_type"].fillna("Unknown")

    fb["Job Type_enc"] = encoders["Job Type"].transform(
        fb["job_type"].map(lambda x: x if x in encoders["Job Type"].classes_ else "Unknown")
    )
    fb["Property Type_enc"] = encoders["Property Type"].transform(
        fb["property_type"].map(lambda x: x if x in encoders["Property Type"].classes_ else "Unknown")
    )

    return fb


def cv_mae(model_cls, params, X, y, n_splits=5):
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    scores = -cross_val_score(model_cls(**params, random_state=42, n_jobs=-1),
                              X, y, cv=kf, scoring="neg_mean_absolute_error")
    return scores.mean(), scores.std()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading existing models and encoders...")
    encoders  = joblib.load(os.path.join(MODELS_DIR, "encoders.pkl"))
    old_model_b = joblib.load(os.path.join(MODELS_DIR, "model_b.pkl"))
    params_b = {k: v for k, v in old_model_b.get_params().items()
                if k in ["n_estimators","learning_rate","max_depth","subsample",
                         "colsample_bytree","min_child_weight","reg_alpha","reg_lambda"]}

    print("Loading original training data...")
    orig = load_original(encoders)
    print(f"  Original rows: {len(orig)}")

    print("Loading feedback log...")
    fb = load_feedback(encoders)
    if len(fb) < MIN_FEEDBACK_ROWS:
        print(f"  ⚠️  Only {len(fb)} feedback rows — recommend at least {MIN_FEEDBACK_ROWS} before retraining.")
        print("  Proceeding anyway for demonstration purposes.")
    else:
        print(f"  Feedback rows: {len(fb)}")

    # ── Model B retrain ───────────────────────────────────────────────────────
    FEATURES_B = encoders["features_b"]
    TARGET_B   = "Jobs Gross Margin %"

    orig_b = orig[FEATURES_B + [TARGET_B]].replace([np.inf, -np.inf], np.nan).dropna()

    if len(fb) > 0:
        fb_b = fb[FEATURES_B + [TARGET_B]].replace([np.inf, -np.inf], np.nan).dropna()
        combined_b = pd.concat([orig_b, fb_b], ignore_index=True)
        print(f"  Model B training rows: {len(orig_b)} original + {len(fb_b)} feedback = {len(combined_b)}")
    else:
        combined_b = orig_b
        print(f"  Model B training rows: {len(combined_b)} (no feedback added)")

    X_b, y_b = combined_b[FEATURES_B], combined_b[TARGET_B]

    old_mae, _ = cv_mae(XGBRegressor, params_b, orig_b[FEATURES_B], orig_b[TARGET_B])
    new_mae, new_std = cv_mae(XGBRegressor, params_b, X_b, y_b)

    print(f"\n  Model B CV MAE — before: {old_mae*100:.2f}pp | after: {new_mae*100:.2f}pp ± {new_std*100:.2f}pp")

    new_model_b = XGBRegressor(**params_b, random_state=42, n_jobs=-1)
    new_model_b.fit(X_b, y_b)

    # ── Model A retrain (original data only — needs post-job actuals) ─────────
    FEATURES_A = encoders["features_a"]
    TARGET_A   = "Jobs Subtotal"
    old_model_a = joblib.load(os.path.join(MODELS_DIR, "model_a.pkl"))
    params_a = {k: v for k, v in old_model_a.get_params().items()
                if k in ["n_estimators","learning_rate","max_depth","subsample",
                         "colsample_bytree","min_child_weight","reg_alpha","reg_lambda"]}

    orig_a = orig[FEATURES_A + [TARGET_A]].replace([np.inf, -np.inf], np.nan).dropna()
    orig_a = orig_a[orig_a[TARGET_A] > 0]
    new_model_a = XGBRegressor(**params_a, random_state=42, n_jobs=-1)
    new_model_a.fit(orig_a[FEATURES_A], orig_a[TARGET_A])
    print(f"  Model A retrained on {len(orig_a)} original rows (post-job actuals required; feedback not used).")

    # ── Save ──────────────────────────────────────────────────────────────────
    joblib.dump(new_model_a, os.path.join(MODELS_DIR, "model_a.pkl"))
    joblib.dump(new_model_b, os.path.join(MODELS_DIR, "model_b.pkl"))
    print(f"\nModels saved to {MODELS_DIR}/")
    print("Restart the Streamlit app to load the updated models.")


if __name__ == "__main__":
    main()
