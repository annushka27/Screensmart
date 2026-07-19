import datetime

def generate_slots():
    today = datetime.date.today()
    return [
        (today + datetime.timedelta(days=1)).strftime("%a, %b %d, %Y at 10:00 AM"),
        (today + datetime.timedelta(days=2)).strftime("%a, %b %d, %Y at 02:00 PM"),
        (today + datetime.timedelta(days=3)).strftime("%a, %b %d, %Y at 04:00 PM")
    ]
