from fastapi import APIRouter, Body, HTTPException, status
from typing import List
from models.donation import Donation, DonationCreate
from database import db
import os
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/donations", tags=["Donations"])

def get_donation_collection():
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["donations"]

def get_campaign_collection():
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["campaigns"]

@router.post("/", response_model=Donation, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_donation(donation: DonationCreate = Body(...)):
    """
    Record a new donation after successful blockchain transaction.
    """
    # Verify campaign exists (optional but recommended)
    if not ObjectId.is_valid(donation.campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
    campaign = await get_campaign_collection().find_one({"_id": ObjectId(donation.campaign_id)})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    donation_dict = donation.model_dump()
    donation_dict["created_at"] = datetime.now()
    
    new_donation = await get_donation_collection().insert_one(donation_dict)
    created_donation = await get_donation_collection().find_one({"_id": new_donation.inserted_id})
    return created_donation

@router.get("/user/{wallet_address}", response_model=List[Donation], response_model_by_alias=False)
async def get_user_donations(wallet_address: str):
    """
    Fetch all donations made by a specific wallet address.
    """
    donations = await get_donation_collection().find({"wallet_address": wallet_address}).sort("created_at", -1).to_list(1000)
    return donations

@router.get("/campaign/{campaign_id}", response_model=List[Donation], response_model_by_alias=False)
async def get_campaign_donations(campaign_id: str):
    """
    Fetch all donations for a specific campaign.
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID")

    # We store campaign_id as a string in the donation record based on the model, 
    # but let's ensure we are consistent. 
    # The DonationBase model defines campaign_id as str.
    
    donations = await get_donation_collection().find({"campaign_id": campaign_id}).sort("created_at", -1).to_list(1000)
    return donations
