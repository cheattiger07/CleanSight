import os
import requests
import logging

RAZORPAY_API = "https://api.razorpay.com/v1"


class BillingError(Exception):
    pass


def _auth():
    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise BillingError("Payments are not configured.")
    return (key_id, key_secret)


def create_subscription(user, plan_env="RAZORPAY_PLAN_STUDENT"):
    """Create a Razorpay subscription and return (subscription_id, checkout_url)."""
    plan_id = os.environ.get(plan_env)
    if not plan_id:
        raise BillingError("Plan is not configured.")

    payload = {
        "plan_id": plan_id,
        "total_count": 60,          # up to 60 monthly charges; user can cancel any time
        "customer_notify": 1,
        "notes": {"user_id": str(user.id), "email": user.email},
    }
    try:
        resp = requests.post(
            f"{RAZORPAY_API}/subscriptions",
            json=payload,
            auth=_auth(),
            timeout=15,
        )
    except requests.RequestException:
        raise BillingError("Could not reach the payment provider. Try again.")

    if resp.status_code != 200:
        
        logging.getLogger(__name__).error(
            "Razorpay subscription error %s: %s", resp.status_code, resp.text[:500]
        )
        raise BillingError("The payment provider rejected the request.")

    data = resp.json()
    return data["id"], data["short_url"]