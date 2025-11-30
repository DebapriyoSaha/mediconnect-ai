import urllib.parse
from datetime import datetime, timedelta


def generate_google_calendar_url(appointment_details: dict) -> str:
    """
    Generates a Google Calendar event URL.
    appointment_details: {
        "doctor_name": str,
        "date": str (YYYY-MM-DD),
        "time": str (HH:MM)
    }
    """
    try:
        date_str = appointment_details.get("date")
        time_str = appointment_details.get("time")
        
        if not date_str or not time_str:
            return ""

        # Parse start time
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        # Assume 1 hour duration
        end_dt = start_dt + timedelta(hours=1)
        
        # Format for Google Calendar (YYYYMMDDTHHMMSS)
        fmt = "%Y%m%dT%H%M%S"
        start_str = start_dt.strftime(fmt)
        end_str = end_dt.strftime(fmt)
        
        title = f"Appointment with {appointment_details.get('doctor_name')}"
        details = "Please arrive 15 minutes early. Bring your ID and ticket.\n\nReminder: Set a notification for 2 hours before."
        location = "Healthcare Clinic"
        
        base_url = "https://calendar.google.com/calendar/render"
        params = {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{start_str}/{end_str}",
            "details": details,
            "location": location,
            "sf": "true",
            "output": "xml"
        }
        
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    except Exception as e:
        print(f"Error generating calendar URL: {e}")
        return ""

def generate_ics_bytes(appointment_details: dict) -> bytes:
    """
    Generates an iCalendar (.ics) file content with a 2-hour reminder.
    """
    try:
        date_str = appointment_details.get("date")
        time_str = appointment_details.get("time")
        
        if not date_str or not time_str:
            return None

        # Parse start time
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(hours=1)
        
        # Format for iCal (YYYYMMDDTHHMMSS)
        fmt = "%Y%m%dT%H%M%S"
        start_str = start_dt.strftime(fmt)
        end_str = end_dt.strftime(fmt)
        now_str = datetime.now().strftime(fmt)
        
        uid = f"healthcare-appt-{appointment_details.get('appointment_id', '000')}@healthcare.com"
        
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Healthcare Assistant//NONSGML v1.0//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now_str}
DTSTART:{start_str}
DTEND:{end_str}
SUMMARY:Appointment with {appointment_details.get('doctor_name')}
DESCRIPTION:Please arrive 15 minutes early. Bring your ID and ticket.
LOCATION:Healthcare Clinic
BEGIN:VALARM
TRIGGER:-PT2H
ACTION:DISPLAY
DESCRIPTION:Reminder: Appointment in 2 hours
END:VALARM
END:VEVENT
END:VCALENDAR"""
        
        return ics_content.encode('utf-8')
    except Exception as e:
        print(f"Error generating ICS: {e}")
        return None
