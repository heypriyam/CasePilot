"""
CasePilot - Gmail Ingestion Module
Connects to a Gmail account via OAuth and pulls emails as raw "case" data
for the pipeline (parsing/structuring happens downstream with Gemini).

Setup before running:
  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client

Place your downloaded OAuth client file as 'credentials.json' in this folder.
First run will open a browser to authorize; a 'token.json' is cached after that.
"""

import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Read-only scope - safest for a demo, avoids write/send permissions
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    """Handles OAuth flow and returns an authenticated Gmail API service object."""
    creds = None

    # token.json stores the user's access/refresh tokens after first login
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If no valid creds, run the OAuth flow (opens browser once)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_case_emails(service, query="", max_results=50):
    """
    Fetch emails matching a Gmail search query and return structured raw data.
    query examples:
      'label:support'                -> only emails in a "support" label
      'subject:(case OR ticket)'     -> subject line filtering
      'after:2026/06/01'             -> date filtering
    """
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    messages = results.get("messages", [])

    cases = []
    for msg_meta in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_meta["id"], format="full"
        ).execute()

        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        body_text = extract_body(msg["payload"])

        cases.append({
            "case_id": msg["id"],
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body_text,
        })

    return cases


def extract_body(payload):
    """Pulls plain-text body out of a Gmail message payload (handles nested parts)."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                data = part["body"]["data"]
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            elif "parts" in part:
                nested = extract_body(part)
                if nested:
                    return nested
    elif "body" in payload and "data" in payload["body"]:
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""


if __name__ == "__main__":
    service = get_gmail_service()
    # Adjust query to match however your "case" emails are labeled/tagged
    cases = fetch_case_emails(service, query="label:support", max_results=50)

    print(f"Fetched {len(cases)} case emails")
    for c in cases[:3]:
        print(c["subject"], "-", c["snippet"][:80])