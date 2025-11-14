"""
Proof of Concept Backend for Paper Companion Web
Minimal FastAPI server to validate PDF → Claude → UI flow
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
import base64
import os
from typing import Optional, List, Dict
import json
from datetime import datetime

app = FastAPI()

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (for PoC - will move to SQLite later)
sessions: Dict[str, dict] = {}

class QueryRequest(BaseModel):
    session_id: str
    query: str
    highlighted_text: Optional[str] = None
    page: Optional[int] = None

class FlagRequest(BaseModel):
    session_id: str
    exchange_id: int

@app.post("/session/new")
async def create_session(file: UploadFile = File(...)):
    """
    Create a new session by uploading a PDF.
    Loads the full PDF into Claude's context.
    """
    try:
        # Read PDF content
        pdf_content = await file.read()
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Create session ID
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize Claude client
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        # Initial message to Claude with full PDF
        initial_prompt = """I've uploaded a scientific paper. Please:

1. Provide a brief overview (2-3 sentences)
2. Identify the main research question
3. Note key methods used
4. Highlight the primary findings

Keep this initial analysis concise - we'll dive deeper through conversation."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": initial_prompt
                        }
                    ]
                }
            ]
        )
        
        initial_analysis = message.content[0].text
        
        # Store session
        sessions[session_id] = {
            "created": datetime.now().isoformat(),
            "filename": file.filename,
            "pdf_base64": pdf_base64,
            "conversation": [
                {
                    "id": 0,
                    "role": "user",
                    "content": initial_prompt,
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "id": 1,
                    "role": "assistant",
                    "content": initial_analysis,
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "flags": [],
            "highlights": []
        }
        
        return {
            "session_id": session_id,
            "filename": file.filename,
            "initial_analysis": initial_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/query")
async def query_paper(request: QueryRequest):
    """
    Ask a question about the paper.
    Uses existing Claude conversation context.
    """
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        # Build conversation history for Claude
        messages = []
        
        # First message includes the PDF
        first_user_msg = {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": session["pdf_base64"]
                    }
                },
                {
                    "type": "text",
                    "text": session["conversation"][0]["content"]
                }
            ]
        }
        messages.append(first_user_msg)
        
        # Add rest of conversation history (skip first exchange, already added)
        for msg in session["conversation"][1:]:
            if msg["role"] == "assistant":
                messages.append({
                    "role": "assistant",
                    "content": msg["content"]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": msg["content"]
                })
        
        # Add new query
        query_text = request.query
        if request.highlighted_text:
            query_text = f"Regarding this highlighted text: \"{request.highlighted_text}\"\n\n{request.query}"
            if request.page:
                query_text += f"\n(from page {request.page})"
        
        messages.append({
            "role": "user",
            "content": query_text
        })
        
        # Get Claude's response
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=messages
        )
        
        response_text = message.content[0].text
        
        # Store in conversation history
        exchange_id = len(session["conversation"])
        session["conversation"].append({
            "id": exchange_id,
            "role": "user",
            "content": query_text,
            "highlighted_text": request.highlighted_text,
            "page": request.page,
            "timestamp": datetime.now().isoformat()
        })
        session["conversation"].append({
            "id": exchange_id + 1,
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        # Store highlight if present
        if request.highlighted_text:
            session["highlights"].append({
                "text": request.highlighted_text,
                "page": request.page,
                "exchange_id": exchange_id,
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "exchange_id": exchange_id,
            "response": response_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/flag")
async def flag_exchange(request: FlagRequest):
    """
    Flag an exchange as important.
    """
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    
    # Toggle flag
    if request.exchange_id in session["flags"]:
        session["flags"].remove(request.exchange_id)
        flagged = False
    else:
        session["flags"].append(request.exchange_id)
        flagged = True
    
    return {"flagged": flagged}

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Retrieve session data (for restoring "pick up where left off").
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Return everything except the base64 PDF (too large)
    return {
        "session_id": session_id,
        "filename": session["filename"],
        "created": session["created"],
        "conversation": session["conversation"],
        "flags": session["flags"],
        "highlights": session["highlights"]
    }

@app.get("/sessions")
async def list_sessions():
    """
    List all sessions (for "pick up where left off" UI).
    """
    return [
        {
            "session_id": sid,
            "filename": session["filename"],
            "created": session["created"],
            "num_exchanges": len([m for m in session["conversation"] if m["role"] == "user"]),
            "num_flags": len(session["flags"])
        }
        for sid, session in sessions.items()
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
