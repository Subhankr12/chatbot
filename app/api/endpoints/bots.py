from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models.database import get_db
from app.models.models import Organization, Bot, BotStatus
from app.api.schemas import (
    BotCreate, BotUpdate, Bot as BotSchema, SuccessResponse,
    TrainingRequest, TrainingResponse
)
from app.api.auth import get_current_org, validate_bot_access
from app.services.chatbot_service import ChatbotService
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/bots",
    response_model=List[BotSchema],
    summary="List bots",
    description="Get all bots for the authenticated organization"
)
async def list_bots(
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org)
):
    """
    List all bots belonging to the authenticated organization.
    """
    bots = db.query(Bot).filter(Bot.organization_id == organization.id).all()
    return bots


@router.post(
    "/bots",
    response_model=BotSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create bot",
    description="Create a new chatbot"
)
async def create_bot(
    bot_data: BotCreate,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org)
):
    """
    Create a new chatbot for the organization.
    """
    try:
        # Verify organization access
        if bot_data.organization_id != organization.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create bot for different organization"
            )
        
        # Create bot
        bot = Bot(
            name=bot_data.name,
            description=bot_data.description,
            organization_id=organization.id,
            default_response=bot_data.default_response,
            confidence_threshold=bot_data.confidence_threshold,
            language=bot_data.language,
            settings=bot_data.settings or {},
            status=BotStatus.INACTIVE  # Start as inactive until trained
        )
        
        db.add(bot)
        db.commit()
        db.refresh(bot)
        
        logger.info(f"Created bot {bot.id} for organization {organization.id}")
        return bot
        
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating bot"
        )


@router.get(
    "/bots/{bot_id}",
    response_model=BotSchema,
    summary="Get bot",
    description="Get a specific bot by ID"
)
async def get_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """
    Get details of a specific bot.
    """
    return bot


@router.put(
    "/bots/{bot_id}",
    response_model=BotSchema,
    summary="Update bot",
    description="Update a bot's configuration"
)
async def update_bot(
    bot_id: int,
    bot_data: BotUpdate,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """
    Update a bot's configuration.
    """
    try:
        # Update fields if provided
        update_data = bot_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(bot, field, value)
        
        db.commit()
        db.refresh(bot)
        
        logger.info(f"Updated bot {bot_id}")
        return bot
        
    except Exception as e:
        logger.error(f"Error updating bot {bot_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating bot"
        )


@router.delete(
    "/bots/{bot_id}",
    response_model=SuccessResponse,
    summary="Delete bot",
    description="Delete a bot (soft delete - marks as inactive)"
)
async def delete_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """
    Delete a bot (soft delete by marking as inactive).
    """
    try:
        bot.status = BotStatus.INACTIVE
        db.commit()
        
        logger.info(f"Deleted bot {bot_id}")
        return SuccessResponse(
            message=f"Bot {bot_id} deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting bot {bot_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting bot"
        )


@router.post(
    "/bots/{bot_id}/train",
    response_model=TrainingResponse,
    summary="Train bot",
    description="Train or retrain the bot with current training data"
)
async def train_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """
    Train the bot with current intents and training phrases.
    """
    try:
        # Set bot status to training
        bot.status = BotStatus.TRAINING
        db.commit()
        
        # Initialize chatbot service and train
        chatbot_service = ChatbotService(bot_id, db)
        metrics = chatbot_service.train_bot()
        
        return TrainingResponse(
            status="completed",
            metrics=metrics,
            message="Bot training completed successfully"
        )
        
    except ValueError as e:
        # Reset status on training error
        bot.status = BotStatus.INACTIVE
        db.commit()
        
        logger.error(f"Training error for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Reset status on training error
        bot.status = BotStatus.INACTIVE
        db.commit()
        
        logger.error(f"Error training bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error training bot"
        )


@router.get(
    "/bots/{bot_id}/status",
    response_model=dict,
    summary="Get bot status",
    description="Get the current status and health of the bot"
)
async def get_bot_status(
    bot_id: int,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_current_org),
    bot: Bot = Depends(validate_bot_access)
):
    """
    Get the current status and health information of the bot.
    """
    try:
        # Count intents and training phrases
        from app.models.models import Intent, TrainingPhrase
        
        intent_count = db.query(Intent).filter(
            Intent.bot_id == bot_id,
            Intent.is_active == True
        ).count()
        
        training_phrase_count = db.query(TrainingPhrase).join(Intent).filter(
            Intent.bot_id == bot_id,
            Intent.is_active == True
        ).count()
        
        # Check if model exists
        from app.nlp.intent_classifier import IntentClassifier
        classifier = IntentClassifier(bot_id)
        model_exists = classifier.load_model()
        
        return {
            "bot_id": bot_id,
            "status": bot.status.value,
            "name": bot.name,
            "intent_count": intent_count,
            "training_phrase_count": training_phrase_count,
            "model_trained": model_exists,
            "confidence_threshold": bot.confidence_threshold,
            "language": bot.language,
            "last_updated": bot.updated_at.isoformat() if bot.updated_at else None
        }
        
    except Exception as e:
        logger.error(f"Error getting bot status for {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving bot status"
        )