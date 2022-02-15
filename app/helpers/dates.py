import datetime


def get_mongo_utc_date():
    now = datetime.datetime.now(datetime.timezone.utc)
    # MongoDB stores datetime with a millisecond precision.
    microseconds = round(now.microsecond, -3)
    if microseconds == 1000000:
        return now.replace(microsecond=0) + datetime.timedelta(seconds=1)
    return now.replace(microsecond=microseconds)
