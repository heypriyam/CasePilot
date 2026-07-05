"""
CasePilot - Scoring Layer
Reads the Gemini-structured cases CSV and computes an explainable
health_score (0-100) and escalation_risk (low/medium/high) for each case.

Uses only fields actually available from the structuring step:
  urgency, sentiment, business_impact, confidence
Plus one derived feature: repeat_complaint_count (same sender appearing
more than once in the dataset).
"""

import pandas as pd


import re


def compute_repeat_complaints(df):
    """
    Counts repeat complainants using the Account ID mentioned in the case
    (e.g. 'ACC-47'), extracted from key_entities or subject/summary text -
    NOT the Gmail 'from' header, since in this test setup all dummy emails
    were sent from one single test inbox to itself, making every 'from'
    value identical (which would wrongly flag every case as a 100x repeat).
    """
    def extract_account_id(row):
        text = " ".join([
            str(row.get("key_entities", "")),
            str(row.get("subject", "")),
            str(row.get("summary", "")),
        ])
        match = re.search(r"ACC-\d+", text)
        return match.group(0) if match else None

    account_ids = df.apply(extract_account_id, axis=1)
    counts = account_ids.value_counts()

    def get_count(acc_id):
        if acc_id is None:
            return 1  # no account ID found - treat as unique, no penalty
        return counts.get(acc_id, 1)

    return account_ids.apply(get_count)


def score_cases(df):
    df = df.copy()

    # Ensure numeric types (CSV round-trip can turn these into strings)
    df["urgency"] = pd.to_numeric(df["urgency"], errors="coerce").fillna(3)
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.8)

    df["repeat_complaint_count"] = compute_repeat_complaints(df)

    impact_penalty = {"critical": 8, "high": 4, "medium": 2, "low": 0}
    sentiment_penalty = {"urgent_negative": 15, "negative": 7, "neutral": 0, "positive": 0}

    def calc_row(row):
        score = 100
        score -= row["urgency"] * 6
        score -= sentiment_penalty.get(row.get("sentiment", "neutral"), 0)
        score -= 4 * max(row["repeat_complaint_count"] - 1, 0)
        score -= impact_penalty.get(row.get("business_impact", "low"), 0)
        if row["confidence"] < 0.6:
            score += 5
        return max(0, min(100, round(score, 1)))

    df["health_score"] = df.apply(calc_row, axis=1)

    # Quantile-based bucketing: guarantees a spread across risk levels
    # regardless of how skewed the raw scores are (e.g. if most dummy
    # cases are dramatic/urgent by design, fixed thresholds would wrongly
    # bucket everything as "high" - relative ranking fixes that).
    try:
        df["escalation_risk"] = pd.qcut(
            df["health_score"], q=3, labels=["high", "medium", "low"], duplicates="drop"
        )
    except ValueError:
        # fallback if scores have too many ties to split into 3 groups
        median = df["health_score"].median()
        df["escalation_risk"] = df["health_score"].apply(
            lambda s: "high" if s < median else "low"
        )

    return df


def load_score_and_save(
    in_path="casepilot_structured_cases.csv",
    out_path="casepilot_scored_cases.csv",
):
    df = pd.read_csv(in_path)
    scored = score_cases(df)
    scored = scored.sort_values("health_score")  # most at-risk cases first
    scored.to_csv(out_path, index=False)

    print(f"Scored {len(scored)} cases -> {out_path}")
    print(scored["escalation_risk"].value_counts())
    return scored


if __name__ == "__main__":
    # Usage in Colab:
    # import scoring
    # scored_df = scoring.load_score_and_save()
    # scored_df.head(10)
    pass
