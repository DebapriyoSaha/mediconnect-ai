from datetime import datetime, timedelta

from database import (Appointment, Availability, Base, Doctor, MedicalRecord,
                      Patient, SessionLocal, engine)


def init_db():
    # Drop dependent tables first to avoid FK errors
    MedicalRecord.__table__.drop(engine, checkfirst=True)
    Appointment.__table__.drop(engine, checkfirst=True)
    Availability.__table__.drop(engine, checkfirst=True)
    Patient.__table__.drop(engine, checkfirst=True)
    Doctor.__table__.drop(engine, checkfirst=True)
    
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Create Doctors (Exhaustive Indian List with Locations)
    doctors_data = [
        # Cardiology
        {"name": "Dr. Rajesh Koothrappali", "specialty": "Cardiology", "bio": "Senior Interventional Cardiologist, 20+ years exp.", "clinic_name": "Apollo Hospitals", "address": "Greams Road", "city": "Chennai", "latitude": 13.06, "longitude": 80.25},
        {"name": "Dr. Anjali Desai", "specialty": "Cardiology", "bio": "Specialist in pediatric cardiology and heart defects.", "clinic_name": "Fortis Hospital", "address": "Bannerghatta Road", "city": "Bangalore", "latitude": 12.90, "longitude": 77.60},
        {"name": "Dr. Vikram Malhotra", "specialty": "Cardiology", "bio": "Expert in heart failure management and transplants.", "clinic_name": "Medanta - The Medicity", "address": "Sector 38", "city": "Gurgaon", "latitude": 28.44, "longitude": 77.04},
        {"name": "Dr. Suresh Kumar", "specialty": "Cardiology", "bio": "Renowned cardiologist specializing in angioplasty.", "clinic_name": "AIIMS", "address": "Ansari Nagar", "city": "New Delhi", "latitude": 28.56, "longitude": 77.21},
        
        # Dermatology
        {"name": "Dr. Priya Sharma", "specialty": "Dermatology", "bio": "Cosmetic dermatologist and laser specialist.", "clinic_name": "Kaya Skin Clinic", "address": "Indiranagar", "city": "Bangalore", "latitude": 12.97, "longitude": 77.64},
        {"name": "Dr. Rahul Verma", "specialty": "Dermatology", "bio": "Clinical dermatologist focusing on acne and psoriasis.", "clinic_name": "Dr. Batra's", "address": "Bandra West", "city": "Mumbai", "latitude": 19.06, "longitude": 72.83},
        {"name": "Dr. Meera Iyer", "specialty": "Dermatology", "bio": "Expert in skin cancer screening and treatment.", "clinic_name": "Apollo Spectra", "address": "MRC Nagar", "city": "Chennai", "latitude": 13.02, "longitude": 80.27},
        
        # Pediatrics
        {"name": "Dr. Amit Patel", "specialty": "Pediatrics", "bio": "General pediatrician with a focus on child nutrition.", "clinic_name": "Cloudnine Hospital", "address": "Jayanagar", "city": "Bangalore", "latitude": 12.93, "longitude": 77.58},
        {"name": "Dr. Sneha Kapoor", "specialty": "Pediatrics", "bio": "Neonatologist and early child development expert.", "clinic_name": "Rainbow Children's Hospital", "address": "Banjara Hills", "city": "Hyderabad", "latitude": 17.41, "longitude": 78.44},
        {"name": "Dr. Rohan Das", "specialty": "Pediatrics", "bio": "Pediatric immunologist and allergy specialist.", "clinic_name": "Sir Ganga Ram Hospital", "address": "Rajinder Nagar", "city": "New Delhi", "latitude": 28.63, "longitude": 77.18},
        
        # Gynecology
        {"name": "Dr. Anjali Gupta", "specialty": "Gynecology", "bio": "Obstetrician and gynecologist, high-risk pregnancy expert.", "clinic_name": "Max Super Speciality Hospital", "address": "Saket", "city": "New Delhi", "latitude": 28.52, "longitude": 77.21},
        {"name": "Dr. Kavita Singh", "specialty": "Gynecology", "bio": "Specialist in reproductive endocrinology and IVF.", "clinic_name": "Lilavati Hospital", "address": "Bandra", "city": "Mumbai", "latitude": 19.05, "longitude": 72.83},
        {"name": "Dr. Neha Agarwal", "specialty": "Gynecology", "bio": "Expert in laparoscopic gynecological surgeries.", "clinic_name": "Manipal Hospitals", "address": "Old Airport Road", "city": "Bangalore", "latitude": 12.96, "longitude": 77.65},
        
        # Orthopedics
        {"name": "Dr. Vikram Singh", "specialty": "Orthopedics", "bio": "Orthopedic surgeon specializing in joint replacements.", "clinic_name": "Sparsh Hospital", "address": "Infantry Road", "city": "Bangalore", "latitude": 12.98, "longitude": 77.61},
        {"name": "Dr. Arjun Nair", "specialty": "Orthopedics", "bio": "Sports medicine specialist and arthroscopic surgeon.", "clinic_name": "Kokilaben Dhirubhai Ambani Hospital", "address": "Andheri West", "city": "Mumbai", "latitude": 19.13, "longitude": 72.82},
        {"name": "Dr. Manoj Kumar", "specialty": "Orthopedics", "bio": "Spine surgeon and trauma specialist.", "clinic_name": "MIOT International", "address": "Manapakkam", "city": "Chennai", "latitude": 13.01, "longitude": 80.18},
        
        # General Practice
        {"name": "Dr. Sneha Reddy", "specialty": "General Practice", "bio": "Family physician with a holistic approach.", "clinic_name": "Apollo Clinic", "address": "HSR Layout", "city": "Bangalore", "latitude": 12.91, "longitude": 77.64},
        {"name": "Dr. Suresh Menon", "specialty": "General Practice", "bio": "General practitioner with 30 years of community service.", "clinic_name": "Practo Care", "address": "Whitefield", "city": "Bangalore", "latitude": 12.97, "longitude": 77.75},
        {"name": "Dr. Deepa Rao", "specialty": "General Practice", "bio": "Focus on preventive medicine and lifestyle management.", "clinic_name": "Columbia Asia", "address": "Hebbal", "city": "Bangalore", "latitude": 13.03, "longitude": 77.59}
    ]

    doctors = []
    for doc_data in doctors_data:
        doc = Doctor(**doc_data)
        db.add(doc)
        doctors.append(doc)
    
    db.commit()
    # Refresh to get IDs
    for doc in doctors:
        db.refresh(doc)
    
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
    
    print("Database initialized with exhaustive Indian doctor list and dummy data!")
    db.close()

if __name__ == "__main__":
    init_db()
