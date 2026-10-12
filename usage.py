from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import UsageEvent


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def month_start():
    return _utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def files_used_this_month(user_id):
    return UsageEvent.query.filter(
        UsageEvent.user_id == user_id,
        UsageEvent.created_at >= month_start(),
    ).count()


def has_counted(user_id, stored_filename):
    return UsageEvent.query.filter_by(
        user_id=user_id, stored_filename=stored_filename
    ).first() is not None


def record_file_usage(user_id, stored_filename):
    """Count a file once. Returns True if newly counted, False if it was already counted."""
    if has_counted(user_id, stored_filename):
        return False
    db.session.add(UsageEvent(user_id=user_id, stored_filename=stored_filename))
    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False