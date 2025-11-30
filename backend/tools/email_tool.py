import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

from tools.calendar_tool import (generate_google_calendar_url,
                                 generate_ics_bytes)
from tools.ticket_tool import generate_ticket_bytes

load_dotenv()

def send_confirmation_email(email: str, appointment_details: dict, ticket_path: str = None, ticket_bytes: bytes = None):
    """
    Sends a confirmation email with the ticket using SMTP.
    Falls back to mock if credentials are not set.
    """
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not smtp_email or not smtp_password:
        print(f"\n[MOCK EMAIL SERVICE] (Set SMTP_EMAIL and SMTP_PASSWORD to send real emails)")
        print(f"To: {email}")
        print(f"Subject: Appointment Confirmation - {appointment_details.get('date')}")
        print(f"Attachment: {ticket_path or 'In-Memory PDF'}")
        return "Email sent successfully (Mock)."

    try:
        msg = MIMEMultipart()
        msg["From"] = f"Healthcare Assistant <{smtp_email}>"
        msg["To"] = email
        msg["Subject"] = f"Appointment Confirmation - {appointment_details.get('date')}"

        # Generate Calendar Link
        calendar_url = appointment_details.get("calendar_url")
        if not calendar_url:
            calendar_url = generate_google_calendar_url(appointment_details)

        html_body = f"""
        <html>
          <body>
            <p>Dear {appointment_details.get('patient_name')},</p>
            <p>Your appointment with <strong>{appointment_details.get('doctor_name')}</strong> is confirmed.</p>
            <ul>
              <li><strong>Date:</strong> {appointment_details.get('date')}</li>
              <li><strong>Time:</strong> {appointment_details.get('time')}</li>
              <li><strong>Address:</strong> {appointment_details.get('address')}, {appointment_details.get('city')}</li>
            </ul>
            <p>
              <a href="{calendar_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Add to Google Calendar</a>
            </p>
            <p>Please find your appointment ticket attached.</p>
            <br>
            <p>Regards,<br>Healthcare Assistant</p>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        # Auto-generate PDF if bytes are missing but details are present
        if not ticket_bytes and not ticket_path and appointment_details:
            print("[EMAIL SERVICE] Generating ticket PDF on-the-fly...")
            ticket_bytes = generate_ticket_bytes(appointment_details)

        # Attach PDF
        if ticket_bytes:
            part = MIMEApplication(ticket_bytes, Name=f"ticket_{appointment_details.get('appointment_id')}.pdf")
            part['Content-Disposition'] = f'attachment; filename="ticket_{appointment_details.get("appointment_id")}.pdf"'
            msg.attach(part)
        elif ticket_path and os.path.exists(ticket_path):
            with open(ticket_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(ticket_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(ticket_path)}"'
            msg.attach(part)

        # Attach iCal (.ics)
        ics_bytes = generate_ics_bytes(appointment_details)
        if ics_bytes:
            part = MIMEApplication(ics_bytes, Name="reminder.ics")
            part['Content-Disposition'] = 'attachment; filename="reminder.ics"'
            msg.attach(part)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(smtp_email, smtp_password)
            server.send_message(msg)
            
        print(f"[EMAIL SERVICE] Real email sent to {email}")
        return "Email sent successfully."

    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email: {e}")
        return f"Error sending email: {e}"
