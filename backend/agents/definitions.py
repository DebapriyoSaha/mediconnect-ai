from langchain_groq import ChatGroq
from tools.medical_tools import check_availability, book_appointment, get_patient_records, get_billing_info, cancel_appointment, search_doctors, verify_user, register_user
from langgraph_swarm import create_handoff_tool
from langgraph.prebuilt import create_react_agent
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM with Groq
llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0)

# Define Handoff Tools
to_appointment = create_handoff_tool(agent_name="Appointment")
to_clinical = create_handoff_tool(agent_name="Clinical")
to_billing = create_handoff_tool(agent_name="Billing")
to_triage = create_handoff_tool(agent_name="Triage")

# Triage Agent
triage_tools = [
    verify_user,
    register_user,
    check_availability, 
    get_patient_records,
    to_appointment,
    to_clinical,
    to_billing
]
triage_agent = create_react_agent(
    llm,
    triage_tools,
    prompt="""You are a Medical Agent. Your FIRST priority is to verify the user's identity.

    VERIFICATION FLOW (MUST FOLLOW):
    1. IF you do not have the user's email:
       - Ask: "Welcome! To verify your identity, please provide your email address."
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
       - Proceed to help them with medical/appointment/billing needs.

    CRITICAL RULES:
    - NEVER invent or guess email addresses.
    - NEVER invent or guess user details.
    - ALWAYS ask the user and WAIT for their input before using verification tools.
    """,
    name="Triage"
)

# Appointment Agent
appointment_tools = [
    check_availability, 
    book_appointment,
    cancel_appointment,
    search_doctors,
    to_triage,
    to_clinical,
    to_billing
]
appointment_agent = create_react_agent(
    llm,
    appointment_tools,
    prompt="""You are an Appointment Scheduling Agent. When you receive a patient, immediately help them with their scheduling needs.
    
    Your responsibilities:
    - Check appointment availability using check_availability tool
    - Book appointments using book_appointment tool
    - Cancel appointments using cancel_appointment tool
    - Search for doctors using search_doctors tool
    - Provide helpful information about scheduling
    
    If the patient asks about medical symptoms or health concerns, immediately hand off to the Clinical Agent using to_clinical tool.
    
    IMPORTANT: Respond directly to the patient's question. Do NOT announce that you received a handoff.
    """,
    name="Appointment"
)

# Clinical Agent
clinical_tools = [
    get_patient_records,
    search_doctors,
    to_triage,
    to_appointment,
    to_billing
]
clinical_agent = create_react_agent(
    llm,
    clinical_tools,
    prompt="""You are a Clinical Information Agent. When you receive a patient with medical symptoms or health concerns, immediately provide helpful general medical information.
    
    Your responsibilities:
    - Provide general medical advice and information about symptoms
    - Access patient records if needed using get_patient_records tool
    - Recommend specialists using search_doctors tool if needed
    - Offer reassurance and guidance
    
    IMPORTANT DISCLAIMERS:
    - You are NOT a doctor and cannot diagnose conditions
    - Always recommend seeing a healthcare provider for serious concerns
    - For urgent symptoms, advise seeking immediate medical attention
    
    If the patient wants to book an appointment after your advice, hand off to the Appointment Agent using to_appointment tool.
    
    IMPORTANT: Respond directly to the patient's health concerns. Do NOT announce that you received a handoff.
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
    prompt="""You are a Billing Agent. When you receive a patient with billing questions, immediately help them with their billing and insurance concerns.
    
    Your responsibilities:
    - Retrieve billing information using get_billing_info tool
    - Answer questions about invoices and charges
    - Help with insurance-related queries
    - Explain payment options and billing procedures
    
    IMPORTANT: Respond directly to the patient's billing question. Do NOT announce that you received a handoff.
    
    Routing rules:
    - Medical symptoms or health concerns -> Use to_clinical tool
    - Appointment booking, scheduling, or rescheduling -> Use to_appointment tool
    """,
    name="Billing"
)

# List of agents for create_swarm
agents = [triage_agent, appointment_agent, clinical_agent, billing_agent]
