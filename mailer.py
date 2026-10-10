import os
import requests

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to_email, subject, html_content):
    """Send one email through Brevo. Returns True on success, False otherwise."""
    api_key = os.environ.get("BREVO_API_KEY")
    sender_email = os.environ.get("MAIL_SENDER_EMAIL")
    sender_name = os.environ.get("MAIL_SENDER_NAME", "CleanSight")

    if not api_key or not sender_email:
        print("Mailer: BREVO_API_KEY or MAIL_SENDER_EMAIL is not set")
        return False

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }
    headers = {
        "api-key": api_key,
        "accept": "application/json",
        "content-type": "application/json",
    }

    try:
        resp = requests.post(BREVO_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            return True
        print(f"Mailer: Brevo returned {resp.status_code}: {resp.text}")
        return False
    except requests.RequestException as e:
        print(f"Mailer: request failed: {e}")
        return False

def send_verification_email(to_email, link):
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;">
      <h2>Welcome to CleanSight</h2>
      <p>Please confirm your email address to start cleaning data.</p>
      <p><a href="{link}" style="display:inline-block;padding:12px 20px;background:#1e3a8a;color:#fff;text-decoration:none;border-radius:6px;">Verify my email</a></p>
      <p style="color:#666;font-size:13px;">This link expires in 24 hours. If you didn't create an account, you can ignore this email.</p>
    </div>
    """
    return send_email(to_email, "Verify your CleanSight email", html)