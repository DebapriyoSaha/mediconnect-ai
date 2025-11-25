from langchain_core.tools import tool
from datetime import datetime, timedelta
import random
from database import get_db, Doctor, Patient, Appointment, MedicalRecord, Availability

@tool
def check_availability(doctor_id: str = None, date: str = None):
    """Checks availability for a specific doctor or all doctors on a given date (YYYY-MM-DD)."""
    db = next(get_db())
    try:
        query = db.query(Doctor)
        if doctor_id:
            # Try to find by ID or Name
            if doctor_id.isdigit():
                query = query.filter(Doctor.id == int(doctor_id))
            else:
                query = query.filter(Doctor.name.ilike(f"%{doctor_id}%"))
        
        doctors = query.all()
        if not doctors:
            return "No doctors found."
            
        results = []
        for doc in doctors:
            # Simple logic: Check if doctor works on this day (derived from date)
            # For MVP, we just show general hours and existing appointments
            appointments = db.query(Appointment).filter(Appointment.doctor_id == doc.id, Appointment.date == date).all()
            booked_times = [appt.time for appt in appointments]
            
            # Mock slots logic based on DB availability (simplified)
            slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
            available_slots = [s for s in slots if s not in booked_times]
            
            results.append(f"Dr. {doc.name} ({doc.specialty}): {', '.join(available_slots) if available_slots else 'Fully Booked'}")
            
        return "\n".join(results)
    finally:
        db.close()

@tool
def book_appointment(doctor_id: str, date: str, time: str, patient_id: str = "1"):
    """Books an appointment. Requires doctor_id (or name), date (YYYY-MM-DD), time (HH:MM), and patient_id."""
    db = next(get_db())
    try:
        # Find doctor
        doc = None
        if doctor_id.isdigit():
            doc = db.query(Doctor).filter(Doctor.id == int(doctor_id)).first()
        else:
            doc = db.query(Doctor).filter(Doctor.name.ilike(f"%{doctor_id}%")).first()
            
        if not doc:
            return f"Error: Doctor '{doctor_id}' not found."

        # Check if slot is taken
        existing = db.query(Appointment).filter(Appointment.doctor_id == doc.id, Appointment.date == date, Appointment.time == time).first()
        if existing:
            return f"Error: Slot {time} on {date} is already booked for Dr. {doc.name}."

        new_appt = Appointment(doctor_id=doc.id, patient_id=int(patient_id), date=date, time=time, status="confirmed")
        db.add(new_appt)
        db.commit()
        return f"Confirmed: Appointment booked with Dr. {doc.name} on {date} at {time}."
    finally:
        db.close()

@tool
def cancel_appointment(appointment_id: str):
    """Cancels an appointment by ID."""
    db = next(get_db())
    try:
        appt = db.query(Appointment).filter(Appointment.id == int(appointment_id)).first()
        if not appt:
            return "Error: Appointment not found."
        
        db.delete(appt)
        db.commit()
        return f"Appointment {appointment_id} cancelled successfully."
    finally:
        db.close()

@tool
def search_doctors(specialty: str = None):
    """Searches for doctors by specialty or lists all doctors."""
    db = next(get_db())
    try:
        query = db.query(Doctor)
        if specialty:
            query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
        
        doctors = query.all()
        if not doctors:
            return "No doctors found matching criteria."
            
        return "\n".join([f"ID: {d.id} | Dr. {d.name} - {d.specialty} | {d.bio}" for d in doctors])
    finally:
        db.close()

@tool
def get_patient_records(patient_id: str):
    """Retrieves patient medical history and records."""
    db = next(get_db())
    try:
        patient = db.query(Patient).filter(Patient.id == int(patient_id)).first()
        if not patient:
            return "Patient not found."
            
        records = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient.id).all()
        history = "\n".join([f"- {r.date}: {r.diagnosis} (Rx: {r.prescription})" for r in records])
        
        return f"Patient: {patient.name} (Age: {patient.age})\nMedical History:\n{history}"
    finally:
        db.close()

@tool
def get_billing_info(patient_id: str):
    """Retrieves billing and insurance information."""
    db = next(get_db())
    try:
        # Mock logic based on appointments
        appts = db.query(Appointment).filter(Appointment.patient_id == int(patient_id)).count()
        balance = appts * 100 # $100 per visit
        return f"Patient ID {patient_id}: Total Visits: {appts}. Outstanding Balance: ${balance}. Insurance: BlueCross (Active)."
    finally:
        db.close()

@tool
def verify_user(email: str):
    """Verifies if a user exists by email. Returns the user details if found, or None."""
    db = next(get_db())
    try:
        user = db.query(Patient).filter(Patient.email == email).first()
        if user:
            return f"User found: {user.name} (ID: {user.id}, Age: {user.age}, Gender: {user.gender})"
        return "User not found."
    finally:
        db.close()

@tool
def register_user(name: str, email: str, age: int, gender: str):
    """Registers a new user with name, email, age, and gender."""
    db = next(get_db())
    try:
        # Check if email already exists
        existing_user = db.query(Patient).filter(Patient.email == email).first()
        if existing_user:
            return f"Error: User with email {email} already exists."
            
        new_user = Patient(name=name, email=email, age=age, gender=gender)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return f"User registered successfully: {new_user.name} (ID: {new_user.id})"
    finally:
        db.close()
