"""
CasePilot - Export Structured Results
Loads the incrementally-saved progress file, separates successful cases
from failed ones, and exports a clean CSV ready for scoring/Sheets upload.
"""

import json
import pandas as pd


def load_and_split(progress_path="structured_cases_progress.json"):
    with open(progress_path, "r") as f:
        all_results = json.load(f)

    successes = [r for r in all_results if "error" not in r]
    failures = [r for r in all_results if "error" in r]

    print(f"Total: {len(all_results)} | Successful: {len(successes)} | Failed: {len(failures)}")
    return successes, failures


def export_successes_to_csv(successes, out_path="casepilot_structured_cases.csv"):
    if not successes:
        print("No successful cases to export.")
        return None

    df = pd.DataFrame(successes)

    # Ensure consistent column order if present
    preferred_cols = [
        "case_id", "subject", "from", "date", "issue_category", "sentiment",
        "urgency", "business_impact", "confidence", "root_cause",
        "recommended_next_action", "summary", "key_entities",
    ]
    cols = [c for c in preferred_cols if c in df.columns] + \
           [c for c in df.columns if c not in preferred_cols]
    df = df[cols]

    df.to_csv(out_path, index=False)
    print(f"Exported {len(df)} cases to {out_path}")
    return df


if __name__ == "__main__":
    # Usage in Colab:
    # import export_results
    # successes, failures = export_results.load_and_split()
    # df = export_results.export_successes_to_csv(successes)
    # df.head()
    pass
