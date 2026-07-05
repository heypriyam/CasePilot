"""
CasePilot - Dummy Case Email Generator
Sends 100+ synthetic customer-case emails to YOUR OWN Gmail inbox
so you have realistic test data for the ingestion pipeline.

Setup:
  Reuses gmail_ingest.py's OAuth flow, but needs the SEND scope too.
  If your token.json was generated with only readonly (+sheets/drive),
  delete it and re-run the auth flow once with ALL scopes together:
    https://www.googleapis.com/auth/gmail.readonly
    https://www.googleapis.com/auth/gmail.send
    https://www.googleapis.com/auth/spreadsheets
    https://www.googleapis.com/auth/drive
"""

import base64
import random
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# --- Synthetic data building blocks ---

CATEGORIES = {
    "billing": {
        "subjects": [
            "Duplicate charge on my last invoice",
            "Billing amount doesn't match my plan",
            "Refund not received after cancellation",
            "Unexpected charge on my card",
        ],
        "bodies": [
            "I was charged twice for my subscription this month. Account ID: ACC-{n}. Please refund the extra charge as soon as possible.",
            "My invoice shows a different amount than what we agreed on the {plan} plan. Can someone from billing check this? Account ID: ACC-{n}.",
            "I cancelled my subscription two weeks ago and still haven't received my refund. This is affecting my business. Account ID: ACC-{n}.",
        ],
    },
    "technical": {
        "subjects": [
            "API returning 500 errors intermittently",
            "Dashboard not loading after latest update",
            "Login failing with error code AUTH-{n}",
            "Data sync broken between environments",
        ],
        "bodies": [
            "We're seeing intermittent 500 errors from the API since this morning. Error code: ERR-{n}. This is blocking our production workflow.",
            "The dashboard has been stuck on a loading screen since the last update. Tried clearing cache, no luck. Account ID: ACC-{n}.",
            "Getting AUTH-{n} error when trying to log in. Happens on both browser and mobile app.",
        ],
    },
    "access": {
        "subjects": [
            "Unable to access admin panel",
            "New team member needs account access",
            "Locked out of my account",
        ],
        "bodies": [
            "I can no longer access the admin panel, it just redirects me to the login page in a loop. Account ID: ACC-{n}.",
            "Can you please grant access to our new team member? Their email is teammate{n}@example.com.",
            "I've been locked out of my account after multiple failed login attempts. Need urgent help, Account ID: ACC-{n}.",
        ],
    },
    "feature_request": {
        "subjects": [
            "Request: export data to CSV",
            "Would love a dark mode option",
            "Feature suggestion: bulk actions",
        ],
        "bodies": [
            "It would be really helpful if we could export our data directly to CSV from the dashboard. Any plans for this?",
            "Just a small suggestion — a dark mode option would improve the experience for our night-shift team.",
            "Could you add bulk actions for managing multiple records at once? Would save us a lot of time.",
        ],
    },
    "complaint": {
        "subjects": [
            "Very disappointed with recent service quality",
            "This is the third time I'm reporting the same issue",
            "Extremely frustrated with lack of response",
        ],
        "bodies": [
            "This is the third time I'm reaching out about the same unresolved issue. I'm extremely frustrated and considering switching providers. Account ID: ACC-{n}.",
            "I've been waiting for a response for over a week now. This level of service is unacceptable for a paying customer. Account ID: ACC-{n}.",
            "Very disappointed with the recent changes. Things that used to work fine are now broken. Account ID: ACC-{n}.",
        ],
    },
}

SENDER_NAMES = [
    "Alex Johnson", "Priya Sharma", "Michael Chen", "Sarah Williams",
    "David Kim", "Emma Brown", "Rahul Verma", "Laura Garcia",
    "James Wilson", "Ananya Rao",
]

PLANS = ["Pro", "Enterprise", "Starter", "Team"]


def generate_dummy_email(n):
    category = random.choice(list(CATEGORIES.keys()))
    data = CATEGORIES[category]
    subject = random.choice(data["subjects"])
    body_template = random.choice(data["bodies"])
    body = body_template.format(n=n, plan=random.choice(PLANS))
    sender_name = random.choice(SENDER_NAMES)

    return {
        "subject": f"[Case #{n}] {subject}",
        "body": f"Hi Support Team,\n\n{body}\n\nThanks,\n{sender_name}",
        "category": category,  # kept for your own reference/validation, not sent
    }


def get_gmail_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("gmail", "v1", credentials=creds)


def send_email(service, to_email, subject, body):
    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def send_dummy_batch(to_email, count=100):
    service = get_gmail_service()
    sent = 0
    for i in range(1, count + 1):
        email_data = generate_dummy_email(i)
        try:
            send_email(service, to_email, email_data["subject"], email_data["body"])
            sent += 1
            if sent % 10 == 0:
                print(f"Sent {sent}/{count}...")
        except Exception as e:
            print(f"Failed to send case #{i}: {e}")

    print(f"Done. Sent {sent}/{count} dummy case emails to {to_email}.")
    print("Tip: create a Gmail label (e.g. 'support') and filter these by subject "
          "containing '[Case #' to route them automatically, matching your ingestion query.")


if __name__ == "__main__":
    YOUR_EMAIL = "your_email@gmail.com"  # <-- replace with your own Gmail address
    send_dummy_batch(YOUR_EMAIL, count=100)
