"""
Bid Deviation & Estimator Decision-Support Tool
Standalone Streamlit app — ServiceTitan integration stubbed and disabled.
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
import streamlit as st

# Make app/ importable regardless of working directory
sys.path.insert(0, os.path.dirname(__file__))

from flag_logic import flag_summary, BENCHMARK_TOLERANCE, MARGIN_FLOOR, MARGIN_YELLOW_FLOOR, get_margin_floors
from servicetitan import SERVICETITAN_ENABLED
import feedback as fb

# ── Constants ─────────────────────────────────────────────────────────────────
MODELS_DIR   = os.path.join(os.path.dirname(__file__), "..", "models")
SCORED_CSV   = os.path.join(os.path.dirname(__file__), "..", "data", "sample_scored_history.csv")

REASON_CODES = [
    "— select —",
    "Competitive pressure",
    "Strategic customer",
    "Site complexity",
    "Low-complexity job",
    "Emergency premium",
    "No strong competition",
    "Material price change",
    "Branch manager guidance",
    "Other",
]

MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bid Decision Support",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Model loading (cached) ─────────────────────────────────────────────────────
@st.cache_resource
def load_models():
    try:
        model_a   = joblib.load(os.path.join(MODELS_DIR, "model_a.pkl"))
        model_b   = joblib.load(os.path.join(MODELS_DIR, "model_b.pkl"))
        encoders  = joblib.load(os.path.join(MODELS_DIR, "encoders.pkl"))
        return model_a, model_b, encoders
    except FileNotFoundError:
        return None, None, None


@st.cache_data
def load_job_cost_stats() -> pd.DataFrame:
    """Historical avg labor, material, PO costs by job type from source data."""
    try:
        df = pd.read_csv(
            os.path.join(os.path.dirname(__file__), "..", "data", "sample_jobs.csv"),
        )
        df = df[df["Business Unit"].notna() & (df["Business Unit"] != "Business Unit: Plumbing")]
        df = df[df["Business Unit"] == "Plumbing"].copy()
        for col in ["Labor Pay", "Labor Burden", "Material Costs", "PO/Bill Costs", "Jobs Total Costs"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["total_labor"] = df["Labor Pay"] + df["Labor Burden"]
        df = df[(df["Jobs Total Costs"] > 0)].copy()
        stats = df.groupby("Job Type")[["total_labor", "Material Costs", "PO/Bill Costs"]].median()
        return stats
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_scored_history() -> pd.DataFrame | None:
    try:
        df = pd.read_csv(SCORED_CSV)
        df.columns = [c.replace("✏️ ", "") for c in df.columns]
        df["Completion Date"] = pd.to_datetime(df["Completion Date"], errors="coerce")
        return df
    except FileNotFoundError:
        return None


def model_confidence_label(job_type: str, counts: dict) -> tuple[str, int]:
    """Map job-type sample count to a confidence label and progress value (0–100)."""
    n = counts.get(job_type, 0)
    if n >= 60:
        return "High", 90
    if n >= 25:
        return "Medium", 55
    return "Low", 25


def predict_margin(model_b, encoders, job_type, prop_type, quote, month):
    """Run Model B inference. Returns predicted GP% as a float (e.g. 0.61)."""
    quarter = (month - 1) // 3 + 1
    try:
        jt_enc = encoders["Job Type"].transform([job_type])[0]
    except ValueError:
        jt_enc = 0
    try:
        pt_enc = encoders["Property Type"].transform([prop_type])[0]
    except ValueError:
        pt_enc = 0

    row = {
        "Jobs Estimate Sales Subtotal": quote,
        "log_estimate": np.log1p(quote),
        "Job Type_enc": jt_enc,
        "Property Type_enc": pt_enc,
        "job_month": month,
        "job_quarter": quarter,
    }
    features_b = encoders["features_b"]
    X = pd.DataFrame([row])[features_b]
    return float(model_b.predict(X)[0])


def predict_revenue(model_a, encoders, job_type, prop_type,
                    labor, material, po, month):
    """Run Model A inference. Returns predicted revenue as a float."""
    quarter = (month - 1) // 3 + 1
    total_cost = labor + material + po
    try:
        jt_enc = encoders["Job Type"].transform([job_type])[0]
    except ValueError:
        jt_enc = 0
    try:
        pt_enc = encoders["Property Type"].transform([prop_type])[0]
    except ValueError:
        pt_enc = 0

    labor_cost_share    = labor    / total_cost if total_cost > 0 else 0
    material_cost_share = material / total_cost if total_cost > 0 else 0
    po_cost_share       = po       / total_cost if total_cost > 0 else 0
    labor_to_material   = labor    / material   if material  > 0 else 0

    row = {
        "total_labor":          labor,
        "Material Costs":       material,
        "PO/Bill Costs":        po,
        "Jobs Total Costs":     total_cost,
        "labor_cost_share":     labor_cost_share,
        "material_cost_share":  material_cost_share,
        "po_cost_share":        po_cost_share,
        "labor_to_material":    labor_to_material,
        "log_total_cost":       np.log1p(total_cost),
        "Job Type_enc":         jt_enc,
        "Property Type_enc":    pt_enc,
        "job_month":            month,
        "job_quarter":          quarter,
    }
    features_a = encoders["features_a"]
    X = pd.DataFrame([row])[features_a]
    return float(model_a.predict(X)[0])


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🔧 Pricing Intelligence")
        st.markdown("**Commercial Plumbing Contractor (demo)**")
        st.divider()

        if SERVICETITAN_ENABLED:
            st.success("ServiceTitan: Connected")
        else:
            st.markdown(
                "<span style='background:#e0e0e0;padding:4px 10px;border-radius:4px;"
                "font-size:0.85em;color:#555'>⚫ ServiceTitan: Not Connected</span>",
                unsafe_allow_html=True,
            )
            st.caption("ServiceTitan integration is pending API credentials.")

        st.divider()
        st.markdown("**Mode**")
        field_mode = st.toggle(
            "Field (quick)",
            value=False,
            help="Field mode: minimal inputs, instant flag. Estimating mode: full cost breakdown.",
        )
        if field_mode:
            st.caption("⚡ Field mode — fewer inputs, faster decision.")
        else:
            st.caption("📋 Estimating mode — full cost breakdown and historical reference.")

        st.divider()
        st.markdown(
            f"**Thresholds (configurable in `flag_logic.py`)**\n"
            f"- Benchmark range: ±{int(BENCHMARK_TOLERANCE*100)}%\n"
            f"- Margin floor (Red): {int(MARGIN_FLOOR*100)}%\n"
            f"- Margin floor (Yellow): {int(MARGIN_YELLOW_FLOOR*100)}%"
        )
        st.divider()
        st.caption("Chicago Booth Lab — Team 4 | Pilot")
        return field_mode


# ── Main UI ───────────────────────────────────────────────────────────────────
def render_checker_tab(model_a, model_b, encoders, field_mode: bool = False):
    st.subheader("Bid Check")

    job_types      = encoders["job_types"]
    property_types = encoders["property_types"]
    jt_counts      = encoders["job_type_counts"]

    col1, col2, col3 = st.columns([1.1, 1.0, 1.1], gap="large")

    # ── Column 1: Job Inputs ──────────────────────────────────────────────────
    cost_stats = load_job_cost_stats()

    with col1:
        st.markdown("#### Job Inputs")

        job_type  = st.selectbox("Job Type", job_types)
        prop_type = st.selectbox("Property Type", property_types)
        month     = st.selectbox(
            "Completion Month",
            options=list(MONTH_NAMES.keys()),
            format_func=lambda m: MONTH_NAMES[m],
            index=4,
        )

        hist_labor    = cost_stats.loc[job_type, "total_labor"]    if job_type in cost_stats.index else None
        hist_material = cost_stats.loc[job_type, "Material Costs"] if job_type in cost_stats.index else None
        hist_po       = cost_stats.loc[job_type, "PO/Bill Costs"]  if job_type in cost_stats.index else None

        if field_mode:
            # ── Field mode: minimal inputs ─────────────────────────────────
            st.caption("⚡ Quick entry — model uses job type and quote to estimate benchmark.")
            fc1, fc2 = st.columns(2)
            field_workers = fc1.number_input("Workers", min_value=0, value=1, step=1, key="f_workers")
            field_hours   = fc2.number_input("Hours", min_value=0.0, value=0.0, step=0.5, format="%.1f", key="f_hours")
            field_rate    = 85.0
            labor    = field_workers * field_hours * field_rate
            material = float(hist_material) if hist_material is not None else 0.0
            po       = float(hist_po)       if hist_po is not None else 0.0
            total_cost = labor + material + po
            if hist_labor or hist_material:
                st.caption(
                    f"Materials and PO pre-filled from historical medians "
                    f"(${material:,.0f} + ${po:,.0f}). Switch to Estimating mode to adjust."
                )
            st.metric("Est. Total Cost", f"${total_cost:,.0f}")

        else:
            # ── Estimating mode: full breakdown ────────────────────────────
            with st.expander("🔨 Labor", expanded=True):
                if hist_labor is not None:
                    st.caption(f"Historical median for {job_type}: **${hist_labor:,.0f}**")
                lc1, lc2 = st.columns(2)
                workers = lc1.number_input("Workers", min_value=0, value=1, step=1)
                hours   = lc2.number_input("Hours each", min_value=0.0, value=0.0, step=0.5, format="%.1f")
                rate    = st.number_input("Labor rate ($/hr)", min_value=0.0, value=85.0, step=5.0, format="%.2f")
                labor   = workers * hours * rate
                st.metric("Labor Total", f"${labor:,.0f}")

            with st.expander("🪛 Materials", expanded=True):
                if hist_material is not None:
                    st.caption(f"Historical median for {job_type}: **${hist_material:,.0f}**")
                if "material_items" not in st.session_state:
                    st.session_state.material_items = [{"Item": "", "Cost ($)": 0.0}]
                edited = st.data_editor(
                    pd.DataFrame(st.session_state.material_items),
                    num_rows="dynamic",
                    use_container_width=True,
                    key="mat_editor",
                    column_config={
                        "Item":     st.column_config.TextColumn("Item", width="medium"),
                        "Cost ($)": st.column_config.NumberColumn("Cost ($)", min_value=0.0, format="$%.2f"),
                    },
                )
                st.session_state.material_items = edited.to_dict("records")
                material = float(edited["Cost ($)"].fillna(0).sum())
                st.metric("Materials Total", f"${material:,.0f}")

            with st.expander("📋 PO / Bill Costs", expanded=False):
                if hist_po is not None:
                    st.caption(f"Historical median for {job_type}: **${hist_po:,.0f}**")
                po = st.number_input("PO / Bill Cost ($)", min_value=0.0, value=0.0, step=100.0, format="%.2f", label_visibility="collapsed")

            total_cost = labor + material + po
            st.metric("Total Estimated Cost", f"${total_cost:,.0f}")

        st.divider()
        quote = st.number_input("Proposed Quote ($)", min_value=0.0, value=0.0, step=100.0, format="%.2f")

        if SERVICETITAN_ENABLED:
            st.text_input("ServiceTitan Job ID (optional)", key="st_job_id")

    # ── Guard: need valid inputs before computing ─────────────────────────────
    ready = total_cost > 0 and quote > 0

    # ── Column 2: Model Benchmark ─────────────────────────────────────────────
    with col2:
        st.markdown("#### Model Benchmark")

        if not ready:
            st.info("Enter costs and a proposed quote to see the benchmark.")
        else:
            predicted_gp = predict_margin(model_b, encoders, job_type, prop_type, quote, month)
            thresholds   = encoders.get("margin_thresholds", {})
            result = flag_summary(quote, total_cost, predicted_gp, job_type=job_type, thresholds=thresholds)

            confidence_label, confidence_val = model_confidence_label(job_type, jt_counts)

            st.metric("Benchmark Price", f"${result['benchmark_price']:,.0f}")
            st.metric(
                "Recommended Range",
                f"${result['range_low']:,.0f} – ${result['range_high']:,.0f}",
            )
            st.metric("Predicted GP%", f"{predicted_gp:.1%}")

            st.markdown(f"**Model Confidence:** {confidence_label}")
            st.progress(confidence_val)
            n = jt_counts.get(job_type, 0)
            st.caption(f"Based on {n} historical {job_type} jobs")

            # ── Historical similar jobs ───────────────────────────────────
            history = load_scored_history()
            if history is not None:
                similar = (
                    history[history["Job Type"] == job_type]
                    .dropna(subset=["Actual GP%", "Actual Revenue ($)"])
                    .sort_values("Completion Date", ascending=False)
                    .head(8)
                )
                if len(similar) > 0:
                    st.divider()
                    st.markdown(f"**Recent {job_type} jobs**")
                    display = similar[[
                        "Completion Date", "Actual Revenue ($)", "Actual GP%"
                    ]].copy()
                    display["Completion Date"] = display["Completion Date"].dt.strftime("%b %Y")
                    display["Actual Revenue ($)"] = display["Actual Revenue ($)"].map("${:,.0f}".format)
                    display["Actual GP%"] = display["Actual GP%"].map("{:.1%}".format)
                    display.columns = ["Date", "Revenue", "GP%"]
                    st.dataframe(display, use_container_width=True, hide_index=True)

                    avg_gp  = similar["Actual GP%"].mean()
                    avg_rev = similar["Actual Revenue ($)"].mean()
                    st.caption(
                        f"Historical avg: {avg_gp:.1%} GP | ${avg_rev:,.0f} revenue "
                        f"({len(similar)} jobs)"
                    )

            # Model A revenue note
            if labor > 0 or material > 0 or po > 0:
                predicted_rev = predict_revenue(
                    model_a, encoders, job_type, prop_type, labor, material, po, month
                )
                rev_gap = (predicted_rev - quote) / quote
                direction_word = "above" if rev_gap > 0 else "below"
                st.divider()
                st.caption(
                    f"**Revenue model (Model A):** suggests ${predicted_rev:,.0f} — "
                    f"your quote is {abs(rev_gap):.1%} {direction_word} that estimate."
                )

    # ── Column 3: Flag Result & Action ────────────────────────────────────────
    with col3:
        st.markdown("#### Flag Result & Action")

        if not ready:
            st.info("Complete Job Inputs to see the flag.")
            return

        flag               = result["flag"]
        dev                = result["deviation_pct"]
        margin             = result["expected_margin"]
        dirn               = result["direction"]
        margin_floor_red   = result["margin_floor_red"]
        margin_floor_yellow = result["margin_floor_yellow"]

        # Status badge
        if flag == "green":
            st.success("✅ GREEN — Within benchmark range")
        elif flag == "yellow":
            st.warning("⚠️ YELLOW — Outside range, reason required")
        else:
            st.error("🔴 RED — Manager approval required")

        # Metrics
        m1, m2 = st.columns(2)
        with m1:
            if dev > 0:
                st.metric("Deviation", f"{dev:.1%} {dirn}", delta=f"{dirn}", delta_color="inverse")
            else:
                st.metric("Deviation", "Within range")
        with m2:
            margin_color = "normal" if margin >= MARGIN_FLOOR else "inverse"
            st.metric("Expected Margin", f"{margin:.1%}", delta_color=margin_color)

        if margin < margin_floor_red:
            st.error(f"Margin {margin:.1%} is below the {margin_floor_red:.0%} floor for {job_type}.")
        elif margin < margin_floor_yellow:
            st.warning(f"Margin {margin:.1%} is near the {margin_floor_yellow:.0%} median for {job_type}.")

        # ── Exception analysis & guidance ─────────────────────────────────────
        with st.expander("📊 What's driving this flag?", expanded=(flag != "green")):
            drivers = []

            # Deviation driver
            if dev > 0:
                drivers.append(
                    f"**Quote deviation ({dev:.1%} {dirn} range):** "
                    f"Your quote of ${quote:,.0f} sits outside the "
                    f"${result['range_low']:,.0f}–${result['range_high']:,.0f} benchmark range "
                    f"(built from a predicted GP% of {predicted_gp:.1%} for this job type)."
                )

            # Margin driver
            if margin < margin_floor_red:
                drivers.append(
                    f"**Low margin ({margin:.1%}):** "
                    f"At this quote, cost recovery leaves only {margin:.1%} gross margin — "
                    f"below the {margin_floor_red:.0%} floor for {job_type} "
                    f"(25th percentile of historical actuals). Consider raising the quote or "
                    f"reviewing cost estimates."
                )
            elif margin < margin_floor_yellow:
                drivers.append(
                    f"**Near-floor margin ({margin:.1%}):** "
                    f"Margin is above the {margin_floor_red:.0%} floor but below the "
                    f"{margin_floor_yellow:.0%} median for {job_type}."
                )

            # Historical guidance
            history = load_scored_history()
            if history is not None:
                similar = history[history["Job Type"] == job_type].dropna(subset=["Actual GP%"])
                if len(similar) >= 3:
                    hist_gp_med  = similar["Actual GP%"].median()
                    hist_gp_std  = similar["Actual GP%"].std()
                    hist_rev_med = similar["Actual Revenue ($)"].median() if "Actual Revenue ($)" in similar.columns else None
                    drivers.append(
                        f"**Historical reference ({len(similar)} {job_type} jobs):** "
                        f"Median actual GP% is {hist_gp_med:.1%} (std ±{hist_gp_std:.1%})"
                        + (f", median revenue is ${hist_rev_med:,.0f}." if hist_rev_med else ".")
                    )
                    if hist_gp_std > 0.15:
                        drivers.append(
                            f"⚠️ **High margin variability** for {job_type} (std ±{hist_gp_std:.1%}) — "
                            f"margins on this job type vary widely; cost estimates matter more than usual."
                        )
                    if predicted_gp < hist_gp_med - 0.05:
                        drivers.append(
                            f"⚠️ Model predicts {predicted_gp:.1%} GP — "
                            f"notably below the {hist_gp_med:.1%} historical median. "
                            f"This job type may have unusual cost exposure."
                        )

            # Cost structure guidance (estimating mode only)
            if not field_mode and total_cost > 0:
                lc_share = labor    / total_cost
                mc_share = material / total_cost
                cost_stats_local = load_job_cost_stats()
                if job_type in cost_stats_local.index:
                    h_labor = cost_stats_local.loc[job_type, "total_labor"]
                    h_mat   = cost_stats_local.loc[job_type, "Material Costs"]
                    h_total = h_labor + h_mat + cost_stats_local.loc[job_type, "PO/Bill Costs"]
                    if h_total > 0:
                        h_lc = h_labor / h_total
                        h_mc = h_mat   / h_total
                        if abs(lc_share - h_lc) > 0.10:
                            direction = "higher" if lc_share > h_lc else "lower"
                            drivers.append(
                                f"**Labor mix:** Your labor is {lc_share:.0%} of total cost vs. "
                                f"a historical {h_lc:.0%} — {direction} than typical."
                            )
                        if abs(mc_share - h_mc) > 0.10:
                            direction = "higher" if mc_share > h_mc else "lower"
                            drivers.append(
                                f"**Material mix:** Your materials are {mc_share:.0%} of total cost vs. "
                                f"a historical {h_mc:.0%} — {direction} than typical."
                            )

            if flag == "green" and not drivers:
                st.success("No exceptions — quote is within range and margin is healthy.")
            else:
                for d in drivers:
                    st.markdown(f"- {d}")

        st.divider()

        # Override fields
        reason_code     = ""
        notes           = ""
        manager_approved = False

        if flag in ("yellow", "red"):
            reason_code = st.selectbox("Reason Code", REASON_CODES)
            notes = st.text_area("Notes (optional)", height=80)

        if flag == "red":
            manager_approved = st.checkbox("Manager approval obtained")

        # Submit
        can_submit = (
            flag == "green"
            or (flag == "yellow" and reason_code not in ("", "— select —"))
            or (flag == "red" and reason_code not in ("", "— select —") and manager_approved)
        )

        submit_label = {
            "green":  "Log & Proceed",
            "yellow": "Submit with Reason",
            "red":    "Submit for Manager Approval",
        }[flag]

        if st.button(submit_label, disabled=not can_submit, type="primary"):
            st_job_id = st.session_state.get("st_job_id", "")
            fb.log_decision(
                job_type=job_type,
                property_type=prop_type,
                quote=quote,
                total_cost=total_cost,
                benchmark_price=result["benchmark_price"],
                range_low=result["range_low"],
                range_high=result["range_high"],
                deviation_pct=result["deviation_pct"],
                expected_margin=result["expected_margin"],
                flag_status=flag,
                reason_code=reason_code,
                notes=notes,
                manager_approved=manager_approved,
                servicetitan_job_id=st_job_id,
            )

            # ServiceTitan push (no-op when disabled)
            from servicetitan import push_job_flag
            push_job_flag({
                "servicetitan_job_id": st_job_id,
                "flag_status": flag,
                "benchmark_price": result["benchmark_price"],
                "range_low": result["range_low"],
                "range_high": result["range_high"],
                "deviation_pct": result["deviation_pct"],
                "expected_margin": result["expected_margin"],
                "reason_code": reason_code,
                "notes": notes,
            })

            st.success("Decision logged.")


def render_history_tab():
    st.subheader("Decision History")

    log = fb.load_log()
    if log is None:
        st.info("No decisions logged yet. Submit a bid check to start the feedback loop.")
        return

    log["timestamp"] = pd.to_datetime(log["timestamp"])

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=True):
        f1, f2, f3 = st.columns(3)

        with f1:
            all_job_types = sorted(log["job_type"].dropna().unique().tolist())
            sel_job_types = st.multiselect(
                "Job Type", all_job_types, default=all_job_types, key="hist_jt"
            )

        with f2:
            sel_flags = st.multiselect(
                "Flag Status",
                ["green", "yellow", "red"],
                default=["green", "yellow", "red"],
                format_func=lambda x: x.capitalize(),
                key="hist_flag",
            )

        with f3:
            min_date = log["timestamp"].dt.date.min()
            max_date = log["timestamp"].dt.date.max()
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="hist_date",
            )

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = log.copy()
    if sel_job_types:
        filtered = filtered[filtered["job_type"].isin(sel_job_types)]
    if sel_flags:
        filtered = filtered[filtered["flag_status"].isin(sel_flags)]
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[
            (filtered["timestamp"].dt.date >= start) &
            (filtered["timestamp"].dt.date <= end)
        ]

    # ── Summary metrics (filtered) ────────────────────────────────────────────
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Decisions", len(filtered))
    m2.metric("Avg Expected Margin", f"{filtered['expected_margin_pct'].mean():.1f}%" if len(filtered) else "—")
    m3.metric("Avg Deviation", f"{filtered['deviation_pct'].mean():.1f}%" if len(filtered) else "—")
    m4.metric("Job Types", filtered["job_type"].nunique())

    # ── Flag breakdown (filtered) ─────────────────────────────────────────────
    flag_counts = filtered["flag_status"].value_counts()
    cols = st.columns(3)
    for i, (flag, label, color) in enumerate([
        ("green",  "Green",  "#2e7d32"),
        ("yellow", "Yellow", "#f57f17"),
        ("red",    "Red",    "#c62828"),
    ]):
        with cols[i]:
            n = int(flag_counts.get(flag, 0))
            st.markdown(
                f"<div style='text-align:center;padding:12px;border-radius:8px;"
                f"background:{color}22;border:1px solid {color}55'>"
                f"<span style='font-size:1.6em;font-weight:700;color:{color}'>{n}</span>"
                f"<br><span style='color:{color}'>{label}</span></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Margin by job type (filtered) ─────────────────────────────────────────
    if len(filtered) > 0:
        st.markdown("**Average Expected Margin % by Job Type**")
        by_jt = (
            filtered.groupby("job_type")["expected_margin_pct"]
            .agg(["mean", "count"])
            .rename(columns={"mean": "Avg Margin %", "count": "Jobs"})
            .sort_values("Avg Margin %", ascending=False)
            .reset_index()
            .rename(columns={"job_type": "Job Type"})
        )
        by_jt["Avg Margin %"] = by_jt["Avg Margin %"].map("{:.1f}%".format)
        st.dataframe(by_jt, use_container_width=True, hide_index=True)

    # ── Reason code breakdown ─────────────────────────────────────────────────
    overrides = filtered[filtered["reason_code"].notna() & (filtered["reason_code"] != "")]
    if len(overrides) > 0:
        st.markdown("**Override Reason Codes**")
        reason_counts = (
            overrides["reason_code"]
            .value_counts()
            .reset_index()
            .rename(columns={"reason_code": "Reason", "count": "Count"})
        )
        st.dataframe(reason_counts, use_container_width=True, hide_index=True)

    st.divider()

    # ── Full filtered table ───────────────────────────────────────────────────
    st.markdown("**All Logged Decisions**")
    display_cols = [
        "timestamp", "job_type", "property_type", "quote", "total_cost",
        "benchmark_price", "deviation_pct", "expected_margin_pct",
        "flag_status", "reason_code", "notes",
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]
    st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered log as CSV",
        data=csv,
        file_name="feedback_log_filtered.csv",
        mime="text/csv",
    )


def render_client_margin_tab():
    st.subheader("Cumulative Margin by Client")
    st.caption("Combines all completed company jobs per customer to show the blended margin picture.")

    history = load_scored_history()
    if history is None:
        st.info("Scored predictions file not found.")
        return

    needed = ["Customer Name", "Job Type", "Actual Revenue ($)", "Actual GP%", "Completion Date"]
    if not all(c in history.columns for c in needed):
        st.warning("Scored predictions file is missing expected columns.")
        return

    df = history.dropna(subset=["Customer Name", "Actual Revenue ($)", "Actual GP%"]).copy()
    df["Gross Margin ($)"] = df["Actual Revenue ($)"] * df["Actual GP%"]

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=True):
        cf1, cf2, cf3 = st.columns(3)
        with cf1:
            search = st.text_input("Search customer name", "")
        with cf2:
            all_jt = sorted(df["Job Type"].dropna().unique().tolist())
            sel_jt = st.multiselect("Job Type", all_jt, default=all_jt, key="cm_jt")
        with cf3:
            min_jobs = st.number_input("Min jobs per client", min_value=1, value=1, step=1)

    filtered = df.copy()
    if search:
        filtered = filtered[filtered["Customer Name"].str.contains(search, case=False, na=False)]
    if sel_jt:
        filtered = filtered[filtered["Job Type"].isin(sel_jt)]

    # ── Aggregate per client ──────────────────────────────────────────────────
    client_summary = (
        filtered.groupby("Customer Name")
        .agg(
            Jobs=("Actual Revenue ($)", "count"),
            Total_Revenue=("Actual Revenue ($)", "sum"),
            Total_GM=("Gross Margin ($)", "sum"),
            Job_Types=("Job Type", lambda x: ", ".join(sorted(x.dropna().unique()))),
            Last_Job=("Completion Date", "max"),
        )
        .reset_index()
    )
    client_summary["Blended GP%"] = client_summary["Total_GM"] / client_summary["Total_Revenue"]
    client_summary = client_summary[client_summary["Jobs"] >= min_jobs]
    client_summary = client_summary.sort_values("Total_Revenue", ascending=False)

    # ── Top-level metrics ─────────────────────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    m1.metric("Clients shown", len(client_summary))
    m2.metric("Total Revenue", f"${client_summary['Total_Revenue'].sum():,.0f}")
    m3.metric("Portfolio Blended GP%", f"{(client_summary['Total_GM'].sum() / client_summary['Total_Revenue'].sum()):.1%}" if client_summary['Total_Revenue'].sum() > 0 else "—")

    st.divider()

    # ── Margin health breakdown ────────────────────────────────────────────────
    st.markdown("**Client Margin Health**")
    st.caption("Thresholds shown are global portfolio floors — not per-job-type.")
    from flag_logic import MARGIN_FLOOR, MARGIN_YELLOW_FLOOR
    strong  = client_summary[client_summary["Blended GP%"] >= MARGIN_YELLOW_FLOOR]
    warning = client_summary[(client_summary["Blended GP%"] >= MARGIN_FLOOR) & (client_summary["Blended GP%"] < MARGIN_YELLOW_FLOOR)]
    at_risk = client_summary[client_summary["Blended GP%"] < MARGIN_FLOOR]

    hc1, hc2, hc3 = st.columns(3)
    hc1.metric(f"Strong (≥{MARGIN_YELLOW_FLOOR:.0%})", len(strong))
    hc2.metric(f"Watch ({MARGIN_FLOOR:.0%}–{MARGIN_YELLOW_FLOOR:.0%})", len(warning))
    hc3.metric(f"At Risk (<{MARGIN_FLOOR:.0%})", len(at_risk))

    st.divider()

    # ── Client table ──────────────────────────────────────────────────────────
    display = client_summary.copy()
    display["Total Revenue"] = display["Total_Revenue"].map("${:,.0f}".format)
    display["Blended GP%"]   = display["Blended GP%"].map("{:.1%}".format)
    display["Last Job"]      = pd.to_datetime(display["Last_Job"]).dt.strftime("%b %Y")
    display = display.rename(columns={
        "Customer Name": "Customer",
        "Jobs": "Jobs",
        "Job_Types": "Job Types",
    })[["Customer", "Jobs", "Total Revenue", "Blended GP%", "Job Types", "Last Job"]]

    st.dataframe(display, use_container_width=True, hide_index=True)

    csv = display.to_csv(index=False).encode("utf-8")
    st.download_button("Download client margin summary", data=csv,
                       file_name="client_margin_summary.csv", mime="text/csv")

    # ── At-risk client detail ─────────────────────────────────────────────────
    if len(at_risk) > 0:
        st.divider()
        st.markdown(f"**At-Risk Clients (Blended GP% < {MARGIN_FLOOR:.0%})**")
        at_risk_display = at_risk.copy()
        at_risk_display["Total Revenue"] = at_risk_display["Total_Revenue"].map("${:,.0f}".format)
        at_risk_display["Blended GP%"]   = at_risk_display["Blended GP%"].map("{:.1%}".format)
        st.dataframe(
            at_risk_display[["Customer Name", "Jobs", "Total Revenue", "Blended GP%", "Job_Types"]]
            .rename(columns={"Customer Name": "Customer", "Job_Types": "Job Types"}),
            use_container_width=True, hide_index=True,
        )


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    field_mode = render_sidebar()

    model_a, model_b, encoders = load_models()

    if model_a is None:
        st.error(
            "Models not found. Run `python train_models.py` from the repo root first, "
            "then restart the app."
        )
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Bid Check", "Decision History", "Client Margins"])

    with tab1:
        render_checker_tab(model_a, model_b, encoders, field_mode=field_mode)

    with tab2:
        render_history_tab()

    with tab3:
        render_client_margin_tab()


if __name__ == "__main__":
    main()
