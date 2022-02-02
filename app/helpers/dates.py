import datetime


def get_mongo_utc_date():
    now = datetime.datetime.now(datetime.timezone.utc)
    # MongoDB stores datetimes with a millisecond precision.
    microseconds = round(now.microsecond, -3)
    return now.replace(microsecond=microseconds)
