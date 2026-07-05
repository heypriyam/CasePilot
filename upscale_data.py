"""
CasePilot - Dataset Upscaling
Takes the 100 real Gemini-structured & scored cases and synthetically
expands them to ~100,000 rows by resampling with controlled variation.

This is NOT meant to fabricate fake "real" cases - it's explicitly a
volume-scaling step to demonstrate NVIDIA acceleration at realistic
enterprise data scale, which the hackathon rubric asks for ("evidence
that acceleration improves the experience... larger data scale").
The dashboard/demo should be transparent that base cases are real,
volume is synthetically scaled for the benchmark.
"""

import pandas as pd
import numpy as np


def upscale_dataset(
    in_path="casepilot_scored_cases.csv",
    out_path="casepilot_scaled_100k.csv",
    target_rows=100_000,
    seed=42,
):
    rng = np.random.default_rng(seed)
    base_df = pd.read_csv(in_path)
    n_base = len(base_df)
    repeats = int(np.ceil(target_rows / n_base))

    scaled = pd.concat([base_df] * repeats, ignore_index=True).iloc[:target_rows].copy()

    # Give every row a unique case_id (avoid literal duplicate IDs)
    scaled["case_id"] = [f"{row_id}-{i}" for i, row_id in enumerate(scaled["case_id"])]

    # Add small random jitter to numeric fields so rows aren't perfect
    # clones - keeps the aggregate distribution realistic for benchmarking
    if "urgency" in scaled.columns:
        jitter = rng.integers(-1, 2, size=len(scaled))  # -1, 0, or +1
        scaled["urgency"] = (pd.to_numeric(scaled["urgency"], errors="coerce").fillna(3) + jitter).clip(1, 5)

    if "health_score" in scaled.columns:
        noise = rng.normal(0, 3, size=len(scaled))  # small gaussian noise
        scaled["health_score"] = (pd.to_numeric(scaled["health_score"], errors="coerce").fillna(60) + noise).clip(0, 100).round(1)

    # Re-derive escalation_risk from the jittered health_score using the
    # same quantile approach as the original scoring step
    scaled["escalation_risk"] = pd.qcut(
        scaled["health_score"], q=3, labels=["high", "medium", "low"], duplicates="drop"
    )

    scaled.to_csv(out_path, index=False)
    print(f"Upscaled {n_base} base rows -> {len(scaled)} rows -> {out_path}")
    print(scaled["escalation_risk"].value_counts())
    return scaled


if __name__ == "__main__":
    # Usage in Colab:
    # import upscale_data
    # scaled_df = upscale_data.upscale_dataset()
    pass
