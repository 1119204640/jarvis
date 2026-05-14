from datetime import datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_time():
    return datetime.now(BEIJING_TZ)

def format_time(dt_obj):
    return dt_obj.strftime("%Y-%m-%d %H:%M:%S")