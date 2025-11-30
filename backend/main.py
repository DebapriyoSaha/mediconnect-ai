import io
import json
import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import (FastAPI, File, HTTPException, Request, UploadFile,
                     WebSocket, WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               StreamingResponse)
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agents.utils import print_graph_ascii, show_graph
from database import Appointment, Doctor, Patient, get_db
from graph.swarm import graph
from tools.calendar_tool import generate_ics_bytes
from tools.ticket_tool import generate_ticket_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="MediConnect AI - Healthcare Agent Swarm")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Use tempfile to get a valid temporary directory (works on Vercel/Lambda)
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
            
        return JSONResponse(content={"file_path": tmp_path, "url": f"/uploads/{file.filename}"})
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/calendar/{appointment_id}")
async def get_calendar(appointment_id: int):
    """
    Generates and returns the iCal (.ics) file on-the-fly.
    """
    db = next(get_db())
    try:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        doctor = db.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
        patient = db.query(Patient).filter(Patient.id == appt.patient_id).first()
        
        details = {
            "appointment_id": appt.id,
            "patient_name": patient.name if patient else "Unknown",
            "doctor_name": doctor.name if doctor else "Unknown",
            "date": appt.date,
            "time": appt.time
        }
        
        ics_bytes = generate_ics_bytes(details)
        if not ics_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate calendar file")
            
        return StreamingResponse(
            io.BytesIO(ics_bytes), 
            media_type="text/calendar",
            headers={"Content-Disposition": f"attachment; filename=reminder_{appointment_id}.ics"}
        )
    finally:
        db.close()

@app.get("/api/tickets/{appointment_id}")
async def get_ticket(appointment_id: int):
    """
    Generates and returns the appointment ticket PDF on-the-fly.
    """
    db = next(get_db())
    try:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        doctor = db.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
        patient = db.query(Patient).filter(Patient.id == appt.patient_id).first()
        
        details = {
            "appointment_id": appt.id,
            "patient_name": patient.name if patient else "Unknown",
            "doctor_name": doctor.name if doctor else "Unknown",
            "date": appt.date,
            "time": appt.time
        }
        
        pdf_bytes = generate_ticket_bytes(details)
        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate ticket")
            
        return StreamingResponse(
            io.BytesIO(pdf_bytes), 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=ticket_{appointment_id}.pdf"}
        )
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    logger.info("="*50)
    logger.info("BACKEND STARTED - Healthcare Agent Swarm")
    logger.info(f"Graph loaded: {graph is not None}")
    logger.info("="*50)
    # show_graph(graph, save_to_file='graph.png')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Serve Static Files ---
BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "static"

print(f"📁 Base directory: {BASE_DIR}")
print(f"📁 Frontend directory: {FRONTEND_DIR}")

# Check if frontend directory exists
if FRONTEND_DIR.exists():
    print("✅ Frontend directory found")
    # Mount static files (CSS, JS, images)
    if (FRONTEND_DIR / "assets").exists():
        app.mount(
            "/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets"
        )
        print("✅ Static assets mounted")
    else:
        print("⚠️ Assets directory not found")
else:
    print("⚠️ Frontend directory does not exist!")
    print("Please copy your built frontend to the 'static' directory")


@app.get("/favicon.svg")
async def favicon():
    if (FRONTEND_DIR / "favicon.svg").exists():
        return FileResponse(FRONTEND_DIR / "favicon.svg", media_type="image/svg+xml")
    return {"error": "Favicon not found"}


@app.get("/")
async def root():
    """
    Serve the React app at the root path.
    """
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
        return FileResponse(FRONTEND_DIR / "index.html")
    else:
        return {
            "message": "🤖 IITM Chatbot API",
            "status": "running",
            "docs": "/docs",
            "health": "/api/health",
            "chat": "/api/chat",
            "note": "Frontend not available - API only mode",
        }

@app.get("/test")
async def test():
    try:
        logger.info("Test endpoint called, graph loaded successfully")
        return {"status": "ok", "graph_loaded": graph is not None}
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/graph")
async def get_graph():
    """Return the swarm graph structure for visualization"""
    try:
        # Define the graph structure
        nodes = [
            {"id": "Triage", "label": "Triage Agent", "role": "Routes patients to specialists", "color": "#3B82F6"},
            {"id": "Clinical", "label": "Clinical Agent", "role": "Medical advice & symptoms", "color": "#10B981"},
            {"id": "Appointment", "label": "Appointment Agent", "role": "Scheduling & booking", "color": "#8B5CF6"},
            {"id": "Billing", "label": "Billing Agent", "role": "Invoices & insurance", "color": "#F59E0B"}
        ]
        
        # Define handoff connections (edges)
        edges = [
            {"source": "Triage", "target": "Clinical", "label": "Medical symptoms"},
            {"source": "Triage", "target": "Appointment", "label": "Booking/scheduling"},
            {"source": "Triage", "target": "Billing", "label": "Billing questions"},
            {"source": "Clinical", "target": "Appointment", "label": "Book appointment"},
            {"source": "Appointment", "target": "Clinical", "label": "Medical questions"},
            {"source": "Billing", "target": "Triage", "label": "Other needs"},
            {"source": "Clinical", "target": "Billing", "label": "Billing inquiry"},
            {"source": "Billing", "target": "Clinical", "label": "Medical check"},
            {"source": "Appointment", "target": "Billing", "label": "Payment due"},
            {"source": "Billing", "target": "Appointment", "label": "Schedule follow-up"}
        ]
        
        return {"nodes": nodes, "edges": edges, "default_agent": "Triage"}
    except Exception as e:
        logger.error(f"Error in graph endpoint: {e}")
        return {"status": "error", "message": str(e)}

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Prepare input with location context if available
    input_data = {"messages": [("user", request.message)]}
    if request.latitude and request.longitude:
        # We can inject location into the message or state. 
        # For simplicity, let's append it to the message content for the LLM to see directly,
        # OR better, pass it as a separate state key if the graph supports it.
        # Given the current graph structure, appending to message is safest/easiest 
        # without changing state schema everywhere.
        # But wait, the frontend ALREADY appends it to the message string!
        # "System: User Location - Lat: ..."
        # So we actually don't need to do anything extra here if the frontend does it.
        # However, passing it explicitly allows tools to use it directly if we parse it.
        # Let's just rely on the frontend message string for now as it's already implemented there.
        pass

    async def event_generator():
        # Yield thread_id first so client knows it
        yield json.dumps({"type": "thread_id", "thread_id": thread_id}) + "\n"
        
        try:
            async for event in graph.astream_events(
                {"messages": [("user", request.message)]},
                config=config,
                version="v1"
            ):
                kind = event["event"]
                
                if kind == "on_chain_start":
                    node_name = event["name"]
                    if node_name in ["Triage", "Clinical", "Appointment", "Billing"]:
                        print(f"TRANSITION: Switched to agent {node_name}", flush=True)
                        yield json.dumps({
                            "type": "agent_event",
                            "agent": node_name
                        }) + "\n"

                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input")
                    print(f"TOOL START: {tool_name}", flush=True)
                    # Optional: yield tool events if frontend needs them

                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield json.dumps({"type": "token", "content": chunk.content}) + "\n"

            # After streaming, get the final state to send the full response
            # We still send the final message event to ensure consistency or close the stream properly
            # But the frontend should rely on tokens for the main display.
            # Actually, if we stream tokens, we don't strictly need the final message, 
            # but it's good for "done" state if needed.
            # For now, let's keep it but maybe the frontend ignores it if it built the message from tokens?
            # Or we just rely on tokens.
            pass
                     
        except Exception as e:
            logger.error(f"Error during graph execution: {e}", exc_info=True)
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    print("="*80, flush=True)
    print("WEBSOCKET: New connection attempt", flush=True)
    print("="*80, flush=True)
    
    await websocket.accept()
    print("WEBSOCKET: Connection accepted!", flush=True)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"WEBSOCKET: Session created with thread_id: {thread_id}", flush=True)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            print("="*80, flush=True)
            print(f"WEBSOCKET: Received message: '{data}'", flush=True)
            print("="*80, flush=True)
            
            try:
                message = json.loads(data)
                user_message = message.get("content", "")
                
                print(f"WEBSOCKET: Starting graph execution...", flush=True)
                
                # Run the graph with streaming events
                async for event in graph.astream_events(
                    {"messages": [("user", user_message)]},
                    config=config,
                    version="v1"
                ):
                    kind = event["event"]
                    
                    if kind == "on_chain_start":
                        node_name = event["name"]
                        if node_name in ["Triage", "Clinical", "Appointment", "Billing"]:
                            print(f"TRANSITION: Switched to agent {node_name}", flush=True)
                            await websocket.send_text(json.dumps({
                                "type": "agent_event",
                                "agent": node_name
                            }))

                    elif kind == "on_chain_end":
                        pass
                    
                # After streaming, get the final state to send the full response
                snapshot = graph.get_state(config)
                if snapshot.values and "messages" in snapshot.values:
                    last_message = snapshot.values["messages"][-1]
                    if hasattr(last_message, "content"):
                         await websocket.send_text(last_message.content)

                print("WEBSOCKET: Graph execution completed", flush=True)
                
            except Exception as e:
                print(f"WEBSOCKET ERROR during graph execution: {e}", flush=True)
                logger.error(f"Error during graph execution: {e}", exc_info=True)
                await websocket.send_text(f"Error: {str(e)}")

    except WebSocketDisconnect:
        print("WEBSOCKET: Client disconnected", flush=True)
    except Exception as e:
        print(f"WEBSOCKET ERROR: {e}", flush=True)
        logger.error(f"WebSocket error: {e}", exc_info=True)
