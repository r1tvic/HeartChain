from fastapi import APIRouter, Body, HTTPException, status
from typing import List
from models.campaign import Campaign, CampaignCreate, CampaignStatus
from database import db
import os
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

def get_collection():
    """Helper to get the campaigns collection"""
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["campaigns"]

@router.post("/", response_model=Campaign, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_campaign(campaign: CampaignCreate = Body(...)):
    """
    Create a new fundraising campaign.
    """
    campaign_dict = campaign.model_dump()
    campaign_dict["created_at"] = datetime.now()
    
    new_campaign = await get_collection().insert_one(campaign_dict)
    created_campaign = await get_collection().find_one({"_id": new_campaign.inserted_id})
    return created_campaign

@router.get("/", response_model=List[Campaign], response_model_by_alias=False)
async def list_campaigns():
    """
    Fetch all campaigns sorted by priority and status.
    High priority (Urgent) active -> Normal active -> Completed.
    """
    
    campaigns = await get_collection().find().sort([
        ("status", 1),
        ("priority", -1)
    ]).to_list(1000)
    return campaigns

@router.get("/{campaign_id}", response_model=Campaign, response_model_by_alias=False)
async def get_campaign(campaign_id: str):
    """
    Fetch details of a single campaign by ID.
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID")

    campaign = await get_collection().find_one({"_id": ObjectId(campaign_id)})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return campaign

@router.put("/{campaign_id}/complete", response_model=Campaign, response_model_by_alias=False)
async def mark_campaign_completed(campaign_id: str):
    """
    Mark a campaign as completed.
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID")

    updated_campaign = await get_collection().find_one_and_update(
        {"_id": ObjectId(campaign_id)},
        {"$set": {"status": CampaignStatus.COMPLETED}},
        return_document=ReturnDocument.AFTER
    )

    if not updated_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return updated_campaign
