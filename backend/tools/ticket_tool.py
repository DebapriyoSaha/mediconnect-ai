import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_ticket_bytes(appointment_details: dict) -> bytes:
    """
    Generates a PDF ticket in-memory and returns the bytes.
    """
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFillColor(colors.darkblue)
        c.rect(0, height - 100, width, 100, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50, height - 60, "Healthcare Assistant - Appointment Ticket")
        
        # Content
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 14)
        
        y = height - 150
        c.drawString(50, y, f"Appointment ID: {appointment_details.get('appointment_id')}")
        y -= 30
        c.drawString(50, y, f"Patient Name: {appointment_details.get('patient_name')}")
        y -= 30
        c.drawString(50, y, f"Doctor: {appointment_details.get('doctor_name')}")
        y -= 30
        c.drawString(50, y, f"Date: {appointment_details.get('date')}")
        y -= 30
        c.drawString(50, y, f"Time: {appointment_details.get('time')}")
        y -= 30
        
        # Location Details
        address = appointment_details.get('address')
        city = appointment_details.get('city')
        
        if address and city:
            c.setFont("Helvetica", 12)
            c.drawString(50, y, f"Address: {address}, {city}")
            y -= 30
        elif address:
            c.setFont("Helvetica", 12)
            c.drawString(50, y, f"Address: {address}")
            y -= 30
            
        y -= 20
        c.setFont("Helvetica-Oblique", 12)
        c.drawString(50, y, "Please arrive 15 minutes before your scheduled time.")
        c.drawString(50, y - 20, "Bring a valid ID and this ticket.")
        
        # Footer
        c.setFont("Helvetica", 10)
        c.drawString(50, 50, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"Error generating ticket: {e}")
        return None

def generate_ticket(appointment_details: dict) -> str:
    """
    Legacy wrapper: Generates PDF and returns a mock link (since we are serverless).
    The actual file is not saved to disk.
    """
    # For the agent tool, we just return a message saying it's ready.
    # The actual download link will be constructed by the agent or API.
    return f"/api/tickets/{appointment_details.get('appointment_id')}"
