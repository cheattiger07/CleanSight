from datetime import datetime,timezone
PLANS = {
    "free": {
        "name": "Free",
        "price_inr": 0,
        "files_per_month": 3,
        "max_file_mb": 5,
        "excel_export": False,
        "pdf_export": False,
        "cleaning_log_export": False,
    },
    "student": {
        "name": "Student",
        "price_inr": 199,
        "files_per_month": 30,
        "max_file_mb": 16,
        "excel_export": True,
        "pdf_export": True,
        "cleaning_log_export": True,
    },
    "pro": {                      # defined now, hidden until the AI features exist
        "name": "Pro",
        "price_inr": 999,
        "files_per_month": 200,
        "max_file_mb": 16,
        "excel_export": True,
        "pdf_export": True,
        "cleaning_log_export": True,
    },
}


def get_plan(tier):
    """Return the plan dict for a tier name. Unknown tiers fall back to free."""
    return PLANS.get(tier, PLANS["free"])


def effective_tier(user):
    """A cancelled plan stays active until the paid period ends, then drops to free."""
    if user.plan_tier != "free" and user.cancel_requested and user.plan_renews_at:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if user.plan_renews_at < now:
            return "free"
    return user.plan_tier

def plan_for_user(user):
    return get_plan(effective_tier(user))