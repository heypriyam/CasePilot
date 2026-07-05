"""
CasePilot - Gemini Structuring Module
Takes a raw case (from gmail_ingest.py) and extracts structured,
decision-support fields using Gemini Flash 2.5.

Includes retry-with-backoff to handle transient 503 "model overloaded"
errors from the Gemini API without crashing a full batch run.

Setup:
  pip install google-genai
  Set your API key via Colab secrets (userdata.get('GEMINI_API_KEY'))
  or paste directly - see usage at the bottom.
"""

import json
import time
from google import genai

EXTRACTION_PROMPT = """You are a customer support case classifier and decision-support assistant. Given the email below, extract:
- issue_category (string, one of: billing, technical, access, feature_request, complaint, other)
- sentiment (string: positive, neutral, negative, urgent_negative)
- urgency (integer 1-5, 5 = most urgent)
- key_entities (array of strings: product names, account IDs, error codes mentioned)
- summary (string, one sentence)
- root_cause (string, one sentence: likely underlying cause, not just the symptom)
- recommended_next_action (string, one sentence: concrete next step for the team)
- business_impact (string, one of: low, medium, high, critical)
- confidence (float 0-1: your confidence in this classification)

Respond ONLY with valid JSON matching this schema. No preamble, no markdown fences.

EMAIL:
Subject: {subject}
From: {sender}
Body: {body}
"""


def structure_case(client, case, max_retries=4, model="gemini-3.1-flash-lite"):
    """
    client: a genai.Client instance
    case: dict with at least subject, from, body, case_id, date
    model: defaults to flash-lite to avoid the stricter free-tier daily cap
           on gemini-2.5-flash (20 requests/day). Flash-lite generally has
           a separate, higher daily allowance.
    """
    prompt = EXTRACTION_PROMPT.format(
        subject=case["subject"], sender=case["from"], body=case["body"]
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"temperature": 0.2, "response_mime_type": "application/json"},
            )
            try:
                structured = json.loads(response.text)
            except json.JSONDecodeError:
                structured = {"error": "parse_failed", "raw": response.text}

            structured["case_id"] = case["case_id"]
            structured["from"] = case["from"]
            structured["subject"] = case["subject"]
            structured["date"] = case["date"]
            return structured

        except Exception as e:
            last_error = e
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 45
            elif "503" in str(e) or "UNAVAILABLE" in str(e):
                wait = 15 * (attempt + 1)  # 15s, 30s, 45s, 60s - give overload time to clear
            else:
                wait = 2 ** attempt
            print(f"  Attempt {attempt+1} failed ({e}), retrying in {wait}s...")
            time.sleep(wait)

    # All retries failed - return a placeholder so the whole batch doesn't crash
    return {
        "case_id": case["case_id"],
        "from": case["from"],
        "subject": case["subject"],
        "date": case["date"],
        "error": f"failed_after_{max_retries}_retries",
        "raw_error": str(last_error),
    }


def structure_all_cases(client, cases, log_every=10, delay_seconds=18, model="gemini-3.1-flash-lite", save_path="structured_cases_progress.json"):
    """
    Runs structure_case over a full list, with progress logging.
    Saves incrementally to save_path after every case, so you can safely
    interrupt (Runtime > Interrupt execution) at any point without losing
    what's already been processed - just reload the file afterward:
        import json
        structured_cases = json.load(open("structured_cases_progress.json"))
    """
    results = []
    for i, case in enumerate(cases):
        result = structure_case(client, case, model=model)
        results.append(result)

        with open(save_path, "w") as f:
            json.dump(results, f, indent=2)

        if (i + 1) % log_every == 0:
            print(f"Processed {i+1}/{len(cases)} (saved to {save_path})")
        if i < len(cases) - 1:
            time.sleep(delay_seconds)

    failed = [r for r in results if "error" in r]
    print(f"Done. {len(results) - len(failed)}/{len(results)} succeeded, {len(failed)} failed.")
    return results


if __name__ == "__main__":
    # Example usage in Colab:
    #
    # from google.colab import userdata
    # GEMINI_API_KEY = userdata.get('GEMINI_API_KEY')
    # client = genai.Client(api_key=GEMINI_API_KEY)
    #
    # import gemini_structure
    # structured_cases = gemini_structure.structure_all_cases(client, cases)
    pass