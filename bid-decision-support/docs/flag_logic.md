# How `flag_logic.py` Works

## Likely Broken Link

The most common confusion here is thinking the "flag" (green/yellow/red) comes from one single calculation. It doesn't — it combines two independent signals: how far your quote deviates from a model-predicted benchmark price, and whether your gross margin falls below a minimum floor. Understanding those two signals separately is the key.

---

## Rebuild

### What This File Is For

`flag_logic.py` is the pure math engine of the app. It takes three raw numbers — your proposed quote, your total estimated cost, and the model's predicted gross profit percentage — and turns them into a single verdict: Green, Yellow, or Red.

It has no buttons, no screen, no interface. It just does arithmetic. The visual app (`app.py`) calls it and uses its output to decide what to show the estimator.

---

### Step 1: Turning GP% into a Benchmark Price

**Gross profit percentage (GP%)** — also called gross margin — is the fraction of revenue left over after paying direct costs. If you charge $100 for a job and it costs you $60, your GP% is 40%.

The model predicts what GP% a job of this type, size, and timing *historically* achieves. From that predicted GP%, the code back-calculates what the quote price *should* be:

```
benchmark_price = total_cost / (1 - predicted_GP%)
```

**Why does that formula work?** GP% is defined as `(revenue - cost) / revenue`. Rearranging algebraically gives `revenue = cost / (1 - GP%)`. So if costs are $60,000 and the model predicts a 40% margin, the benchmark price is `$60,000 / (1 - 0.40) = $100,000`.

The code then adds a ±10% tolerance band around that benchmark:

```
range_low  = benchmark_price × 0.90
range_high = benchmark_price × 1.10
```

A quote anywhere inside that band is considered "within range."

---

### Step 2: Measuring Deviation

Once the range is set, the code checks where your proposed quote lands:

- **Below the range** → deviation = `(range_low - quote) / range_low`
- **Above the range** → deviation = `(quote - range_high) / range_high`
- **Inside the range** → deviation = 0, direction = "within"

This deviation is expressed as a percentage. A quote $5,000 below a $100,000 range_low has a 5% downward deviation.

---

### Step 3: Computing Your Actual Margin

Separately from the benchmark, the code computes what gross margin your proposed quote would actually produce:

```
expected_margin = (quote - total_cost) / quote
```

This is not the model's prediction. This is the real arithmetic of your specific quote. If you quote $90,000 on a $60,000-cost job, your actual margin is `($90,000 - $60,000) / $90,000 = 33.3%`.

---

### Step 4: Combining Into a Flag

The flag uses both signals, and **Red always wins over Yellow**:

| Condition | Flag |
|---|---|
| Margin < 40% OR deviation > 20% outside range | 🔴 Red |
| Margin < 50% OR any deviation outside range | 🟡 Yellow |
| Neither | 🟢 Green |

The thresholds (10%, 20%, 40%, 50%) are named constants at the top of the file. They are the only things you need to touch if management wants to tighten or loosen the rules — the rest of the logic stays the same.

---

### The Convenience Wrapper

`flag_summary()` is just a single function that runs all four steps above and returns everything as one package (a Python dictionary). `app.py` calls only this one function rather than calling each step individually.

---

## Takeaway

`flag_logic.py` runs two independent checks — "is your price near what the model expects?" and "does your margin clear the floor?" — then combines them into one traffic-light verdict. Red wins over Yellow. All the tunable rules live in the constants at the top of the file.

> **Self-check:** If a quote is inside the ±10% benchmark range but the actual margin works out to 38%, what flag does it get, and why?  
> *(Answer: Red — because the 38% margin is below the 40% floor, and the margin-red condition overrides the fact that the price is within range.)*
