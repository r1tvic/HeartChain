"""
Campaign Routes for HeartChain.

Handles campaign creation, listing, and status management.
Implements encryption for sensitive data before storage.
"""
from fastapi import APIRouter, Body, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import ReturnDocument

from models.campaign import (
    CampaignType,
    CampaignStatus,
    PriorityLevel,
    IndividualCampaignCreate,
    CharityCampaignCreate,
    CampaignPublicResponse,
    CampaignInDB,
    CampaignDocument,
    INDIVIDUAL_ENCRYPTED_FIELDS,
    CHARITY_ENCRYPTED_FIELDS,
)
from core.encryption import get_encryption, EncryptionError
from database import db
import os

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def get_collection():
    """Helper to get the campaigns collection."""
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["campaigns"]


def convert_db_to_public_response(campaign: dict) -> dict:
    """
    Convert a database campaign document to public response format.
    Strips all encrypted fields and exposes only public data.
    """
    return {
        "_id": campaign.get("_id"),
        "campaign_type": campaign.get("campaign_type"),
        "title": campaign.get("title"),
        "description": campaign.get("description"),
        "target_amount": campaign.get("target_amount"),
        "raised_amount": campaign.get("raised_amount", 0.0),
        "duration_days": campaign.get("duration_days"),
        "category": campaign.get("category"),
        "priority": campaign.get("priority"),
        "status": campaign.get("status"),
        "image_url": campaign.get("image_url"),
        "organization_name": campaign.get("organization_name"),  # Public for charity
        "documents_count": len(campaign.get("documents", [])),
        "created_at": campaign.get("created_at"),
        "end_date": campaign.get("end_date"),
        "blockchain_tx_hash": campaign.get("blockchain_tx_hash"),
    }


# ============== CREATE ENDPOINTS ==============

@router.post(
    "/individual",
    response_model=CampaignPublicResponse,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False,
    summary="Create Individual Campaign",
    description="Create a personal/individual campaign (medical emergencies, personal crises). Sensitive data is encrypted before storage."
)
async def create_individual_campaign(campaign: IndividualCampaignCreate = Body(...)):
    """
    Create a new Individual/Personal campaign.
    
    - Encrypts sensitive fields (beneficiary_name, phone_number, residential_address, verification_notes)
    - Sets initial status to DRAFT
    - Campaign type is immutably set to INDIVIDUAL
    """
    try:
        encryption = get_encryption()
    except EncryptionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encryption configuration error: {str(e)}"
        )
    
    # Calculate end date
    end_date = datetime.now() + timedelta(days=campaign.duration_days)
    
    # Build campaign document
    campaign_dict = {
        "campaign_type": CampaignType.INDIVIDUAL.value,
        
        # Public fields (plain text)
        "title": campaign.title,
        "description": campaign.description,
        "target_amount": campaign.target_amount,
        "raised_amount": 0.0,
        "duration_days": campaign.duration_days,
        "category": campaign.category,
        "priority": campaign.priority.value,
        "status": CampaignStatus.DRAFT.value,
        "image_url": campaign.image_url,
        
        # Encrypted fields
        "beneficiary_name": encryption.encrypt(campaign.beneficiary_name),
        "phone_number": encryption.encrypt(campaign.phone_number),
        "residential_address": encryption.encrypt(campaign.residential_address),
        "verification_notes": encryption.encrypt(campaign.verification_notes) if campaign.verification_notes else None,
        
        # Documents (empty initially, uploaded separately)
        "documents": [],
        
        # Timestamps
        "created_at": datetime.now(),
        "end_date": end_date,
    }
    
    # Insert into database
    result = await get_collection().insert_one(campaign_dict)
    created_campaign = await get_collection().find_one({"_id": result.inserted_id})
    
    # Return public response (no sensitive data)
    return convert_db_to_public_response(created_campaign)


@router.post(
    "/charity",
    response_model=CampaignPublicResponse,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False,
    summary="Create Charity Campaign",
    description="Create a charity/organization campaign (NGOs, registered institutions). Sensitive data is encrypted before storage."
)
async def create_charity_campaign(campaign: CharityCampaignCreate = Body(...)):
    """
    Create a new Charity/Organization campaign.
    
    - Encrypts sensitive fields (contact_person_name, contact_phone_number, official_address, verification_notes)
    - Organization name is public (not encrypted)
    - Sets initial status to DRAFT
    - Campaign type is immutably set to CHARITY
    """
    try:
        encryption = get_encryption()
    except EncryptionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encryption configuration error: {str(e)}"
        )
    
    # Calculate end date
    end_date = datetime.now() + timedelta(days=campaign.duration_days)
    
    # Build campaign document
    campaign_dict = {
        "campaign_type": CampaignType.CHARITY.value,
        
        # Public fields (plain text)
        "title": campaign.title,
        "description": campaign.description,
        "target_amount": campaign.target_amount,
        "raised_amount": 0.0,
        "duration_days": campaign.duration_days,
        "category": campaign.category,
        "priority": campaign.priority.value,
        "status": CampaignStatus.DRAFT.value,
        "image_url": campaign.image_url,
        "organization_name": campaign.organization_name,  # Public!
        
        # Encrypted fields
        "contact_person_name": encryption.encrypt(campaign.contact_person_name),
        "contact_phone_number": encryption.encrypt(campaign.contact_phone_number),
        "official_address": encryption.encrypt(campaign.official_address),
        "verification_notes": encryption.encrypt(campaign.verification_notes) if campaign.verification_notes else None,
        
        # Documents (empty initially, uploaded separately)
        "documents": [],
        
        # Timestamps
        "created_at": datetime.now(),
        "end_date": end_date,
    }
    
    # Insert into database
    result = await get_collection().insert_one(campaign_dict)
    created_campaign = await get_collection().find_one({"_id": result.inserted_id})
    
    # Return public response (no sensitive data)
    return convert_db_to_public_response(created_campaign)


# ============== LIST/READ ENDPOINTS ==============

@router.get(
    "/",
    response_model=List[CampaignPublicResponse],
    response_model_by_alias=False,
    summary="List All Active Campaigns",
    description="Fetch all ACTIVE campaigns sorted by priority. Urgent campaigns first, then normal."
)
async def list_campaigns(
    campaign_type: Optional[CampaignType] = Query(None, description="Filter by campaign type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of campaigns to return")
):
    """
    List all active campaigns (public view).
    
    - Only shows ACTIVE campaigns (approved and live)
    - Sorted by priority (urgent first) then by creation date
    - No sensitive data exposed
    """
    query = {"status": CampaignStatus.ACTIVE.value}
    
    if campaign_type:
        query["campaign_type"] = campaign_type.value
    if category:
        query["category"] = category
    
    campaigns = await get_collection().find(query).sort([
        ("priority", -1),  # urgent before normal
        ("created_at", -1)  # newest first
    ]).limit(limit).to_list(limit)
    
    return [convert_db_to_public_response(c) for c in campaigns]


@router.get(
    "/{campaign_id}",
    response_model=CampaignPublicResponse,
    response_model_by_alias=False,
    summary="Get Campaign Details",
    description="Fetch public details of a single campaign by ID."
)
async def get_campaign(campaign_id: str):
    """
    Get a single campaign's public details.
    
    - Only returns public data
    - Works for any status (draft campaigns visible to creator only - TODO: add auth)
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return convert_db_to_public_response(campaign)


# ============== STATUS MANAGEMENT ENDPOINTS ==============

@router.post(
    "/{campaign_id}/submit",
    response_model=CampaignPublicResponse,
    response_model_by_alias=False,
    summary="Submit Campaign for Verification",
    description="Submit a DRAFT campaign for admin verification."
)
async def submit_for_verification(campaign_id: str):
    """
    Submit a campaign for verification.
    
    - Only DRAFT campaigns can be submitted
    - Changes status to PENDING_VERIFICATION
    - Requires at least one supporting document (TODO: enforce)
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] != CampaignStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit campaign. Current status is '{campaign['status']}', must be 'draft'"
        )
    
    # Update status
    updated = await get_collection().find_one_and_update(
        {"_id": ObjectId(campaign_id)},
        {
            "$set": {
                "status": CampaignStatus.PENDING_VERIFICATION.value,
                "submitted_at": datetime.now()
            }
        },
        return_document=ReturnDocument.AFTER
    )
    
    return convert_db_to_public_response(updated)


@router.put(
    "/{campaign_id}/close",
    response_model=CampaignPublicResponse,
    response_model_by_alias=False,
    summary="Close Campaign",
    description="Close an ACTIVE campaign (goal reached or cancelled)."
)
async def close_campaign(campaign_id: str, reason: Optional[str] = Query(None)):
    """
    Close an active campaign.
    
    - Only ACTIVE campaigns can be closed
    - Used when goal is reached or campaign is cancelled
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] != CampaignStatus.ACTIVE.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot close campaign. Current status is '{campaign['status']}', must be 'active'"
        )
    
    updated = await get_collection().find_one_and_update(
        {"_id": ObjectId(campaign_id)},
        {
            "$set": {
                "status": CampaignStatus.CLOSED.value,
                "closed_at": datetime.now(),
                "close_reason": reason
            }
        },
        return_document=ReturnDocument.AFTER
    )
    
    return convert_db_to_public_response(updated)


# ============== BLOCKCHAIN INTEGRATION ==============

@router.put(
    "/{campaign_id}/blockchain-tx",
    response_model=CampaignPublicResponse,
    response_model_by_alias=False,
    summary="Record Blockchain Transaction",
    description="Record the blockchain transaction hash for a campaign."
)
async def record_blockchain_tx(
    campaign_id: str,
    tx_hash: str = Query(..., description="Blockchain transaction hash")
):
    """
    Record blockchain transaction hash for a campaign.
    
    - Public/transparent record of on-chain activity
    - Not encrypted (for transparency)
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    updated = await get_collection().find_one_and_update(
        {"_id": ObjectId(campaign_id)},
        {"$set": {"blockchain_tx_hash": tx_hash}},
        return_document=ReturnDocument.AFTER
    )
    
    return convert_db_to_public_response(updated)


# ============== RAISED AMOUNT UPDATE ==============

@router.put(
    "/{campaign_id}/update-raised",
    response_model=CampaignPublicResponse,
    response_model_by_alias=False,
    summary="Update Raised Amount",
    description="Update the total raised amount for a campaign (called when donations are received)."
)
async def update_raised_amount(
    campaign_id: str,
    amount: float = Query(..., gt=0, description="Amount to add to raised total")
):
    """
    Update the raised amount for a campaign.
    
    - Increments the raised_amount field
    - Should be called when donations are confirmed on blockchain
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] != CampaignStatus.ACTIVE.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot update raised amount for non-active campaign"
        )
    
    updated = await get_collection().find_one_and_update(
        {"_id": ObjectId(campaign_id)},
        {"$inc": {"raised_amount": amount}},
        return_document=ReturnDocument.AFTER
    )
    
    return convert_db_to_public_response(updated)
