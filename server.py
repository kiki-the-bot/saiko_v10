import sys
import os
import asyncio
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # 
from fastapi.responses import FileResponse
import queue

# FIX PATH
sys.path.append("/app")

# IMPORT THE REAL BRAIN
from src.bridge import BrainBridge  
from src.data.ammo import ChatMsg   

app = FastAPI(title="Saiko API", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (Safe for demo)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
saiko_bot = None

class UserRequest(BaseModel):
    prompt: str
    role: str = "user"

@app.on_event("startup")
async def startup_event():
    global saiko_bot
    print("🦍 WAKING UP SAIKO...")
    # Initialize the brain (This loads models, might take 10s)
    saiko_bot = BrainBridge() 
    print("✅ SAIKO IS ONLINE.")

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

@app.post("/chat")
async def chat_endpoint(request: UserRequest):
    global saiko_bot
    if saiko_bot is None: 
        raise HTTPException(status_code=500, detail="Brain Dead (Initializing...)")
    
    my_mailbox = queue.Queue()



    # 1. Send Message
    msg = ChatMsg(role=request.role, content=request.prompt, reply_q=my_mailbox)
    saiko_bot.send_chat_msg(msg)
    
    
    try:
        # This waits exactly as long as needed. 0.001s latency.
        # We keep a timeout just to prevent hanging forever if the brain crashes.
        response_data = await asyncio.to_thread(my_mailbox.get, timeout=120) 
        
        return {
            "response": response_data.get("text", ""), 
            "scenario": response_data.get("scenario", "UNKNOWN"),
            "status": "success"
        }
        
    except queue.Empty:
        return {"error": "Timeout: Brain took too long (no response in 120s)."}