import json
import math
import os
import random
import re
from datetime import datetime, timedelta

import requests
from ddgs import DDGS
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from serpapi import GoogleSearch

from database import (Appointment, Availability, Doctor, MedicalRecord,
                      Patient, get_db)
from tools.calendar_tool import generate_google_calendar_url


@tool
def check_availability(doctor_id: str | None = None, date: str | None = None):
    """Checks availability for a specific doctor or all doctors on a given date (YYYY-MM-DD)."""
    print(f"DEBUG: check_availability called with doctor_id={doctor_id}, date={date}")
    
    # FORCE FIX: Ensure date uses current year
    if date:
        current_year = str(datetime.now().year)
        # Find any 4-digit year (19xx or 20xx)
        match = re.search(r'\b(19|20)\d{2}\b', date)
        if match:
            found_year = match.group(0)
            if found_year != current_year:
                print(f"DEBUG: Correcting year {found_year} to {current_year} in date '{date}'")
                date = date.replace(found_year, current_year)
        
    db = next(get_db())
    try:
        query = db.query(Doctor)
        if doctor_id:
            # Try to match by ID first (if it's numeric), then by name
            try:
                doc_id_int = int(doctor_id)
                query = query.filter(Doctor.id == doc_id_int)
            except ValueError:
                # Not a number, search by name
                query = query.filter(Doctor.name.ilike(f"%{doctor_id}%"))
        
        doctors = query.all()
        
        if not doctors:
            return f"No doctors found with ID or name matching '{doctor_id}'."
            
        results = []
        for doc in doctors:
            # Check availability for this doctor
            # For simplicity, assume 9-5 availability unless booked
            # Fetch appointments for this date
            booked_times = []
            if date:
                appts = db.query(Appointment).filter(
                    Appointment.doctor_id == doc.id,
                    Appointment.date == date,
                    Appointment.status == "confirmed"
                ).all()
                booked_times = [appt.time for appt in appts]
            
            # Generate slots
            slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
            available_slots = [s for s in slots if s not in booked_times]
            
            results.append(f"| Dr. {doc.name} | {doc.specialty} | {', '.join(available_slots) if available_slots else 'Fully Booked'} |")
            
        header = "| Doctor Name | Specialty | Available Slots |\n|---|---|---|\n"
        return header + "\n".join(results)
    finally:
        db.close()

@tool
def book_appointment(doctor_id: str, date: str, time: str, patient_id: str):
    """Books an appointment. Requires doctor_id (or name), date (YYYY-MM-DD), time (HH:MM), and patient_id."""
    print(f"DEBUG: book_appointment called with doctor_id={doctor_id}, date={date}, time={time}, patient_id={patient_id}")
    
    # FORCE FIX: Ensure date uses current year
    if date:
        current_year = str(datetime.now().year)
        # Find any 4-digit year (19xx or 20xx)
        match = re.search(r'\b(19|20)\d{2}\b', date)
        if match:
            found_year = match.group(0)
            if found_year != current_year:
                print(f"DEBUG: Correcting year {found_year} to {current_year} in date '{date}'")
                date = date.replace(found_year, current_year)
    
    # Handle date parsing (if year is missing)
    try:
        # Check if date matches YYYY-MM-DD
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        try:
            # Try parsing as DD-MM or MM-DD (ambiguous, but let's assume user input is day-month or month-day based on locale, or just append year)
            # Better approach: If it doesn't look like YYYY-MM-DD, try to parse it with dateutil or simple logic
            # Let's assume the user might say "25th Oct" or "10-25". 
            # Simplest fix for "day and month" is to check if year is present.
            current_year = datetime.now().year
            # If date string is short (e.g. "10-25"), append year
            if len(date) <= 5:
                 date = f"{current_year}-{date}"
            else:
                 # If it's a text format like "October 25", we might need more robust parsing.
                 # For now, let's rely on the agent to provide YYYY-MM-DD usually, but if it sends "MM-DD", we fix it.
                 pass
        except Exception:
            pass

    # More robust fix: Use dateutil if available, or just manual check
    # Let's assume the agent sends "MM-DD" or "DD-MM" if it misses the year.
    if len(date.split('-')) == 2:
        date = f"{datetime.now().year}-{date}"
        
    db = next(get_db())
    try:
        # Find doctor
        try:
            doc_id = int(doctor_id)
            doc = db.query(Doctor).filter(Doctor.id == doc_id).first()
        except ValueError:
            doc = None

        if not doc:
            # Try by name
            doc = db.query(Doctor).filter(Doctor.name.ilike(f"%{doctor_id}%")).first()
            
        if not doc:
            print(f"DEBUG: Doctor '{doctor_id}' not found.")
            return f"Error: Doctor '{doctor_id}' not found."

        # Check if slot is taken
        existing = db.query(Appointment).filter(
            Appointment.doctor_id == doc.id,
            Appointment.date == date,
            Appointment.time == time,
            Appointment.status == "confirmed"
        ).first()
        
        if existing:
            print(f"DEBUG: Slot {time} on {date} is already booked.")
            return f"Error: Slot {time} on {date} is already booked for Dr. {doc.name}."

        new_appt = Appointment(doctor_id=doc.id, patient_id=int(patient_id), date=date, time=time, status="confirmed")
        db.add(new_appt)
        db.commit()
        db.refresh(new_appt)
        
        # Fetch patient name for better context
        patient = db.query(Patient).filter(Patient.id == int(patient_id)).first()
        patient_name = patient.name if patient else "Unknown"
        
        print(f"DEBUG: Appointment booked successfully. ID: {new_appt.id}")
        
        # Return structured info for the agent to use
        import json
        
        appt_details = {
            "doctor_name": doc.name,
            "date": date,
            "time": time,
            "clinic_name": doc.clinic_name,
            "address": doc.address,
            "city": doc.city
        }
        calendar_url = generate_google_calendar_url(appt_details)
        
        result = {
            "status": "confirmed",
            "appointment_id": new_appt.id,
            "doctor_name": doc.name,
            "patient_name": patient_name,
            "date": date,
            "time": time,
            "clinic_name": doc.clinic_name,
            "address": doc.address,
            "city": doc.city,
            "calendar_url": calendar_url,
            "message": f"Confirmed: Appointment booked with Dr. {doc.name} at {doc.address}, {doc.city} on {date} at {time}."
        }
        return json.dumps(result)
    except Exception as e:
        print(f"DEBUG: Exception in book_appointment: {str(e)}")
        return f"Error booking appointment: {str(e)}"
    finally:
        db.close()

@tool
def cancel_appointment(appointment_id: str, patient_id: str):
    """Cancels an existing appointment. Requires appointment_id and patient_id."""
    print(f"DEBUG: cancel_appointment called with appointment_id={appointment_id}, patient_id={patient_id}")
    
    db = next(get_db())
    try:
        # Find appointment
        appt = db.query(Appointment).filter(
            Appointment.id == int(appointment_id),
            Appointment.patient_id == int(patient_id)
        ).first()
        
        if not appt:
            return f"Error: Appointment {appointment_id} not found for patient {patient_id}."
            
        if appt.status == "cancelled":
            return f"Appointment {appointment_id} is already cancelled."
            
        # Update status
        appt.status = "cancelled"
        db.commit()
        
        return f"Appointment {appointment_id} has been successfully cancelled."
    except Exception as e:
        print(f"DEBUG: Exception in cancel_appointment: {str(e)}")
        return f"Error cancelling appointment: {str(e)}"
    finally:
        db.close()

@tool
def search_doctors(specialty: str | None = None, location: str | None = None, clinic_name: str | None = None):
    """
    Searches for doctors by specialty, location (city/address), or clinic name.
    Returns a Markdown table with columns: Name, Specialty, Clinic, Location, Next Available Slot.
    If local results are insufficient, performs a live web search and syncs to DB.
    """
    print(f"DEBUG: search_doctors called with specialty={specialty}, location={location}, clinic={clinic_name}")
    
    # 1. Parse User Location (Coordinates)
    user_lat = None
    user_lng = None
    if location and "Lat:" in location:
        try:
            lat_lng = location.split("Lat:")[1].split(", Lng:")
            user_lat = float(lat_lng[0].strip())
            user_lng = float(lat_lng[1].strip().replace("]", ""))
            print(f"DEBUG: Extracted coordinates: Lat={user_lat}, Lng={user_lng}")
        except:
            pass

    # 2. Resolve City Name (for fallback)
    resolved_city = None
    if user_lat and user_lng:
        try:
            # Use Nominatim to get city name from coordinates
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={user_lat}&lon={user_lng}"
            headers = {'User-Agent': 'HealthcareAgent/1.0'}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                address = data.get("address", {})
                resolved_city = address.get("city") or address.get("town") or address.get("village") or address.get("county")
                print(f"DEBUG: Resolved City for DB Query: {resolved_city}")
        except Exception as e:
            print(f"DEBUG: Reverse geocoding failed: {e}")

    # 3. Search Strategy
    local_doctors = []
    db = next(get_db())
    
    try:
        # Strategy A: Proximity Search (if coordinates available)
        if user_lat and user_lng:
            print(f"DEBUG: Attempting Proximity Search near {user_lat}, {user_lng}")
            # Fetch all doctors with matching specialty
            query = db.query(Doctor)
            if specialty:
                query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
            
            all_docs = query.all()
            
            # Filter by distance (Haversine)
            nearby_docs = []
            for doc in all_docs:
                if doc.latitude and doc.longitude:
                    # Simple Haversine approximation
                    R = 6371 # Radius of earth in km
                    dlat = math.radians(doc.latitude - user_lat)
                    dlon = math.radians(doc.longitude - user_lng)
                    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(user_lat)) * math.cos(math.radians(doc.latitude)) * math.sin(dlon/2) * math.sin(dlon/2)
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    d = R * c # Distance in km
                    
                    if d <= 20: # Within 20km
                        nearby_docs.append((d, doc))
            
            # Sort by distance
            nearby_docs.sort(key=lambda x: x[0])
            local_doctors = [doc for _, doc in nearby_docs]
            
            if local_doctors:
                print(f"DEBUG: Found {len(local_doctors)} doctors via Proximity Search.")

        # Strategy B: City/Text Search (Fallback)
        if not local_doctors:
            search_term = resolved_city or location
            if search_term and "Lat:" not in search_term: # Avoid using raw coords as search term
                print(f"DEBUG: Attempting City Search for: {search_term}")
                query = db.query(Doctor)
                if specialty:
                    query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
                
                query = query.filter(
                    (Doctor.city.ilike(f"%{search_term}%")) | 
                    (Doctor.address.ilike(f"%{search_term}%"))
                )
                local_doctors = query.all()
                if local_doctors:
                    print(f"DEBUG: Found {len(local_doctors)} doctors via City Search.")

    finally:
        db.close()

    # Return local results if found
    if local_doctors:
        print("DEBUG: Returning local results.")
        return format_doctor_table(local_doctors)

    # Strategy C: Live Web Search (if no local results)
    print("DEBUG: No local results found, performing live web search...")
    
    new_doctors = []
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    
    # Determine best location string for search
    search_location_str = resolved_city if resolved_city else location
    if search_location_str and "Lat:" in search_location_str:
        # If we still only have coords and no city, try to just use "India" or fail gracefully
        search_location_str = "India"
    
    if serpapi_key:
        try:
            print("DEBUG: Using SerpApi for Google Maps search...")
            params = {
                "engine": "google_maps",
                "q": f"{specialty or 'doctors'} {clinic_name or ''}".strip(),
                "api_key": serpapi_key,
                "type": "search",
                "gl": "in", # Restrict to India
            }
            
            # Handle coordinates if present in location string
            if location and "Lat:" in location:
                # Extract lat/lng
                try:
                    lat_lng = location.split("Lat:")[1].split(", Lng:")
                    lat = lat_lng[0].strip()
                    lng = lat_lng[1].strip().replace("]", "")
                    params["ll"] = f"@{lat},{lng},15z" # 15z is zoom level
                except:
                    pass
            
            # Append location text to query if available
            if search_location_str:
                if "india" not in search_location_str.lower():
                    search_location_str += ", India"
                params["q"] += f" in {search_location_str}"
                
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results.get("local_results", [])
            
            # Process web results
            for result in local_results:
                name = result.get("title", "")
                
                # Name Cleaning & Validation
                if not name or len(name) > 50: continue
                if "List" in name or "Directory" in name or "Best" in name or "Top" in name: continue
                
                # Robust Name Cleaning: Remove existing "Dr." or "Dr " prefixes (case insensitive)
                clean_name = re.sub(r"^(dr\.?|doctor)\s+", "", name, flags=re.IGNORECASE).strip()
                name = f"Dr. {clean_name}"
                    
                address = result.get("address", "Unknown")
                # Extract city from address if possible, else use the resolved_city or search location
                city = resolved_city or "Unknown"
                if "Unknown" in city and "," in address:
                        # Fallback to last part of address
                        parts = address.split(",")
                        if len(parts) > 1:
                            city = parts[-2].strip() if "India" in parts[-1] else parts[-1].strip()
                    
                # Extract Coordinates from SerpApi result if available
                gps = result.get("gps_coordinates", {})
                lat = gps.get("latitude")
                lng = gps.get("longitude")
                
                doctor_data = {
                    "name": name,
                    "specialty": specialty or result.get("type", "General Practice"),
                    "clinic_name": result.get("type", "Private Clinic"), 
                    "address": address,
                    "city": city,
                    "bio": result.get("description", "Experienced specialist."),
                    "latitude": lat,
                    "longitude": lng
                }
                new_doctors.append(doctor_data)
            
            # Save to DB
            if new_doctors:
                print(f"DEBUG: Saving {len(new_doctors)} new doctors to DB...")
                db = next(get_db())
                saved_doctors = []
                try:
                    for doc_data in new_doctors:
                        # Check if exists (by name and city)
                        exists = db.query(Doctor).filter(
                            Doctor.name == doc_data["name"], 
                            Doctor.city == doc_data["city"]
                        ).first()
                        
                        if not exists:
                            new_doc = Doctor(**doc_data)
                            db.add(new_doc)
                            db.flush()  # Get the ID without committing
                            saved_doctors.append(new_doc)
                            # Add default availability
                            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                            for day in days:
                                db.add(Availability(doctor=new_doc, day_of_week=day, start_time="09:00", end_time="17:00"))
                        else:
                            saved_doctors.append(exists)
                    db.commit()
                    
                    # Return the saved Doctor objects (with IDs) instead of dicts
                    return format_doctor_table(saved_doctors)
                except Exception as e:
                    print(f"DEBUG: Error saving to DB: {e}")
                    db.rollback()
                    # Fallback to returning dicts without IDs
                    return format_doctor_table(new_doctors)
                finally:
                    db.close()
        except Exception as e:
            print(f"DEBUG: SerpApi failed: {e}")
            # Fallback to DuckDuckGo...
            pass

    # Fallback: DuckDuckGo + LLM (Existing Logic)
    web_results_text = []
    try:
        # Enforce India in query
        # Use search_location_str which is resolved city or clean location
        base_query = f"top {specialty or 'doctors'} in {search_location_str or 'India'} {clinic_name or ''}".strip()
        if "india" not in base_query.lower():
            base_query += " India"
            
        query_str = base_query
        print(f"DEBUG: Searching web (DDGS) for: {query_str}")
        with DDGS() as ddgs:
            results = list(ddgs.text(query_str, max_results=10))
            for r in results:
                web_results_text.append(f"Title: {r['title']}\nLink: {r['href']}\nSnippet: {r['body']}\n")
    except Exception as e:
        print(f"DEBUG: Web search failed: {e}")

    if web_results_text:
        try:
            print("DEBUG: Extracting structured data using LLM...")
            llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
            
            prompt = f"""
            You are a data extraction assistant. Extract REAL doctor details from the following web search results.
            Return a JSON object with a key "doctors" containing a list of doctors.
            
            Rules:
            1. Each doctor object MUST have: "name", "specialty", "clinic_name", "address", "city", "bio".
            2. "name" MUST be a specific person's name (e.g., "Dr. Anjali Desai"), NOT "Dr. Unknown" or "Best Cardiologist".
            3. If you cannot find a specific doctor's name, DO NOT include that entry.
            4. Infer missing fields reasonably.
            
            Search Results:
            {"".join(web_results_text)}
            
            JSON Output:
            """
            
            response = llm.invoke(prompt)
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            data = json.loads(content.strip())
            extracted_doctors = data.get("doctors", [])
            
            db = next(get_db())
            final_doctors_list = []
            for doc_data in extracted_doctors:
                name = doc_data.get('name', 'Unknown')
                if "Unknown" in name or "Best" in name or len(name) < 5:
                    continue
                    
                exists = db.query(Doctor).filter(Doctor.name.ilike(f"%{name}%")).first()
                if not exists:
                    print(f"DEBUG: Adding new doctor: {name}")
                    new_doc = Doctor(
                        name=name,
                        specialty=doc_data.get('specialty', specialty or 'General Practice'),
                        clinic_name=doc_data.get('clinic_name', clinic_name or 'Unknown Clinic'),
                        address=doc_data.get('address', 'Unknown Address'),
                        city=doc_data.get('city', location or 'Unknown City'),
                        bio=doc_data.get('bio', 'Extracted from web search.')
                    )
                    db.add(new_doc)
                    db.commit()
                    db.refresh(new_doc)
                    
                    # Add Default Availability
                    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                    for day in days:
                        db.add(Availability(doctor_id=new_doc.id, day_of_week=day, start_time="09:00", end_time="17:00"))
                    db.commit()
                    
                    # Append the Doctor object (with ID) instead of dict
                    final_doctors_list.append(new_doc)
                else:
                    # Append existing Doctor object (has ID)
                    final_doctors_list.append(exists)
            
            if final_doctors_list:
                return format_doctor_table(final_doctors_list)
                
        except Exception as e:
            print(f"DEBUG: LLM extraction failed: {e}")
            return "Could not find specific doctors. Please try a different search."

    return "No doctors found matching your criteria."



import urllib.parse


def format_doctor_table(doctors):
    """Helper to format a list of Doctor objects or dictionaries into a Markdown table."""
    # User requested only Name and Location.
    header = "| Doctor Name | Location | Action |\n|---|---|---|\n"
    rows = []
    map_data = []
    
    db = next(get_db())
    try:
        for doc in doctors:
            name = ""
            city = ""
            lat = None
            lng = None
            specialty = ""
            clinic = ""
            
            if isinstance(doc, dict):
                name = doc.get("name", "Unknown")
                city = doc.get("city", "Unknown")
                lat = doc.get("latitude")
                lng = doc.get("longitude")
                specialty = doc.get("specialty", "General")
                clinic = doc.get("clinic_name", "Clinic")
                doc_id = doc.get("id", "")  # Get ID from dict if available
            else:
                try:
                    d = db.merge(doc)
                    name = d.name
                    city = d.city
                    lat = d.latitude
                    lng = d.longitude
                    specialty = d.specialty
                    clinic = d.clinic_name
                    doc_id = d.id
                except Exception:
                    name = getattr(doc, "name", "Unknown")
                    city = getattr(doc, "city", "Unknown")
                    lat = getattr(doc, "latitude", None)
                    lng = getattr(doc, "longitude", None)
                    specialty = getattr(doc, "specialty", "General")
                    clinic = getattr(doc, "clinic_name", "Clinic")
                    doc_id = getattr(doc, "id", "")
            
            # Bold the name for professional look
            # Add Book Action Link (ID is used internally in URL but not displayed)
            
            # URL Encode parameters to prevent Markdown breakage
            safe_name = urllib.parse.quote(name)
            safe_id = urllib.parse.quote(str(doc_id)) if doc_id else ""
            
            # Include ID in URL for internal routing, but button text shows no ID
            if safe_id:
                action_link = f"[Book Appointment](/book_appointment?id={safe_id}&name={safe_name})"
            else:
                action_link = f"[Book Appointment](/book_appointment?name={safe_name})"
            rows.append(f"| **{name}** | {city} | {action_link} |")
            
            if lat and lng:
                map_data.append({
                    "name": name,
                    "latitude": lat,
                    "longitude": lng,
                    "specialty": specialty,
                    "clinic_name": clinic
                })
                
    finally:
        db.close()
        
    output = header + "\n".join(rows)
    
    # Append hidden map data if available
    if map_data:
        output += f"\n\n<!-- MAP_DATA_START -->{json.dumps(map_data)}<!-- MAP_DATA_END -->"
    
    return output

@tool
def get_patient_records(patient_id: str):
    """Retrieves medical records for a patient."""
    db = next(get_db())
    try:
        records = db.query(MedicalRecord).filter(MedicalRecord.patient_id == int(patient_id)).all()
        if not records:
            return "No medical records found."
        
        # Calculate outstanding balance (mock logic)
        appts = db.query(Appointment).filter(Appointment.patient_id == int(patient_id)).count()
        balance = appts * 50 # $50 per visit
        
        return f"Patient ID {patient_id}: Total Visits: {appts}. Outstanding Balance: ${balance}. Insurance: BlueCross (Active)."
    finally:
        db.close()

import re


def is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

@tool
def verify_user(email: str):
    """Verifies if a user exists by email. Returns the user details if found, or None."""
    if not is_valid_email(email):
        return "Error: Invalid email format. Please provide a valid email address (e.g., user@example.com)."
        
    db = next(get_db())
    try:
        user = db.query(Patient).filter(Patient.email == email).first()
        if user:
            return f"User found: {user.name} (ID: {user.id}, Age: {user.age}, Gender: {user.gender})"
        return "User not found."
    finally:
        db.close()

@tool
def register_user(name: str, email: str, age: int | str, gender: str):
    """Registers a new user with name, email, age, and gender."""
    if not is_valid_email(email):
        return "Error: Invalid email format. Please provide a valid email address (e.g., user@example.com)."

    db = next(get_db())
    try:
        # Check if email already exists
        existing_user = db.query(Patient).filter(Patient.email == email).first()
        if existing_user:
            return f"Error: User with email {email} already exists."
            
        new_user = Patient(name=name, email=email, age=int(age), gender=gender)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return f"User registered successfully: {new_user.name} (ID: {new_user.id})"
    finally:
        db.close()

@tool
def add_medical_record(patient_id: str, diagnosis: str, prescription: str, date: str = None):
    """
    Adds a new medical record for a patient.
    Use this when you identify a diagnosis and prescription from an uploaded file or conversation.
    date format: YYYY-MM-DD (defaults to today if not provided).
    """
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    db = next(get_db())
    try:
        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == int(patient_id)).first()
        if not patient:
            return f"Error: Patient with ID {patient_id} not found."
            
        new_record = MedicalRecord(
            patient_id=int(patient_id),
            date=date,
            diagnosis=diagnosis,
            prescription=prescription
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return f"Medical record added successfully: {date} - {diagnosis} (Rx: {prescription})"
    finally:
        db.close()

@tool
def get_billing_info(patient_id: str):
    """Retrieves billing information for a patient, including outstanding balance and insurance status."""
    db = next(get_db())
    try:
        # Check if patient exists
        patient = db.query(Patient).filter(Patient.id == int(patient_id)).first()
        if not patient:
            return f"Error: Patient with ID {patient_id} not found."

        # Calculate outstanding balance (mock logic based on appointments)
        appts = db.query(Appointment).filter(Appointment.patient_id == int(patient_id)).count()
        balance = appts * 50.0 # $50 per visit
        
        # In a real system, we would check an Invoice table
        
        return json.dumps({
            "patient_id": patient_id,
            "name": patient.name,
            "outstanding_balance": f"${balance:.2f}",
            "insurance_provider": "BlueCross BlueShield",
            "insurance_status": "Active",
            "last_payment_date": "2024-10-15"
        })
    except Exception as e:
        return f"Error retrieving billing info: {str(e)}"
    finally:
        db.close()
