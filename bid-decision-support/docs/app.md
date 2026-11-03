# How `app.py` Works

## Likely Broken Link

The most common confusion with a file like this is thinking it contains the "intelligence" of the tool. It doesn't — `app.py` is the conductor, not the orchestra. The math lives in `flag_logic.py`, the models live in saved files, and the logging lives in `feedback.py`. `app.py`'s job is to collect inputs from the user, call those other pieces, and display the results on screen. Keeping that division clear makes the whole system readable.

---

## Rebuild

### What Kind of File This Is

`app.py` is a **Streamlit** application. Streamlit is a Python library that turns a regular Python script into an interactive web page — buttons, dropdowns, number inputs, and colored result boxes — without requiring any knowledge of HTML, JavaScript, or traditional web development. When you run `streamlit run app.py` in a terminal, Streamlit reads the file top to bottom and renders the page.

Every time a user changes an input (say, updates the quote amount), Streamlit re-runs the entire file from top to bottom. That's why variables are recalculated live — there's no manual "refresh" needed.

---

### The Imports: What Gets Loaded

At the top, the file pulls in the tools it needs:

- `numpy` / `pandas` — standard scientific Python libraries for numbers and tables
- `joblib` — loads the trained machine learning models from disk (they were saved as `.pkl` files, a compressed binary format)
- `streamlit` — the web interface library
- `flag_logic`, `feedback`, `servicetitan` — the other three files in this same folder

---

### Model Loading: `load_models()`

Before any predictions can happen, the two trained models and a collection of supporting data called `encoders` need to be loaded from the `models/` folder on disk. The function does this once and caches the result — meaning Streamlit won't reload the files from disk on every user interaction, which would be slow.

If the model files aren't found (because `train_models.py` hasn't been run yet), the app displays an error message and stops.

**What are `encoders`?** Machine learning models can't work with text labels like "Drain Cleaning" or "Commercial" — they require numbers. The `encoders` object contains the mapping that was built during training: e.g., "Drain Cleaning" → 3, "Commercial" → 1. It also stores the list of valid job types, property types, and which input columns each model expects.

---

### The Two Prediction Functions

#### `predict_margin()` — Model B

Model B predicts the gross profit percentage (GP%) a job of a given type, size, and timing is likely to produce. Its inputs are:

- Job type and property type (converted to numbers via encoders)
- The proposed quote amount and its log-transform (a mathematical compression that makes large dollar ranges easier for models to handle)
- The month and the derived quarter

It returns a single decimal, e.g. `0.61` meaning 61% predicted GP%.

#### `predict_revenue()` — Model A

Model A predicts what revenue a job should generate given its cost breakdown — labor, materials, and PO/Bill costs. It uses more inputs than Model B because it reasons from cost structure rather than from the quote itself.

The function also computes derived ratios before feeding them to the model:
- `labor_cost_share` = labor ÷ total cost (what fraction of the job's cost is labor)
- `material_cost_share` = material ÷ total cost
- `labor_to_material` = labor ÷ material (how labor-heavy vs. material-heavy the job is)

These ratios help the model generalize across jobs of very different total sizes.

Model A's output is used as a secondary reference point: the app notes whether your quote is above or below what Model A would expect, without flagging it directly.

---

### The Sidebar: `render_sidebar()`

The sidebar is a persistent panel on the left side of the screen. It shows:
- The app name and company name
- Whether ServiceTitan is connected (pulled from `servicetitan.py`'s on/off switch)
- The current flag thresholds (pulled from `flag_logic.py`'s named constants)

This is intentional design: if a manager changes the thresholds in `flag_logic.py`, the sidebar automatically shows the updated values — no one has to remember to update the display separately.

---

### The Main Tab: `render_checker_tab()`

This is the largest function in the file, broken into three visual columns.

**Column 1 — Job Inputs:** The estimator selects job type, property type, enters cost breakdowns (labor, material, PO), types a proposed quote, and picks a completion month. Total cost is computed and displayed live.

**Column 2 — Model Benchmark:** Once costs and a quote are entered, the app runs `predict_margin()` (Model B) to get a predicted GP%, then calls `flag_summary()` from `flag_logic.py` to get the benchmark price, acceptable range, and flag. It displays:
- The benchmark price and range
- Predicted GP%
- Model confidence (based on how many historical jobs of that type were in the training data — more examples = higher confidence)
- A secondary note from Model A comparing the quote to the revenue model's estimate

**Column 3 — Flag Result & Action:** Shows the green/yellow/red badge and the key metrics. If the flag is yellow or red, required fields appear:
- A reason code dropdown (mandatory)
- A notes text box (optional)
- A manager approval checkbox (red only)

The submit button is disabled until all required fields are filled. When clicked, it calls `fb.log_decision()` to write the decision to the feedback log, then calls `push_job_flag()` from `servicetitan.py` (which currently does nothing, since integration is disabled).

---

### The History Tab: `render_history_tab()`

Reads `feedback_log.csv` via `feedback.py` and displays it as a scrollable table. A download button lets anyone export the full log as a CSV. Summary counts of green/yellow/red decisions are shown as colored stat boxes.

---

### The Entry Point: `main()`

At the bottom, `main()` ties everything together in order:

1. Render the sidebar
2. Load the models
3. If models are missing, show an error and stop
4. Create two tabs ("Bid Check" and "Decision History")
5. Render each tab with its respective function

The final two lines:
```python
if __name__ == "__main__":
    main()
```
...mean "only run `main()` when this file is executed directly." This is standard Python convention to prevent the app from launching if the file is imported by another script.

---

## Takeaway

`app.py` is the shell that connects everything. It handles what the user sees and types, calls `flag_logic.py` for the math, calls the models for predictions, and calls `feedback.py` to record what happened. None of the core logic lives here — it's all wiring and display. If you want to understand how the flag is calculated, look at `flag_logic.py`. If you want to understand what gets saved, look at `feedback.py`.

> **Self-check:** If you wanted to add a new input field (say, "Permit Cost") that contributes to total cost, which file would you edit first, and what else would need to change downstream?  
> *(Answer: `app.py` for the new input widget and the updated total cost calculation; `train_models.py` and the model features would need updating if you wanted the models to actually use the new field — adding the UI input alone wouldn't automatically teach the model about permit costs.)*
