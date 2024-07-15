from datetime import datetime
import pytz


def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    formatted_hours = hours if hours > 9 else f"0{hours}"
    formatted_minutes = minutes if minutes > 9 else f"0{minutes}"
    formatted_seconds = seconds if seconds > 9 else f"0{seconds}"
    return f"{formatted_hours}:{formatted_minutes}:{formatted_seconds}"


def check_if_too_long(start_time, range, timezone='Europe/Warsaw'):
    break_start = datetime.fromisoformat(start_time[:-6])
    break_start = pytz.timezone(timezone).localize(break_start)
    now = datetime.now(pytz.timezone(timezone))
    time_diff = now - break_start
    break_range_details = range['range_details']
    allowed_break_time = break_range_details['time_limit_in_minutes'] * 60
    more_than_allowed = time_diff.total_seconds() > allowed_break_time
    return more_than_allowed


def calculate_time_difference(start, end=None, timezone='Europe/Warsaw'):
    start_datetime = datetime.fromisoformat(start[:-6])
    start_datetime = pytz.timezone(timezone).localize(start_datetime)
    if end:
        end_datetime = datetime.fromisoformat(end[:-6])
        end_datetime = pytz.timezone(timezone).localize(end_datetime)
    else:
        end_datetime = datetime.now(pytz.timezone(timezone))
    time_difference = end_datetime - start_datetime
    duration_in_seconds = time_difference.total_seconds()
    formatted_start_datetime = str(start_datetime.time())
    formatted_end_datetime = str(end_datetime.time())
    duration_str = format_time(duration_in_seconds)
    calculated_dict = {
        'start': formatted_start_datetime[:8],
        'end': formatted_end_datetime[:8],
        'duration': duration_in_seconds,
        'duration_str': duration_str
    }

    return calculated_dict


def assume_gender(first_name):
    gender = 'F' if first_name[-1].lower() == 'a' else 'M'
    return gender


def check_kwarg_key(kwargs, value):
    if value in kwargs.keys():
        return True
    else:
        return False


def extract_agent_data(agents):
    agents_table = []
    for agent in agents:
        ad = agent.split(";")
        agents_table.append({
            'id': ad[0],
            'full_name': ad[1],
            'gender': ad[2]
        })
    return agents_table
