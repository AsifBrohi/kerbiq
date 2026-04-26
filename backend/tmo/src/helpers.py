def categorise_restriction(order_type: str, restriction: str) -> str:
    """this function takes the order_type and restriction columns and categorises the restriction into a predefined set of categories
    the categorisation is based on the presence of certain keywords in the order_type and restriction columns"""

    if order_type is None:
        return "unknown"
    
    ot = order_type.lower()
    
    if "clearway" in ot:
        return "clearway"
    if "loading" in ot:
        return "loading_only"
    if "disabled" in ot:
        return "disabled_bay"
    if "ambulance" in ot:
        return "disabled_bay"        # emergency vehicle bay
    if "permit" in ot:
        return "permit_only"
    if "resident" in ot:
        return "permit_only"
    if "shared use" in ot:
        return "shared_use"          # permit OR pay depending on time
    if "pay" in ot or "display" in ot:
        return "pay_display"
    if "electric" in ot or "ev" in ot or "charging" in ot:
        return "ev_charging"
    if "no waiting" in ot:
        return "no_waiting"
    if "red route" in ot or "tfl" in ot:
        return "red_route"
    if "cycle hire" in ot:
        return "cycle_hire"
    if "event" in ot or "stadium" in ot or "match" in ot:
        return "event_day"           # dynamic restriction — flag separately
    if "off-street car park" in ot:
        return "off_street_car_park"
    if "motorcycle parking" in ot:
        return "motorcycle_parking"
    if "school keep clear" in ot:
        return "school_keep_clear"
    
    if "streetcar parking" in ot:
        return "streetcar_parking"
    if "limited waiting" in ot:
        return "limited_waiting"
    
    return "unknown"



import re
from datetime import time

def parse_time(time_str: str) -> str | None:
    """Convert time string like '9.30am', '6pm', '11am' to HH:MM string"""
    if not time_str:
        return None
    
    time_str = time_str.strip().lower()
    
    match = re.match(r"(\d{1,2})(?:\.(\d{2}))?([ap]m)", time_str)
    if not match:
        return None
    
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    period = match.group(3)
    
    if period == "pm" and hour != 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0
    
    # return as HH:MM string not time object
    return f"{hour:02d}:{minute:02d}"


def parse_days(days_str: str) -> list[str]:
    """Convert day range string like 'Mon-Fri', 'Mon-Sat', 'Sat-Sun' to list of days"""
    all_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    if not days_str:
        return []
    
    days_str = days_str.strip()
    result = set()
    
    # handle ranges like Mon-Fri, Mon-Sat, Sat-Sun
    range_match = re.findall(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)-(Mon|Tue|Wed|Thu|Fri|Sat|Sun)", days_str)
    for start, end in range_match:
        start_idx = all_days.index(start)
        end_idx = all_days.index(end)
        for i in range(start_idx, end_idx + 1):
            result.add(all_days[i])
    
    # handle individual days
    individual = re.findall(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", days_str)
    for day in individual:
        result.add(day)
    
    # return in week order
    return [d for d in all_days if d in result]


def parse_restriction(restriction: str) -> dict:
    """
    Parse restriction text into structured time fields.
    
    Handles patterns:
    - No waiting at any time
    - No waiting Mon-Fri 9.30am-6pm
    - No waiting Mon-Fri 9.30am-6pm and Sat 9.30am-12.30pm
    - No waiting Mon-Fri 9.30am-12.30pm and 4.30pm-6.30pm and Sat 9.30am-12.30pm
    - No waiting 7am-11pm on event days
    - Resident Permit Holders Mon-Fri 9.30am-6pm Except Christmas Day...
    """
    result = {
        "is_any_time":    False,
        "has_exceptions": False,
        "is_event_day":   False,
        "overnight":      False,
        "needs_review":   False,
        "days_of_week":   None,
        "start_time":     None,
        "end_time":       None,
        "sat_start_time": None,
        "sat_end_time":   None,
        "time_window_2_start": None,  # for split windows like 9-12 and 4-6
        "time_window_2_end":   None,
    }
    
    if not restriction:
        result["needs_review"] = True
        return result
    
    r = restriction.strip()
    
    # --- at any time ---
    if re.search(r"at any time", r, re.IGNORECASE):
        result["is_any_time"] = True
        return result
    
    # --- exceptions ---
    if re.search(r"bank holiday|christmas day|good friday", r, re.IGNORECASE):
        result["has_exceptions"] = True
    
    # --- event days ---
    if re.search(r"event day|match day|brentford fc|stadium", r, re.IGNORECASE):
        result["is_event_day"] = True
        # still try to parse times for event day restrictions
        time_match = re.search(r"(\d{1,2}(?:\.\d{2})?[ap]m)-(\d{1,2}(?:\.\d{2})?[ap]m)", r)
        if time_match:
            result["start_time"] = parse_time(time_match.group(1))
            result["end_time"] = parse_time(time_match.group(2))
        return result
    
    # --- parse day ranges ---
    # look for day pattern before the times
    day_match = re.search(
        r"((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:-(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun))?)",
        r
    )
    if day_match:
        result["days_of_week"] = parse_days(day_match.group(1))
    
    # --- find all time windows ---
    # pattern: time-time (e.g. 9.30am-6pm)
    time_pattern = r"(\d{1,2}(?:\.\d{2})?[ap]m)-(\d{1,2}(?:\.\d{2})?[ap]m)"
    
    # split on "and Sat" to handle Saturday separately
    sat_split = re.split(r"\band\s+Sat\b", r, flags=re.IGNORECASE)
    
    main_part = sat_split[0]
    sat_part = sat_split[1] if len(sat_split) > 1 else None
    
    # find time windows in main part
    main_windows = re.findall(time_pattern, main_part)
    
    if len(main_windows) >= 1:
        result["start_time"] = parse_time(main_windows[0][0])
        result["end_time"] = parse_time(main_windows[0][1])
    
    if len(main_windows) >= 2:
        # split window like 9.30am-12.30pm and 4.30pm-6.30pm
        result["time_window_2_start"] = parse_time(main_windows[1][0])
        result["time_window_2_end"] = parse_time(main_windows[1][1])
    
    # split on "and Sat" — use capturing group to preserve Sat
    sat_split = re.split(r"\band\s+(Sat(?:-Sun)?)\b", r, flags=re.IGNORECASE)

    main_part = sat_split[0]

    if len(sat_split) > 2:
        sat_part = sat_split[1] + sat_split[2]  # "Sat-Sun -2pm-4pm"
    elif len(sat_split) > 1:
        sat_part = "Sat " + sat_split[1]
    else:
        sat_part = None

    # find time windows in main part
    main_windows = re.findall(time_pattern, main_part)

    if len(main_windows) >= 1:
        result["start_time"] = parse_time(main_windows[0][0])
        result["end_time"] = parse_time(main_windows[0][1])

    if len(main_windows) >= 2:
        result["time_window_2_start"] = parse_time(main_windows[1][0])
        result["time_window_2_end"] = parse_time(main_windows[1][1])

    if sat_part:
        sat_windows = re.findall(time_pattern, sat_part)
        if sat_windows:
            result["sat_start_time"] = parse_time(sat_windows[0][0])
            result["sat_end_time"] = parse_time(sat_windows[0][1])

        all_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        existing = set(result["days_of_week"] or [])
        existing.add("Sat")
        if re.search(r"\bSun\b", sat_part, re.IGNORECASE):
            existing.add("Sun")
        result["days_of_week"] = [d for d in all_days if d in existing]
        
    # --- overnight check ---
    if result["start_time"] and result["end_time"]:
        start_h, start_m = map(int, result["start_time"].split(":"))
        end_h, end_m = map(int, result["end_time"].split(":"))
        if (end_h * 60 + end_m) < (start_h * 60 + start_m):
            result["overnight"] = True
    
    # --- needs review if no times parsed and not AAT or event ---
    if (not result["is_any_time"] and 
        not result["is_event_day"] and 
        result["start_time"] is None and
        not re.search(r"cycle hire|disabled|ambulance", r, re.IGNORECASE)):
        result["needs_review"] = True
    
    return result