"""
Benchmark range, deviation, and margin flag calculations.
All thresholds are named constants — tune here without touching the UI.

Margin floors are per-job-type (computed from historical actuals in
train_models.py). Global fallback constants are used for job types
with insufficient history (< 10 jobs).
"""

# ── Global fallback thresholds ────────────────────────────────────────────────
BENCHMARK_TOLERANCE = 0.10   # ±10% defines the green benchmark range
YELLOW_THRESHOLD    = 0.20   # 0–20% outside range boundary → Yellow
# >20% outside range boundary OR margin below job-type floor → Red
MARGIN_FLOOR        = 0.40   # global fallback Red floor
MARGIN_YELLOW_FLOOR = 0.50   # global fallback Yellow floor


def get_margin_floors(job_type: str, thresholds: dict) -> tuple[float, float]:
    """
    Look up the Red and Yellow margin floors for a given job type.

    Falls back to global constants if the job type isn't in the threshold
    dict or was flagged as a fallback due to insufficient history.
    """
    entry = thresholds.get(job_type) or thresholds.get("__global__", {})
    red    = entry.get("red",    MARGIN_FLOOR)
    yellow = entry.get("yellow", MARGIN_YELLOW_FLOOR)
    return red, yellow


def compute_benchmark(total_cost: float, predicted_gp: float) -> tuple[float, float, float]:
    """
    Derive benchmark price and ±BENCHMARK_TOLERANCE range from predicted GP%.

    Returns (benchmark_price, range_low, range_high).
    Clamps predicted_gp to [0.01, 0.95] to avoid divide-by-zero or negative prices.
    """
    gp = max(0.01, min(0.95, predicted_gp))
    benchmark = total_cost / (1.0 - gp)
    return benchmark, benchmark * (1 - BENCHMARK_TOLERANCE), benchmark * (1 + BENCHMARK_TOLERANCE)


def compute_deviation(quote: float, range_low: float, range_high: float) -> tuple[float, str]:
    """
    Measure how far a quote sits outside the benchmark range.

    Returns (deviation_pct, direction) where:
      deviation_pct > 0  means outside the range
      direction          is "below", "above", or "within"
    """
    if quote < range_low:
        return (range_low - quote) / range_low, "below"
    if quote > range_high:
        return (quote - range_high) / range_high, "above"
    return 0.0, "within"


def compute_margin(quote: float, total_cost: float) -> float:
    """Expected gross margin % at the proposed quote price."""
    if quote <= 0:
        return 0.0
    return (quote - total_cost) / quote


def compute_flag(
    deviation_pct: float,
    expected_margin: float,
    margin_floor_red: float,
    margin_floor_yellow: float,
) -> str:
    """
    Combine deviation and margin signals into a single Green / Yellow / Red flag.
    Red wins over Yellow — always apply the stricter flag.
    Margin floors are job-type specific.
    """
    margin_red       = expected_margin < margin_floor_red
    margin_yellow    = expected_margin < margin_floor_yellow
    deviation_red    = deviation_pct > YELLOW_THRESHOLD
    deviation_yellow = deviation_pct > 0

    if margin_red or deviation_red:
        return "red"
    if margin_yellow or deviation_yellow:
        return "yellow"
    return "green"


def flag_summary(
    quote: float,
    total_cost: float,
    predicted_gp: float,
    job_type: str = "",
    thresholds: dict | None = None,
) -> dict:
    """
    Convenience wrapper — returns all computed values as a single dict.
    Used by app.py to get everything in one call.
    """
    t = thresholds or {}
    margin_floor_red, margin_floor_yellow = get_margin_floors(job_type, t)

    benchmark, range_low, range_high = compute_benchmark(total_cost, predicted_gp)
    deviation_pct, direction = compute_deviation(quote, range_low, range_high)
    expected_margin = compute_margin(quote, total_cost)
    flag = compute_flag(deviation_pct, expected_margin, margin_floor_red, margin_floor_yellow)

    return {
        "benchmark_price":      benchmark,
        "range_low":            range_low,
        "range_high":           range_high,
        "deviation_pct":        deviation_pct,
        "direction":            direction,
        "expected_margin":      expected_margin,
        "flag":                 flag,
        "margin_floor_red":     margin_floor_red,
        "margin_floor_yellow":  margin_floor_yellow,
    }
