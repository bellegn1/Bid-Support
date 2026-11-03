# Bid Decision Support Tool

A pricing-intelligence app that helps estimators at a commercial plumbing contractor check a bid **before** they send it. Enter the job type and estimated costs, and the app returns a model-predicted benchmark price, an acceptable price range, the expected margin, and a green / yellow / red verdict that tells the estimator whether the bid is fine, needs a reason code, or needs manager approval.

> **About the data:** This project was originally built for a real client. All client data has been removed. The repo ships with a generator that creates realistic **synthetic** job data with the same schema, so everything runs end to end without any confidential information.

## The problem

The company had years of job history in its field-service software, but none of it was visible at the moment an estimator was building a quote. Pricing depended on individual experience, which led to inconsistent margins across estimators and job types and no easy way to spot under-priced bids before they went out.

## How it works

**Model A: Revenue consistency.** An XGBoost regressor trained on labor, material, and PO costs (plus engineered cost-mix features) predicts what the company has historically billed for jobs with similar cost inputs. It's shown as a secondary reference point.

**Model B: Bid-time margin.** A second XGBoost model predicts gross margin % using only information available at quoting time. The app converts that predicted margin into a benchmark price (`cost / (1 − GP%)`) with a ±10% tolerance band.

**Flag logic.** Each quote is scored on deviation from the benchmark range and on its actual margin. Margin thresholds are computed per job type from historical percentiles (25th = red floor, median = yellow floor), with global fallbacks for job types with thin data.

**Feedback loop.** Every decision, including reason codes and manager approvals, is logged. `retrain_models.py` folds those outcomes back into the training set so the models keep up as the business changes.

The app also includes a decision-history view and a client-margin view that rolls up blended margin per customer to highlight at-risk accounts.

## Tech stack

Python, pandas, NumPy, scikit-learn, XGBoost, Streamlit, joblib, python-pptx. A ServiceTitan API integration (OAuth2 client-credentials flow) is stubbed out and disabled by default.

## Running it locally

```bash
pip install -r requirements.txt
python scripts/generate_sample_data.py   # creates synthetic data in data/
python train_models.py                    # trains both models into models/
streamlit run app/app.py
```

To regenerate the stakeholder slide deck: `pip install python-pptx` then `python generate_presentation.py`.

## Project structure

```
app/
  app.py              Streamlit UI: bid check, decision history, client margins
  flag_logic.py       Benchmark range, deviation, and green/yellow/red rules
  feedback.py         Logs each estimator decision for retraining
  servicetitan.py     API integration stub (disabled)
scripts/
  generate_sample_data.py   Synthetic data generator
train_models.py       Feature engineering + training for both models
retrain_models.py     Retrains using logged feedback
generate_presentation.py    Builds the stakeholder deck
docs/                 Plain-language walkthroughs of each module + design notes
```

## My role

<!-- Fill this in: what you personally built, e.g. "Built the Streamlit app and flag logic; co-developed the margin model." -->

Developed as a team project through the University of Chicago Booth consulting lab.
