from datetime import timedelta, datetime

KST_DELTA = timedelta(hours=9)


def to_kst(d: datetime):
    return d + KST_DELTA
