from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv
import sqlitecloud # Import to register the dialect
import os

load_dotenv()

api_key = os.getenv("SQLITE_CLOUD_API_KEY")
SQLALCHEMY_DATABASE_URL = f"sqlitecloud://catpee6mvk.g2.sqlite.cloud:8860/healthcare.db?apikey={api_key}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    specialty = Column(String, index=True)
    bio = Column(String)
    
    appointments = relationship("Appointment", back_populates="doctor")
    availabilities = relationship("Availability", back_populates="doctor")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, index=True)
    age = Column(Integer)
    gender = Column(String)
    
    appointments = relationship("Appointment", back_populates="patient")
    medical_records = relationship("MedicalRecord", back_populates="patient")

class Availability(Base):
    __tablename__ = "availabilities"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    day_of_week = Column(String) # Monday, Tuesday, etc.
    start_time = Column(String) # 09:00
    end_time = Column(String) # 17:00
    
    doctor = relationship("Doctor", back_populates="availabilities")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    date = Column(String) # YYYY-MM-DD
    time = Column(String) # HH:MM
    status = Column(String, default="confirmed") # confirmed, cancelled
    reason = Column(String)
    
    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    date = Column(String)
    diagnosis = Column(String)
    prescription = Column(String)
    
    patient = relationship("Patient", back_populates="medical_records")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
