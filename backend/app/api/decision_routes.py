from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union
from app.agents.decision_agent import orchestrate_session
from app.db.base import AsyncSessionLocal

router = APIRouter()

class ChatRequest(BaseModel):
    user_message: str
    session_ulid: Optional[str] = None
    source: Optional[str] = None
    final_data: Optional[Dict[str, Any]] = None
    current_state: Optional[Dict[str, Any]] = {}

class ChatResponse(BaseModel):
    ui_action: str
    agent_message: str
    data_required: Optional[List[Union[str, Dict[str, Any]]]] = []
    session_ulid: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    current_state: Optional[Dict[str, Any]] = None

@router.post("/v1/orchestrator/chat", response_model=ChatResponse)
async def chat_orchestrator(request: ChatRequest):
    """
    Master Account Opening Orchestrator
    Acts as the dynamic entrypoint for the React Frontend Chat UI.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await orchestrate_session(
                message=request.user_message,
                session_ulid=request.session_ulid,
                current_state=request.current_state,
                source=request.source,
                final_data=request.final_data,
                db=db
            )
            return result
    except Exception as e:
        import logging
        logging.error(f"Orchestration Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
