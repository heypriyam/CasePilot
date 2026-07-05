"""
Run this ONCE on your local laptop to log in via browser and generate token.json.
Upload the resulting token.json to Colab afterward — Colab itself never needs
to run this interactive step.

Usage:
  1. Make sure credentials.json (downloaded from Cloud Console) is in this folder.
  2. Run: python authorize.py
  3. A browser tab opens — log in with the Gmail account you want this token
     tied to (run it once for your PRIMARY account, and again for the
     casepilot.support/demo account — just rename the output token.json
     each time, see bottom of this file).
  4. token.json will appear in this folder — upload that file to Colab.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)

with open("token.json", "w") as token_file:
    token_file.write(creds.to_json())

print("Done. token.json created in this folder.")
print("Upload this file to your Colab session.")

# NOTE: Run this script TWICE total —
#   1st time: log in with your PRIMARY Gmail (for Sheets/Drive access)
#              -> after it finishes, rename token.json to token_primary.json
#   2nd time: log in with your casepilot.support/demo Gmail (for reading case emails)
#              -> after it finishes, rename token.json to token_support.json
# Upload BOTH renamed files to Colab.