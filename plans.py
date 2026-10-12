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


def plan_for_user(user):
    return get_plan(user.plan_tier)