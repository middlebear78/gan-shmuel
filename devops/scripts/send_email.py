#!/usr/bin/env python3
"""
Email notifier for CI/CD pipeline.

Sends email notifications on CI test and deploy events.
Called by the bash scripts alongside Slack notifications.

Usage:
    python3 send_email.py --event ci --status pass --details "All tests green"
    python3 send_email.py --event ci --status fail --details "Weight unit tests failed"
    python3 send_email.py --event deploy --status pass
    python3 send_email.py --event deploy --status fail --details "Frontend not healthy"

Required env vars:
    SMTP_HOST      — SMTP server hostname (e.g. smtp.gmail.com)
    SMTP_PORT      — SMTP server port (e.g. 587)
    SMTP_USER      — SMTP login username
    SMTP_PASSWORD  — SMTP login password
    EMAIL_FROM     — sender address
    EMAIL_TO       — comma-separated recipient addresses
"""

import os
import sys
import argparse
import smtplib
from email.mime.text import MIMEText

# ---- config from env vars ----

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO", "")


# ---- message templates ----

TEMPLATES = {
    ("ci", "pass"): {
        "subject": "CI Passed — waiting for PR approval",
        "body": (
            "Hi DevOps,\n\n"
            "CI pipeline passed successfully.\n"
            "All unit, integration, and e2e tests are green.\n\n"
            "{details}\n\n"
            "The PR is ready for review and approval.\n"
        ),
    },
    ("ci", "fail"): {
        "subject": "CI Failed",
        "body": (
            "Hi DevOps,\n\n"
            "CI pipeline failed.\n\n"
            "{details}\n\n"
            "Please check the logs and fix the issue.\n"
        ),
    },
    ("deploy", "pass"): {
        "subject": "Deployment Successful — smoke tests passed",
        "body": (
            "Hi DevOps,\n\n"
            "Production deployment completed successfully.\n"
            "Smoke tests passed — weight /health, billing /health,\n"
            "and frontend are all responding.\n\n"
            "{details}\n"
        ),
    },
    ("deploy", "fail"): {
        "subject": "Deployment Failed",
        "body": (
            "Hi DevOps,\n\n"
            "Production deployment failed.\n\n"
            "{details}\n\n"
            "Containers have been torn down. Please investigate.\n"
        ),
    },
}


def send_email(event, status, details=""):
    """Build and send the notification email."""

    # validate env vars are set
    missing = []
    for var in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"):
        if not os.getenv(var):
            missing.append(var)
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # look up the template for this event+status combo
    template = TEMPLATES.get((event, status))
    if not template:
        print(f"ERROR: Unknown event/status combo: {event}/{status}", file=sys.stderr)
        sys.exit(1)

    # build the email
    subject = template["subject"]
    body = template["body"].format(details=details if details else "No additional details.")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    # parse recipient list (comma-separated)
    recipients = [addr.strip() for addr in EMAIL_TO.split(",") if addr.strip()]

    # send via SMTP with TLS
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send CI/CD email notification")
    parser.add_argument("--event", required=True, choices=["ci", "deploy"],
                        help="Event type: ci or deploy")
    parser.add_argument("--status", required=True, choices=["pass", "fail"],
                        help="Event status: pass or fail")
    parser.add_argument("--details", default="",
                        help="Optional details to include in the email body")
    args = parser.parse_args()

    send_email(args.event, args.status, args.details)
