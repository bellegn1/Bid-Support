# How `feedback.py` Works

## Likely Broken Link

The word "feedback" here does not mean user interface feedback (like a success message). It means a data feedback loop — every time an estimator submits a bid decision, that decision gets written to a file, building a dataset of real outcomes over time. Understanding that this file is a logging mechanism, not a display mechanism, is the key.

---

## Rebuild

### What This File Is For

`feedback.py` has exactly one job: record what happened. Every time an estimator submits a bid check in the app — whether green, yellow, or red — `feedback.py` appends one new row to a spreadsheet-style file called `feedback_log.csv`.

Over weeks and months, this log becomes the raw material for retraining and improving the prediction models. The file does no math, no flagging, and no screen rendering. It only reads and writes data.

---

### The Log File

The log is stored at `data/feedback_log.csv` relative to the project root. A CSV (comma-separated values) file is essentially a plain-text spreadsheet — each line is one row, and each value is separated by a comma. Any spreadsheet program (Excel, Google Sheets) can open it.

Each row records 15 pieces of information:

| Column | What It Captures |
|---|---|
| `timestamp` | Exact date and time the decision was submitted |
| `job_type` | The type of job (e.g., Water Heater, Drain Cleaning) |
| `property_type` | Residential or Commercial |
| `quote` | The dollar amount the estimator proposed |
| `total_cost` | Total estimated cost (labor + material + PO) |
| `benchmark_price` | What the model said the price should be |
| `range_low` / `range_high` | The ±10% acceptable band around the benchmark |
| `deviation_pct` | How far outside the range the quote was (as a %) |
| `expected_margin_pct` | The gross margin the proposed quote would produce |
| `flag_status` | green, yellow, or red |
| `reason_code` | Why the estimator deviated (if yellow/red) |
| `notes` | Free-text explanation |
| `manager_approved` | True/False — was manager sign-off obtained? |
| `servicetitan_job_id` | The job's ID in the ServiceTitan system (optional) |

---

### The Two Functions

#### `log_decision()`

This function is called by `app.py` every time the estimator clicks the submit button. It:

1. Builds one row as a Python dictionary (a key-value pair structure, like a labeled container for each piece of data).
2. Converts that dictionary into a single-row DataFrame — a table object that the pandas library can write to a file.
3. Checks whether `feedback_log.csv` already exists.
   - If it does not exist yet: writes the row and includes the column header row at the top.
   - If it already exists: appends the row without repeating the headers.

The `mode="a"` in the write command means "append" — add to the end rather than overwrite from the beginning.

#### `load_log()`

This function is called by the "Decision History" tab in `app.py`. It checks whether `feedback_log.csv` exists, and if so, reads it into a DataFrame so it can be displayed as a table on screen. If no decisions have been logged yet, it returns `None` and the app shows a message instead.

---

### A Concrete Example

Imagine an estimator submits a yellow-flagged bid for a commercial drain cleaning job. Here is what one row in `feedback_log.csv` would look like:

```
2026-05-12T14:33:07,Drain Cleaning,Commercial,8500.00,5200.00,9100.00,8190.00,10010.00,7.14,35.29,yellow,Competitive pressure,,False,
```

Each value maps directly to a column header. The empty fields are `notes` (no notes written) and `servicetitan_job_id` (not filled in).

---

## Takeaway

`feedback.py` is a write-and-read log. Every bid decision adds one row to a CSV file, and the History tab reads that same file back for display. The longer the app runs, the more decisions are captured — and that accumulating record is what eventually feeds back into improving the model.
