import datetime
import re

def parse_isoformat(s):
    """
    parses a date string in isoformat and returns a datetime object
    
    >>> ds = '2011-08-04T22:25:58.895542'
    >>> parse_isoformat(ds) # doctest: +ELLIPSIS
    datetime.datetime(...)

    >>> ds = '2011-08-04'
    >>> parse_isoformat(ds) # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: Invalid ISO Format Date String
    
    """

    p = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{1,2}):(\d{1,2}):(\d{1,2})\.(\d+)$")

    m = p.search(s)

    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        hour = int(m.group(4))
        minutes = int(m.group(5))
        seconds = int(m.group(6))
        microseconds = int(m.group(7))

        return datetime.datetime(year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minutes,
            second=seconds,
            microsecond=microseconds)

    else:
        raise ValueError, "Invalid ISO Format Date String"
