import calendar

def get_personal_calendar_data(year, month, repo, username):
    calendar.setfirstweekday(6)
    month_name = calendar.month_name[month]
    weeks = calendar.monthcalendar(year, month)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    user = repo.find_user(username)

    events_by_day = {}

    if user.account_type not in {"Organizer", "Admin"}:
        for event in repo.list_user_signed_up_events_by_month(username, year, month):
            day = int(event.start_datetime[8:10])
            events_by_day.setdefault(day, []).append(event)
    else:
        for event in repo.list_user_events_by_month(username, year, month):
            day = int(event.start_datetime[8:10])
            events_by_day.setdefault(day, []).append(event)

    return dict(
        year=year, month=month, month_name=month_name,
        weeks=weeks,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
        events_by_day=events_by_day
    )
