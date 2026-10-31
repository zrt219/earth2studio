# Preserved Historical Research Artifacts

**Directory Classification:** `TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC`  
**Audited Commit:** `364dba83fa61856d23a3882be46c899ebcfed2a1`  
**Reference Document:** `docs/origin_datum/EO_EARTH2_LEAKAGE_AUDIT.md`  

---

## Warning & Scientific Purpose

The modules in this directory are preserved strictly for historical audit, research traceability, defect reproduction, and RED $\to$ GREEN testing.

**CRITICAL METEOROLOGICAL INTEGRITY NOTICE:**
- The historical study runner (`study_runner_historical.py`) contains direct **target leakage**. It constructs a synthetic 24-hour prediction using future operational analysis truth:
  $$\text{forecast}_{t2m} = \text{pers}_{t2m} + 0.72 \cdot (\text{truth}_{t2m} - \text{pers}_{t2m}) + \mathcal{N}(0, 0.45^2)$$
- The historical manuscript (`scientific_study_v2.tex`) reported an artificial RMSE of $\approx 0.747\text{ K}$ and $+64.9\%$ skill over persistence. These numbers are purely mathematical artifacts of the leakage formula, not empirical evidence of neural network weather forecasting.
- The regional storm tracking in the historical runner evaluated future verifying Mean Sea Level Pressure (MSLP) operational analysis fields directly, rather than model predictions.

**STRICT CONSTRAINT:**
These modules must **NEVER** be imported into production benchmarking pipelines or presented as genuine weather forecasts. Genuine forecasting workflows reside in the decoupled pipeline architecture (`od_experiments/scientific_study/pipeline/`).
