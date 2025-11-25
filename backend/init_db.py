from database import engine, Base, SessionLocal, Doctor, Patient, Availability, Appointment, MedicalRecord
from datetime import datetime, timedelta

def init_db():
    # Drop dependent tables first to avoid FK errors
    MedicalRecord.__table__.drop(engine, checkfirst=True)
    Appointment.__table__.drop(engine, checkfirst=True)
    Availability.__table__.drop(engine, checkfirst=True)
    Patient.__table__.drop(engine, checkfirst=True)
    Doctor.__table__.drop(engine, checkfirst=True)
    
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if data exists
    if db.query(Doctor).first():
        print("Database already initialized.")
        return

    # Create Doctors
    doctors = [
        Doctor(name="Sarah Smith", specialty="Cardiology", bio="Expert in heart health with 15 years of experience."),
        Doctor(name="Michael Jones", specialty="Dermatology", bio="Specializes in skin conditions and cosmetic procedures."),
        Doctor(name="Emily Chen", specialty="Pediatrics", bio="Caring pediatrician focused on child development."),
        Doctor(name="David Wilson", specialty="General Practice", bio="Comprehensive primary care for the whole family.")
    ]
    db.add_all(doctors)
    db.commit()
    
    # Create Patients
    patients = [
        Patient(name="Debapriyo Saha", email="debopriyo.saha@gmail.com", age=45, gender="Male"),
        Patient(name="Rohit Agarwal", email="rohit.agarwal@gmail.com", age=32, gender="Male"),
        Patient(name="Pratik Dasgupta", email="pratik.dasgupta@gmail.com", age=60, gender="Male")
    ]
    db.add_all(patients)
    db.commit()
    
    # Create Availabilities (Mocking for next 7 days)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for doctor in doctors:
        for day in days:
            db.add(Availability(doctor_id=doctor.id, day_of_week=day, start_time="09:00", end_time="17:00"))
    db.commit()
    
    # Create some Medical Records
    records = [
        MedicalRecord(patient_id=1, date="2023-10-15", diagnosis="Hypertension", prescription="Lisinopril 10mg"),
        MedicalRecord(patient_id=1, date="2024-01-20", diagnosis="Regular Checkup", prescription="None"),
        MedicalRecord(patient_id=2, date="2023-11-05", diagnosis="Eczema", prescription="Hydrocortisone Cream"),
        MedicalRecord(patient_id=3, date="2023-12-10", diagnosis="Type 2 Diabetes", prescription="Metformin 500mg")
    ]
    db.add_all(records)
    db.commit()
    
    print("Database initialized with dummy data!")
    db.close()

if __name__ == "__main__":
    init_db()
