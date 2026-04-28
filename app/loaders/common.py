from datetime import datetime


def parse_int(value):
    if value in (None, ""):
        return None
    return int(float(value))


def parse_float(value):
    if value in (None, ""):
        return None
    return float(value)


def parse_date(value):
    if not value:
        return None
    value = str(value).strip()
    if value in {"-", "nan", "None"}:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
