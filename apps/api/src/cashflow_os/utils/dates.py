from calendar import monthrange
from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def today_ist() -> date:
    return datetime.now(IST).date()



def daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def clamp_day(year: int, month: int, day: int) -> date:
    last_day = monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def month_sequence(start: date, months: int) -> List[Tuple[int, int]]:
    sequence = []
    year = start.year
    month = start.month
    for _ in range(months):
        sequence.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return sequence


def seven_day_windows(start: date, horizon_days: int) -> List[Tuple[int, date, date]]:
    windows = []
    cursor = start
    index = 1
    remaining = horizon_days
    while remaining > 0:
        bucket_days = min(7, remaining)
        bucket_end = cursor + timedelta(days=bucket_days - 1)
        windows.append((index, cursor, bucket_end))
        cursor = bucket_end + timedelta(days=1)
        remaining -= bucket_days
        index += 1
    return windows


def parse_date_value(value: object) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace(".", "-").replace("/", "-")
    for parser in (
        lambda raw: datetime.fromisoformat(raw).date(),
        lambda raw: datetime.strptime(raw, "%d-%m-%Y").date(),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d").date(),
        lambda raw: datetime.strptime(raw, "%d-%b-%Y").date(),
        lambda raw: datetime.strptime(raw, "%d-%B-%Y").date(),
    ):
        try:
            return parser(normalized)
        except ValueError:
            continue
    return None
