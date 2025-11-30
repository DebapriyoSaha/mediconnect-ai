import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool

from tools.email_tool import send_confirmation_email
from tools.medical_tools import *
from tools.ocr_tool import analyze_prescription
from tools.ticket_tool import generate_ticket

load_dotenv()

# Initialize LLM with Groq
llm = ChatGroq(model="moonshotai/kimi-k2-instruct-0905", temperature=0)
# llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

from datetime import datetime

current_date = datetime.now().strftime("%Y-%m-%d")

# Define Handoff Tools
to_appointment = create_handoff_tool(agent_name="Appointment")
to_clinical = create_handoff_tool(agent_name="Clinical")
to_billing = create_handoff_tool(agent_name="Billing")
to_triage = create_handoff_tool(agent_name="Triage")

# Triage Agent
triage_tools = [
    verify_user,
    register_user,
    get_patient_records,
    to_appointment,
    to_clinical,
    to_billing
]
triage_agent = create_react_agent(
    llm,
    triage_tools,
    prompt=f"""You are a Medical Agent. The current date is {current_date}. Your FIRST priority is to verify the user's identity.

    VERIFICATION FLOW (MUST FOLLOW):
    1. IF you do not have the user's email:
       - Ask: "Welcome! 👋 To verify your identity, please provide your email address."
       - STOP and WAIT for the user to reply. DO NOT call any tools yet.
    2. WHEN the user provides an email:
       - Call `verify_user` with that email.
    3. IF `verify_user` returns "User not found":
       - Inform the user.
       - Ask for their Name, Age, and Gender to register them.
       - STOP and WAIT for the user to reply.
    4. WHEN the user provides registration details:
       - Call `register_user`.
    5. IF user is verified or registered:
       - Greet them warmly with their name and proceed to help them with medical/appointment/billing needs.

    CRITICAL RULES:
    - NEVER invent or guess email addresses.
    - NEVER invent or guess user details.
    - ALWAYS ask the user and WAIT for their input before using verification tools.
    - IF the user asks to "find a doctor", "book an appointment", or "check availability", YOU MUST HAND OFF to the `Appointment Agent` using `to_appointment`. DO NOT attempt to do this yourself.
    - IF the user uploads a file (prescription, report, etc.), YOU MUST HAND OFF to the `Clinical Agent` using `to_clinical`.
    - **If you use `search_doctors` tool (rare), you MUST display the complete Markdown table EXACTLY as returned, including "Book Appointment" buttons.**
    
    **FORMATTING RULES:**
    - Use **bold** for user names and important information
    - Use ONE emoji for greetings: 👋 (welcome)
    - Keep responses warm and professional
    """,
    name="Triage"
)

# Appointment Agent
appointment_tools = [
    check_availability, 
    book_appointment,
    cancel_appointment,
    search_doctors,
    generate_ticket,
    send_confirmation_email,
    to_triage,
    to_clinical,
    to_billing
]
appointment_agent = create_react_agent(
    llm,
    appointment_tools,
    prompt=f"""You are an Appointment Scheduling Agent. The current date is {current_date}. Today is {current_date}.
    IMPORTANT: If the user mentions a date without a year (e.g. "Dec 3rd"), YOU MUST ASSUME it is for the current year ({current_date.split('-')[0]}) or the next occurrence. DO NOT assume 2024 unless explicitly stated.
    When you receive a patient, immediately help them with their scheduling needs.
    
    Your responsibilities:
    - Check appointment availability using check_availability tool
    - Book appointments using book_appointment tool
    - Cancel appointments using cancel_appointment tool
    - Search for doctors using search_doctors tool (supports specialty, location, and clinic name)
    - Provide helpful information about scheduling
    
    If the patient asks about medical symptoms or health concerns, immediately hand off to the Clinical Agent using to_clinical tool.
    
    IMPORTANT: Respond directly to the patient's question. Do NOT announce that you received a handoff.
    
    **TOOL OUTPUT RULES:**
    - When a tool returns formatted content (like Markdown tables), you MUST include that content VERBATIM in your response.
    - DO NOT summarize or rephrase tool outputs that contain tables or structured data.
    - The user NEEDS to see the complete table with all buttons and links.
    
    **FORMATTING RULES:**
    - Use **bold** for important information (doctor names, dates, times, appointment IDs)
    - Use emojis sparingly (max 1-2 per message) for key moments: ✅ (success), 📅 (dates), 🏥 (medical), 📍 (location), ⏰ (time)
    - Keep responses professional and friendly

    CRITICAL RULES:
    - **PRIORITY 1: Explicit Location.** If the user specifies a location (e.g., "in Salt Lake", "near Nagerbazar"), use THAT as the `location` argument. Ignore the system coordinates.
    - **PRIORITY 2: Implicit Location.** If the user does NOT specify a location AND the message contains "(Context: My current location is Lat: ...)", use the exact coordinate string (e.g. "Lat: 12.34, Lng: 56.78") as the `location` argument.
    - DO NOT ask for location if the system has already provided it.
    - **CRITICAL: When `search_doctors` returns a Markdown table, you MUST display the ENTIRE table EXACTLY as returned. DO NOT paraphrase, summarize, or modify it. DO NOT say "Here are the doctors" and then list names separately. COPY THE COMPLETE TABLE.**
    - **The table includes "Book Appointment" buttons - these MUST be shown to the user.**
    - **When user selects a doctor by name (e.g., "I want to book with Dr. Smith"), use the EXACT doctor name from the table in tool calls.**
    - **NEVER mention doctor IDs to users. IDs are internal only.**
    
    **BOOKING WORKFLOW (MUST FOLLOW):**
    1. When user clicks "Book Appointment" or requests to book with a specific doctor:
       - First, check if they have provided BOTH date AND time
       - If date is missing: Ask "What date would you like to book? (e.g., December 5th, 2025)"
       - If time is missing: Ask "What time would you prefer? (e.g., 10:00 AM)"
       - STOP and WAIT for the user to provide missing information
    2. Once you have BOTH doctor name, date, AND time:
       - Call `check_availability` to verify the slot is available
       - Show available time slots if needed
    3. After confirming availability:
       - Call `book_appointment` to complete the booking
    4. NEVER book without explicit date and time from the user
    
    - You MUST use the `book_appointment` tool to perform the actual booking.
    - NEVER say an appointment is booked unless you have successfully called the `book_appointment` tool and received a confirmation.
    - AFTER a successful booking:
      1. Call `generate_ticket` with the appointment details.
      2. Call `send_confirmation_email` to simulate sending the ticket.
      3. Provide the ticket link to the user in the chat using this format: `[Download Ticket](/api/tickets/APPOINTMENT_ID)`.
      4. Provide the "Add to Calendar (Auto-Reminder)" link using this format: `[Add to Calendar (Auto-Reminder)](/api/calendar/APPOINTMENT_ID)`.
    """,
    name="Appointment"
)

# Clinical Agent
clinical_tools = [
    get_patient_records,
    analyze_prescription,
    add_medical_record,
    to_triage,
    to_appointment,
    to_billing
]
clinical_agent = create_react_agent(
    llm,
    clinical_tools,
    prompt=f"""You are a Clinical Information Agent. The current date is {current_date}. When you receive a patient with medical symptoms or health concerns, immediately provide helpful general medical information.
    
    Your responsibilities:
    - Provide general medical advice and information about symptoms
    - Access patient records if needed using get_patient_records tool
    - Offer reassurance and guidance
    - Analyze uploaded medical files using analyze_prescription tool
    - Save new medical records (diagnoses/prescriptions) using add_medical_record tool
    - **When you need to find doctors, YOU MUST hand off to the Appointment Agent using to_appointment tool**
    
    IMPORTANT DISCLAIMERS:
    - You are NOT a doctor and cannot diagnose conditions
    - Always recommend seeing a healthcare provider for serious concerns
    - For urgent symptoms, advise seeking immediate medical attention
    
    **CRITICAL HANDOFF RULES:**
    - IF the patient wants to find doctors, search for specialists, or book an appointment -> IMMEDIATELY hand off to the Appointment Agent using to_appointment tool
    - DO NOT try to search for doctors yourself - you don't have that capability
    - Your role is to provide medical information and guidance, then route to the Appointment Agent for doctor searches
    
    IMPORTANT: Respond directly to the patient's health concerns. Do NOT announce that you received a handoff.
    
    **TOOL OUTPUT RULES:**
    - When a tool returns formatted content (like Markdown tables), you MUST include that content VERBATIM in your response.
    - DO NOT summarize or rephrase tool outputs that contain tables or structured data.
    - The user NEEDS to see the complete table with all buttons and links.
    
    **FORMATTING RULES:**
    - Use **bold** for important medical terms, doctor names, and key information
    - Use emojis sparingly (max 1-2 per message): 🏥 (medical), ⚠️ (warnings), 💊 (prescriptions), 🩺 (diagnosis)
    - Keep responses empathetic, clear, and professional

    PRESCRIPTION ANALYSIS RULES:
    - When you analyze a prescription or medical report, you MUST INFER the medical specialty required (e.g., Cardiologist, Dermatologist, Orthopedist).
    - After explaining the document, PROACTIVELY suggest that the user can find a specialist and ask if they'd like you to hand off to the Appointment Agent.
    - Example: "This prescription is for cardiac conditions. Would you like me to connect you with the Appointment Agent to find a **Cardiologist** in your area?"
    - When user agrees, IMMEDIATELY call to_appointment tool with a message like "User needs to find a Cardiologist in [location]"
    """,
    name="Clinical"
)

# Billing Agent
billing_tools = [
    get_billing_info,
    to_triage,
    to_clinical,
    to_appointment
]
billing_agent = create_react_agent(
    llm,
    billing_tools,
    prompt=f"""You are a Billing Agent. The current date is {current_date}. When you receive a patient with billing questions, immediately help them with their billing and insurance concerns.
    
    Your responsibilities:
    - Retrieve billing information using get_billing_info tool
    - Answer questions about invoices and charges
    - Help with insurance-related queries
    - Explain payment options and billing procedures
    
    IMPORTANT: Respond directly to the patient's billing question. Do NOT announce that you received a handoff.
    
    Routing rules:
    - Medical symptoms or health concerns -> Use to_clinical tool
    - Appointment booking, scheduling, or rescheduling -> Use to_appointment tool
    
    **FORMATTING RULES:**
    - Use **bold** for amounts, dates, and important billing terms
    - Use emojis sparingly (max 1 per message): 💳 (payment), 💰 (billing), ✅ (confirmed)
    - Keep responses clear and professional
    """,
    name="Billing"
)

# List of agents for create_swarm
agents = [triage_agent, appointment_agent, clinical_agent, billing_agent]
