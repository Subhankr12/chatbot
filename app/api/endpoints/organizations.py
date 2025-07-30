from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models.database import get_db
from app.models.models import Organization
from app.api.schemas import (
    OrganizationCreate, OrganizationUpdate, Organization as OrganizationSchema,
    SuccessResponse
)
import uuid
import secrets
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"cb_{secrets.token_urlsafe(32)}"


@router.post(
    "/organizations",
    response_model=OrganizationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Create a new organization (admin only)"
)
async def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new organization with a unique API key.
    
    This endpoint is typically used for initial setup or by admin users.
    """
    try:
        # Check if organization name already exists
        existing_org = db.query(Organization).filter(
            Organization.name == org_data.name
        ).first()
        
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization '{org_data.name}' already exists"
            )
        
        # Generate unique API key
        api_key = generate_api_key()
        
        # Ensure API key is unique (very unlikely collision, but being safe)
        while db.query(Organization).filter(Organization.api_key == api_key).first():
            api_key = generate_api_key()
        
        organization = Organization(
            name=org_data.name,
            api_key=api_key
        )
        
        db.add(organization)
        db.commit()
        db.refresh(organization)
        
        logger.info(f"Created organization {organization.id}: {organization.name}")
        return organization
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating organization"
        )


@router.get(
    "/organizations",
    response_model=List[OrganizationSchema],
    summary="List organizations",
    description="List all organizations (admin only)"
)
async def list_organizations(
    db: Session = Depends(get_db)
):
    """
    List all organizations.
    
    This endpoint is typically restricted to admin users.
    """
    organizations = db.query(Organization).all()
    return organizations


@router.get(
    "/organizations/{org_id}",
    response_model=OrganizationSchema,
    summary="Get organization",
    description="Get organization details (admin only)"
)
async def get_organization(
    org_id: int,
    db: Session = Depends(get_db)
):
    """Get details of a specific organization."""
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return organization


@router.put(
    "/organizations/{org_id}",
    response_model=OrganizationSchema,
    summary="Update organization",
    description="Update organization details (admin only)"
)
async def update_organization(
    org_id: int,
    org_data: OrganizationUpdate,
    db: Session = Depends(get_db)
):
    """Update an organization."""
    try:
        organization = db.query(Organization).filter(Organization.id == org_id).first()
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Check for name conflicts if name is being updated
        if org_data.name and org_data.name != organization.name:
            existing_org = db.query(Organization).filter(
                Organization.name == org_data.name,
                Organization.id != org_id
            ).first()
            
            if existing_org:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Organization '{org_data.name}' already exists"
                )
        
        # Update fields
        update_data = org_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(organization, field, value)
        
        db.commit()
        db.refresh(organization)
        
        logger.info(f"Updated organization {org_id}")
        return organization
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization {org_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating organization"
        )


@router.post(
    "/organizations/{org_id}/regenerate-api-key",
    response_model=OrganizationSchema,
    summary="Regenerate API key",
    description="Generate a new API key for the organization (admin only)"
)
async def regenerate_api_key(
    org_id: int,
    db: Session = Depends(get_db)
):
    """
    Regenerate the API key for an organization.
    
    WARNING: This will invalidate the current API key immediately.
    """
    try:
        organization = db.query(Organization).filter(Organization.id == org_id).first()
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Generate new API key
        new_api_key = generate_api_key()
        
        # Ensure API key is unique
        while db.query(Organization).filter(Organization.api_key == new_api_key).first():
            new_api_key = generate_api_key()
        
        old_api_key = organization.api_key
        organization.api_key = new_api_key
        
        db.commit()
        db.refresh(organization)
        
        logger.info(f"Regenerated API key for organization {org_id}")
        logger.warning(f"Old API key {old_api_key[:10]}... is now invalid")
        
        return organization
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating API key for organization {org_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error regenerating API key"
        )


@router.delete(
    "/organizations/{org_id}",
    response_model=SuccessResponse,
    summary="Delete organization",
    description="Deactivate an organization (admin only)"
)
async def delete_organization(
    org_id: int,
    db: Session = Depends(get_db)
):
    """
    Deactivate an organization (soft delete).
    
    This will deactivate the organization and all its bots.
    """
    try:
        organization = db.query(Organization).filter(Organization.id == org_id).first()
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Soft delete by marking as inactive
        organization.is_active = False
        
        # Also deactivate all bots in the organization
        from app.models.models import Bot, BotStatus
        db.query(Bot).filter(Bot.organization_id == org_id).update(
            {Bot.status: BotStatus.INACTIVE}
        )
        
        db.commit()
        
        logger.info(f"Deactivated organization {org_id}")
        return SuccessResponse(
            message=f"Organization {org_id} deactivated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating organization {org_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deactivating organization"
        )