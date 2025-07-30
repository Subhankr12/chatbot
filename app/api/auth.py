from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Organization
from typing import Optional
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


class APIKeyAuth:
    """API Key authentication for organizations"""
    
    def __init__(self):
        pass
    
    async def __call__(
        self, 
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
    ) -> Organization:
        """Validate API key and return organization"""
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials"
            )
        
        api_key = credentials.credentials
        
        # Query organization by API key
        organization = db.query(Organization).filter(
            Organization.api_key == api_key,
            Organization.is_active == True
        ).first()
        
        if not organization:
            logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        return organization


# Create instance for dependency injection
get_current_org = APIKeyAuth()


def get_organization_bots(
    organization: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """Get all bots for the authenticated organization"""
    from app.models.models import Bot
    return db.query(Bot).filter(Bot.organization_id == organization.id).all()


def validate_bot_access(
    bot_id: int,
    organization: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """Validate that the organization has access to the specified bot"""
    from app.models.models import Bot
    
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.organization_id == organization.id
    ).first()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot {bot_id} not found or access denied"
        )
    
    return bot


# Optional authentication for public endpoints
class OptionalAPIKeyAuth:
    """Optional API Key authentication"""
    
    async def __call__(
        self, 
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db)
    ) -> Optional[Organization]:
        """Optionally validate API key and return organization"""
        
        if not credentials:
            return None
        
        try:
            api_key = credentials.credentials
            organization = db.query(Organization).filter(
                Organization.api_key == api_key,
                Organization.is_active == True
            ).first()
            return organization
        except Exception:
            return None


get_optional_org = OptionalAPIKeyAuth()