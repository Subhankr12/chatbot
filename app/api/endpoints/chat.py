from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models.database import get_db
from app.models.models import Organization, Bot
from app.api.schemas import ChatRequest, ChatResponse, ConversationHistory, SuccessResponse
from app.api.auth import get_current_org, validate_bot_access
from app.services.chatbot_service import ChatbotService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/bots/{bot_id}/chat",
    response_model=ChatResponse,
    summary="Send message to chatbot",
    description="Process a user message and get bot response"
)
async def chat_with_bot(
    bot_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """
    Send a message to the specified chatbot and get a response.
    
    The chatbot will:
    - Extract entities from the message
    - Classify the intent
    - Generate an appropriate response
    - Maintain conversation context
    """
    try:
        # Initialize chatbot service
        chatbot_service = ChatbotService(bot_id, db)
        
        # Process the message
        response = chatbot_service.process_message(
            message=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            context_override=request.context
        )
        
        return response.to_dict()
        
    except Exception as e:
        logger.error(f"Error in chat endpoint for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing chat request"
        )


@router.get(
    "/bots/{bot_id}/conversations/{session_id}/history",
    response_model=List[ConversationHistory],
    summary="Get conversation history",
    description="Retrieve the message history for a conversation session"
)
async def get_conversation_history(
    bot_id: int,
    session_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """
    Get the conversation history for a specific session.
    """
    try:
        chatbot_service = ChatbotService(bot_id, db)
        history = chatbot_service.get_conversation_history(session_id, limit)
        return history
        
    except Exception as e:
        logger.error(f"Error getting conversation history for bot {bot_id}, session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversation history"
        )


@router.post(
    "/bots/{bot_id}/conversations/{session_id}/end",
    response_model=SuccessResponse,
    summary="End conversation",
    description="Mark a conversation as ended"
)
async def end_conversation(
    bot_id: int,
    session_id: str,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """
    End an active conversation session.
    """
    try:
        chatbot_service = ChatbotService(bot_id, db)
        chatbot_service.end_conversation(session_id)
        
        return SuccessResponse(
            message=f"Conversation {session_id} ended successfully"
        )
        
    except Exception as e:
        logger.error(f"Error ending conversation for bot {bot_id}, session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error ending conversation"
        )