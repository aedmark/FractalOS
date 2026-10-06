"""
cal - Display a calendar
"""
import calendar
import datetime

def metadata():
    return {
        "name": "cal",
        "version": "1.0.0",
        "description": "Displays monthly and yearly calendar with date highlighting",
        "author": "FractalOS Community",
        "license": "MIT",
        "wheels": [],
        "dependencies": []
    }

def define_flags():
    return {
        "flags": [
            {"name": "help", "short": "h", "long": "help", "takes_value": False},
            {"name": "three", "short": "3", "long": "three", "takes_value": False},
            {"name": "year", "short": "y", "long": "year", "takes_value": False},
            {"name": "monday", "short": "m", "long": "monday", "takes_value": False},
            {"name": "julian", "short": "j", "long": "julian", "takes_value": False},
        ],
        "aliases": {
            "h": "help", "3": "three", "y": "year", "m": "monday", "j": "julian"
        }
    }

def _format_month_grid(year, month, first_weekday, highlight_day=None):
    cal = calendar.Calendar(firstweekday=first_weekday)
    month_days = cal.monthdayscalendar(year, month)
    
    month_name = calendar.month_name[month]
    header = f"{month_name} {year}".center(20)
    
    if first_weekday == calendar.MONDAY:
        day_headers = "Mo Tu We Th Fr Sa Su"
    else:
        day_headers = "Su Mo Tu We Th Fr Sa"
        
    lines = [header, day_headers]
    for week in month_days:
        week_parts = []
        for day in week:
            if day == 0:
                week_parts.append("  ")
            else:
                s = str(day).rjust(2)
                if highlight_day and day == highlight_day:
                    s = f"\x1b[7m{s}\x1b[0m"
                week_parts.append(s)
        lines.append(" ".join(week_parts))
    return lines

async def run(args, flags, user_context, **kwargs):
    if flags.get("help"):
        return {"success": True, "output": help(args, flags, user_context)}

    now = datetime.datetime.now()
    cur_year = now.year
    cur_month = now.month
    cur_day = now.day

    first_weekday = calendar.MONDAY if flags.get("monday") else calendar.SUNDAY

    target_month = cur_month
    target_year = cur_year

    if len(args) == 1:
        val = int(args[0])
        if 1 <= val <= 12:
            target_month = val
        else:
            target_year = val
            flags["year"] = True
    elif len(args) >= 2:
        target_month = int(args[0])
        target_year = int(args[1])

    # Three-month view (-3)
    if flags.get("three"):
        prev_month = target_month - 1 if target_month > 1 else 12
        prev_year = target_year if target_month > 1 else target_year - 1
        next_month = target_month + 1 if target_month < 12 else 1
        next_year = target_year if target_month < 12 else target_year + 1

        m1 = _format_month_grid(prev_year, prev_month, first_weekday, cur_day if (prev_year == cur_year and prev_month == cur_month) else None)
        m2 = _format_month_grid(target_year, target_month, first_weekday, cur_day if (target_year == cur_year and target_month == cur_month) else None)
        m3 = _format_month_grid(next_year, next_month, first_weekday, cur_day if (next_year == cur_year and next_month == cur_month) else None)

        # Pad all to same height (typically 8 lines)
        max_lines = max(len(m1), len(m2), len(m3))
        for m in (m1, m2, m3):
            while len(m) < max_lines:
                m.append(" " * 20)

        merged = []
        for i in range(max_lines):
            merged.append(f"{m1[i].ljust(20)}  {m2[i].ljust(20)}  {m3[i].ljust(20)}")
        return "\n".join(merged)

    # Full year view (-y)
    if flags.get("year"):
        output_lines = [f"{str(target_year).center(66)}\n"]
        for row in range(4): # 4 quarters of 3 months
            m_indices = [row * 3 + 1, row * 3 + 2, row * 3 + 3]
            grids = [
                _format_month_grid(target_year, m, first_weekday, cur_day if (target_year == cur_year and m == cur_month) else None)
                for m in m_indices
            ]
            max_lines = max(len(g) for g in grids)
            for g in grids:
                while len(g) < max_lines:
                    g.append(" " * 20)
            for i in range(max_lines):
                output_lines.append(f"{grids[0][i].ljust(20)}  {grids[1][i].ljust(20)}  {grids[2][i].ljust(20)}")
            output_lines.append("")
        return "\n".join(output_lines)

    # Single month view
    highlight = cur_day if (target_year == cur_year and target_month == cur_month) else None
    lines = _format_month_grid(target_year, target_month, first_weekday, highlight)
    return "\n".join(lines)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    cal - Display a calendar

SYNOPSIS
    cal [-3] [-y] [-m] [month [year]]
    cal [year]

DESCRIPTION
    Displays a calendar for the current or specified month and year,
    highlighting the current day.

OPTIONS
    -3
        Display previous, current and next month side-by-side.
    -y, --year
        Display a calendar for the entire year.
    -m, --monday
        Display Monday as the first day of the week (default: Sunday).

EXAMPLES
    cal
    cal -3
    cal 12 2026
    cal 2026
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: cal [-3] [-y] [-m] [month [year]]"
