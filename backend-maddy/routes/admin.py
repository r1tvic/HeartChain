"""
Admin Routes for HeartChain.

Handles campaign verification, approval/rejection, and admin-only operations.
This is the ONLY place where encrypted data is decrypted.
"""
from fastapi import APIRouter, Body, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument

from models.campaign import (
    CampaignType,
    CampaignStatus,
    CampaignAdminResponse,
    CampaignApproval,
    INDIVIDUAL_ENCRYPTED_FIELDS,
    CHARITY_ENCRYPTED_FIELDS,
    ALL_ENCRYPTED_FIELDS,
)
from core.encryption import get_encryption, DecryptionError
from database import db
import os

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_campaigns_collection():
    """Helper to get the campaigns collection."""
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["campaigns"]


def get_admin_logs_collection():
    """Helper to get the admin logs collection."""
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["admin_logs"]


def decrypt_campaign_for_admin(campaign: dict) -> dict:
    """
    Decrypt all sensitive fields in a campaign document for admin viewing.
    
    Args:
        campaign: Raw campaign document from MongoDB
        
    Returns:
        Campaign with decrypted sensitive fields
    """
    encryption = get_encryption()
    result = campaign.copy()
    
    # Determine which fields to decrypt based on campaign type
    if campaign.get("campaign_type") == CampaignType.INDIVIDUAL.value:
        fields_to_decrypt = INDIVIDUAL_ENCRYPTED_FIELDS
    else:
        fields_to_decrypt = CHARITY_ENCRYPTED_FIELDS
    
    # Decrypt each field
    for field in fields_to_decrypt:
        if field in result and result[field] is not None:
            if isinstance(result[field], dict) and "nonce" in result[field]:
                try:
                    result[field] = encryption.decrypt(result[field])
                except DecryptionError as e:
                    result[field] = f"[DECRYPTION ERROR: {str(e)}]"
    
    return result


async def log_admin_action(
    admin_id: str,
    action: str,
    campaign_id: str,
    details: Optional[dict] = None
):
    """
    Log an admin action for audit trail.
    
    Args:
        admin_id: ID of the admin performing the action
        action: Type of action (approve, reject, view, etc.)
        campaign_id: ID of the affected campaign
        details: Additional details about the action
    """
    log_entry = {
        "admin_id": admin_id,
        "action": action,
        "campaign_id": campaign_id,
        "details": details or {},
        "timestamp": datetime.now(),
        "ip_address": None,  # TODO: Extract from request
    }
    
    await get_admin_logs_collection().insert_one(log_entry)


# ============== VERIFICATION QUEUE ==============

@router.get(
    "/campaigns/pending",
    response_model=List[CampaignAdminResponse],
    response_model_by_alias=False,
    summary="Get Pending Campaigns",
    description="Fetch all campaigns pending verification with decrypted sensitive data."
)
async def list_pending_campaigns(
    admin_id: str = Query(..., description="Admin user ID for logging"),
    campaign_type: Optional[CampaignType] = Query(None, description="Filter by campaign type"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List all campaigns pending verification.
    
    - Decrypts sensitive data for admin review
    - Logs the access for audit trail
    """
    query = {"status": CampaignStatus.PENDING_VERIFICATION.value}
    
    if campaign_type:
        query["campaign_type"] = campaign_type.value
    
    campaigns = await get_campaigns_collection().find(query).sort([
        ("submitted_at", 1)  # Oldest first (FIFO)
    ]).limit(limit).to_list(limit)
    
    # Decrypt all campaigns and log access
    decrypted_campaigns = []
    for campaign in campaigns:
        decrypted = decrypt_campaign_for_admin(campaign)
        decrypted_campaigns.append(decrypted)
        
        # Log that this campaign was viewed
        await log_admin_action(
            admin_id=admin_id,
            action="view_pending",
            campaign_id=str(campaign["_id"])
        )
    
    return decrypted_campaigns


@router.get(
    "/campaigns/{campaign_id}",
    response_model=CampaignAdminResponse,
    response_model_by_alias=False,
    summary="Get Campaign Details (Admin)",
    description="Fetch full campaign details with decrypted sensitive data."
)
async def get_campaign_admin(
    campaign_id: str,
    admin_id: str = Query(..., description="Admin user ID for logging")
):
    """
    Get full campaign details including decrypted sensitive data.
    
    - Only for admin use
    - Logs the access for audit trail
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_campaigns_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Decrypt and log access
    decrypted = decrypt_campaign_for_admin(campaign)
    
    await log_admin_action(
        admin_id=admin_id,
        action="view_details",
        campaign_id=campaign_id
    )
    
    return decrypted


# ============== APPROVAL/REJECTION ==============

@router.post(
    "/campaigns/{campaign_id}/approve",
    response_model=CampaignAdminResponse,
    response_model_by_alias=False,
    summary="Approve Campaign",
    description="Approve a pending campaign, making it ACTIVE."
)
async def approve_campaign(
    campaign_id: str,
    admin_id: str = Query(..., description="Admin user ID"),
    notes: Optional[str] = Query(None, description="Approval notes")
):
    """
    Approve a campaign that is pending verification.
    
    - Changes status from PENDING_VERIFICATION to APPROVED, then to ACTIVE
    - Records approval timestamp and admin ID
    - Logs the action
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_campaigns_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] != CampaignStatus.PENDING_VERIFICATION.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve campaign. Current status is '{campaign['status']}', must be 'pending_verification'"
        )
    
    # Update to ACTIVE (skipping APPROVED state for simplicity)
    updated = await get_campaigns_collection().find_one_and_update(
        {"_id": ObjectId(campaign_id)},
        {
            "$set": {
                "status": CampaignStatus.ACTIVE.value,
                "approved_at": datetime.now(),
                "approved_by": admin_id,
                "approval_notes": notes
            }
        },
        return_document=ReturnDocument.AFTER
    )
    
    # Log the approval
    await log_admin_action(
        admin_id=admin_id,
        action="approve",
        campaign_id=campaign_id,
        details={"notes": notes}
    )
    
    return decrypt_campaign_for_admin(updated)


@router.post(
    "/campaigns/{campaign_id}/reject",
    response_model=CampaignAdminResponse,
    response_model_by_alias=False,
    summary="Reject Campaign",
    description="Reject a pending campaign with a reason."
)
async def reject_campaign(
    campaign_id: str,
    admin_id: str = Query(..., description="Admin user ID"),
    reason: str = Query(..., min_length=10, description="Rejection reason (required)")
):
    """
    Reject a campaign that is pending verification.
    
    - Changes status to REJECTED
    - Records rejection reason
    - Logs the action
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_campaigns_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] != CampaignStatus.PENDING_VERIFICATION.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject campaign. Current status is '{campaign['status']}', must be 'pending_verification'"
        )
    
    # Update to REJECTED
    updated = await get_campaigns_collection().find_one_and_update(
        {"_id": ObjectId(campaign_id)},
        {
            "$set": {
                "status": CampaignStatus.REJECTED.value,
                "rejected_at": datetime.now(),
                "rejected_by": admin_id,
                "rejection_reason": reason
            }
        },
        return_document=ReturnDocument.AFTER
    )
    
    # Log the rejection
    await log_admin_action(
        admin_id=admin_id,
        action="reject",
        campaign_id=campaign_id,
        details={"reason": reason}
    )
    
    return decrypt_campaign_for_admin(updated)


# ============== AUDIT LOGS ==============

@router.get(
    "/logs",
    summary="Get Admin Logs",
    description="Fetch admin action logs for audit purposes."
)
async def get_admin_logs(
    admin_id: Optional[str] = Query(None, description="Filter by admin ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Retrieve admin action logs.
    
    - Used for audit and compliance
    - Filterable by admin, action type, or campaign
    """
    query = {}
    
    if admin_id:
        query["admin_id"] = admin_id
    if action:
        query["action"] = action
    if campaign_id:
        query["campaign_id"] = campaign_id
    
    logs = await get_admin_logs_collection().find(query).sort([
        ("timestamp", -1)
    ]).limit(limit).to_list(limit)
    
    # Convert ObjectIds to strings
    for log in logs:
        log["_id"] = str(log["_id"])
    
    return logs


# ============== STATISTICS ==============

@router.get(
    "/stats",
    summary="Get Admin Statistics",
    description="Get overview statistics for admin dashboard."
)
async def get_admin_stats():
    """
    Get campaign statistics for admin dashboard.
    """
    collection = get_campaigns_collection()
    
    # Count by status
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_counts = await collection.aggregate(pipeline).to_list(None)
    
    # Count by type
    type_pipeline = [
        {"$group": {"_id": "$campaign_type", "count": {"$sum": 1}}}
    ]
    type_counts = await collection.aggregate(type_pipeline).to_list(None)
    
    # Total raised
    raised_pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$raised_amount"}}}
    ]
    total_raised = await collection.aggregate(raised_pipeline).to_list(None)
    
    return {
        "by_status": {item["_id"]: item["count"] for item in status_counts},
        "by_type": {item["_id"]: item["count"] for item in type_counts},
        "total_raised": total_raised[0]["total"] if total_raised else 0,
        "generated_at": datetime.now().isoformat()
    }
