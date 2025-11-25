
import logging
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket, WebSocketDisconnect
from graph.swarm import graph
from agents.utils import show_graph, print_graph_ascii
import uuid
from langchain_core.messages import HumanMessage
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Healthcare Agent")

@app.on_event("startup")
async def startup_event():
    logger.info("="*50)
    logger.info("BACKEND STARTED - Healthcare Agent Swarm")
    logger.info(f"Graph loaded: {graph is not None}")
    logger.info("="*50)
    show_graph(graph, save_to_file='graph.png')

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
                
                # Log incoming message
                # with open("debug.log", "a") as f:
                #     f.write(f"INCOMING: {user_message}\n")

                print(f"WEBSOCKET: Starting graph execution...", flush=True)
                
                # Run the graph with streaming events
                async for event in graph.astream_events(
                    {"messages": [("user", user_message)]},
                    config=config,
                    version="v1"
                ):
                    kind = event["event"]
                    
                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if content:
                            # Send token to client (optional, if frontend supports it)
                            # await websocket.send_text(json.dumps({
                            #     "type": "token",
                            #     "content": content
                            # }))
                            pass
                            
                    elif kind == "on_chain_start":
                        node_name = event["name"]
                        if node_name in ["Triage", "Clinical", "Appointment", "Billing"]:
                            print(f"TRANSITION: Switched to agent {node_name}", flush=True)
                            with open("debug.log", "a") as f:
                                f.write(f"TRANSITION: {node_name}\n")
                            await websocket.send_text(json.dumps({
                                "type": "agent_event",
                                "agent": node_name
                            }))

                    elif kind == "on_tool_start":
                        tool_name = event["name"]
                        tool_input = event["data"].get("input")
                        print(f"TOOL START: {tool_name} input: {tool_input}", flush=True)
                        with open("debug.log", "a") as f:
                            f.write(f"TOOL START: {tool_name} input: {tool_input}\n")
                            
                    elif kind == "on_tool_end":
                        tool_name = event["name"]
                        tool_output = event["data"].get("output")
                        print(f"TOOL END: {tool_name} output: {tool_output}", flush=True)
                        with open("debug.log", "a") as f:
                            f.write(f"TOOL END: {tool_name} output: {tool_output}\n")

                    elif kind == "on_chain_end":
                        # Check for agent state updates or final response
                        pass

                # After streaming, get the final state to send the full response
                # This is a bit redundant if we stream, but ensures compatibility with current frontend
                snapshot = graph.get_state(config)
                if snapshot.values and "messages" in snapshot.values:
                    last_message = snapshot.values["messages"][-1]
                    if hasattr(last_message, "content"):
                         await websocket.send_text(last_message.content)
                         with open("debug.log", "a") as f:
                            f.write(f"RESPONSE: {last_message.content}\n")

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
