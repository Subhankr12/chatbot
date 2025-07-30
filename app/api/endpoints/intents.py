from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models.database import get_db
from app.models.models import Organization, Bot, Intent, TrainingPhrase, Response
from app.api.schemas import (
    IntentCreate, IntentUpdate, Intent as IntentSchema,
    TrainingPhraseCreate, TrainingPhraseUpdate, TrainingPhrase as TrainingPhraseSchema,
    ResponseCreate, ResponseUpdate, Response as ResponseSchema,
    SuccessResponse, BulkIntentCreate
)
from app.api.auth import get_current_org, validate_bot_access
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Intent endpoints
@router.get(
    "/bots/{bot_id}/intents",
    response_model=List[IntentSchema],
    summary="List intents",
    description="Get all intents for a bot"
)
async def list_intents(
    bot_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """List all intents for the specified bot."""
    intents = db.query(Intent).filter(Intent.bot_id == bot_id).all()
    return intents


@router.post(
    "/bots/{bot_id}/intents",
    response_model=IntentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create intent",
    description="Create a new intent for the bot"
)
async def create_intent(
    bot_id: int,
    intent_data: IntentCreate,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """Create a new intent for the bot."""
    try:
        # Verify bot_id matches
        if intent_data.bot_id != bot_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bot ID mismatch"
            )
        
        # Check if intent name already exists for this bot
        existing_intent = db.query(Intent).filter(
            Intent.name == intent_data.name,
            Intent.bot_id == bot_id
        ).first()
        
        if existing_intent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Intent '{intent_data.name}' already exists for this bot"
            )
        
        intent = Intent(
            name=intent_data.name,
            description=intent_data.description,
            bot_id=bot_id,
            priority=intent_data.priority
        )
        
        db.add(intent)
        db.commit()
        db.refresh(intent)
        
        logger.info(f"Created intent {intent.id} for bot {bot_id}")
        return intent
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating intent: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating intent"
        )


@router.get(
    "/bots/{bot_id}/intents/{intent_id}",
    response_model=IntentSchema,
    summary="Get intent",
    description="Get a specific intent by ID"
)
async def get_intent(
    bot_id: int,
    intent_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """Get a specific intent."""
    intent = db.query(Intent).filter(
        Intent.id == intent_id,
        Intent.bot_id == bot_id
    ).first()
    
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intent not found"
        )
    
    return intent


@router.put(
    "/bots/{bot_id}/intents/{intent_id}",
    response_model=IntentSchema,
    summary="Update intent",
    description="Update an intent"
)
async def update_intent(
    bot_id: int,
    intent_id: int,
    intent_data: IntentUpdate,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """Update an intent."""
    try:
        intent = db.query(Intent).filter(
            Intent.id == intent_id,
            Intent.bot_id == bot_id
        ).first()
        
        if not intent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intent not found"
            )
        
        # Check for name conflicts if name is being updated
        if intent_data.name and intent_data.name != intent.name:
            existing_intent = db.query(Intent).filter(
                Intent.name == intent_data.name,
                Intent.bot_id == bot_id,
                Intent.id != intent_id
            ).first()
            
            if existing_intent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Intent '{intent_data.name}' already exists for this bot"
                )
        
        # Update fields
        update_data = intent_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(intent, field, value)
        
        db.commit()
        db.refresh(intent)
        
        logger.info(f"Updated intent {intent_id}")
        return intent
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating intent {intent_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating intent"
        )


@router.delete(
    "/bots/{bot_id}/intents/{intent_id}",
    response_model=SuccessResponse,
    summary="Delete intent",
    description="Delete an intent and all its training phrases and responses"
)
async def delete_intent(
    bot_id: int,
    intent_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """Delete an intent and all its associated data."""
    try:
        intent = db.query(Intent).filter(
            Intent.id == intent_id,
            Intent.bot_id == bot_id
        ).first()
        
        if not intent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intent not found"
            )
        
        # Delete associated training phrases and responses (cascade)
        db.delete(intent)
        db.commit()
        
        logger.info(f"Deleted intent {intent_id}")
        return SuccessResponse(
            message=f"Intent {intent_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting intent {intent_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting intent"
        )


# Training Phrases endpoints
@router.get(
    "/bots/{bot_id}/intents/{intent_id}/training-phrases",
    response_model=List[TrainingPhraseSchema],
    summary="List training phrases",
    description="Get all training phrases for an intent"
)
async def list_training_phrases(
    bot_id: int,
    intent_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """List all training phrases for an intent."""
    # Verify intent exists and belongs to bot
    intent = db.query(Intent).filter(
        Intent.id == intent_id,
        Intent.bot_id == bot_id
    ).first()
    
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intent not found"
        )
    
    training_phrases = db.query(TrainingPhrase).filter(
        TrainingPhrase.intent_id == intent_id
    ).all()
    
    return training_phrases


@router.post(
    "/bots/{bot_id}/intents/{intent_id}/training-phrases",
    response_model=TrainingPhraseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create training phrase",
    description="Add a new training phrase to an intent"
)
async def create_training_phrase(
    bot_id: int,
    intent_id: int,
    phrase_data: TrainingPhraseCreate,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """Create a new training phrase for an intent."""
    try:
        # Verify intent exists and belongs to bot
        intent = db.query(Intent).filter(
            Intent.id == intent_id,
            Intent.bot_id == bot_id
        ).first()
        
        if not intent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intent not found"
            )
        
        # Verify intent_id matches
        if phrase_data.intent_id != intent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Intent ID mismatch"
            )
        
        training_phrase = TrainingPhrase(
            text=phrase_data.text,
            intent_id=intent_id,
            entities_data=phrase_data.entities_data
        )
        
        db.add(training_phrase)
        db.commit()
        db.refresh(training_phrase)
        
        logger.info(f"Created training phrase {training_phrase.id} for intent {intent_id}")
        return training_phrase
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating training phrase: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating training phrase"
        )


@router.delete(
    "/bots/{bot_id}/intents/{intent_id}/training-phrases/{phrase_id}",
    response_model=SuccessResponse,
    summary="Delete training phrase",
    description="Delete a training phrase"
)
async def delete_training_phrase(
    bot_id: int,
    intent_id: int,
    phrase_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """Delete a training phrase."""
    try:
        training_phrase = db.query(TrainingPhrase).filter(
            TrainingPhrase.id == phrase_id,
            TrainingPhrase.intent_id == intent_id
        ).first()
        
        if not training_phrase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training phrase not found"
            )
        
        db.delete(training_phrase)
        db.commit()
        
        logger.info(f"Deleted training phrase {phrase_id}")
        return SuccessResponse(
            message=f"Training phrase {phrase_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting training phrase {phrase_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting training phrase"
        )


# Response endpoints
@router.get(
    "/bots/{bot_id}/intents/{intent_id}/responses",
    response_model=List[ResponseSchema],
    summary="List responses",
    description="Get all responses for an intent"
)
async def list_responses(
    bot_id: int,
    intent_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """List all responses for an intent."""
    # Verify intent exists and belongs to bot
    intent = db.query(Intent).filter(
        Intent.id == intent_id,
        Intent.bot_id == bot_id
    ).first()
    
    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intent not found"
        )
    
    responses = db.query(Response).filter(
        Response.intent_id == intent_id
    ).all()
    
    return responses


@router.post(
    "/bots/{bot_id}/intents/{intent_id}/responses",
    response_model=ResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create response",
    description="Add a new response to an intent"
)
async def create_response(
    bot_id: int,
    intent_id: int,
    response_data: ResponseCreate,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """Create a new response for an intent."""
    try:
        # Verify intent exists and belongs to bot
        intent = db.query(Intent).filter(
            Intent.id == intent_id,
            Intent.bot_id == bot_id
        ).first()
        
        if not intent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intent not found"
            )
        
        # Verify intent_id matches
        if response_data.intent_id != intent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Intent ID mismatch"
            )
        
        response = Response(
            text=response_data.text,
            intent_id=intent_id,
            response_type=response_data.response_type,
            metadata=response_data.metadata,
            priority=response_data.priority
        )
        
        db.add(response)
        db.commit()
        db.refresh(response)
        
        logger.info(f"Created response {response.id} for intent {intent_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating response: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating response"
        )