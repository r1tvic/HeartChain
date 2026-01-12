from fastapi import APIRouter, Body, HTTPException, status
from typing import List
from models.badge import Badge, BadgeCreate
from database import db
import os
from datetime import datetime

router = APIRouter(prefix="/badges", tags=["Badges"])

def get_badge_collection():
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["badges"]

@router.post("/", response_model=Badge, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_badge_metadata(badge: BadgeCreate = Body(...)):
    """
    Store badge metadata.
    """
    badge_dict = badge.model_dump()
    badge_dict["created_at"] = datetime.now()
    
    new_badge = await get_badge_collection().insert_one(badge_dict)
    created_badge = await get_badge_collection().find_one({"_id": new_badge.inserted_id})
    return created_badge

@router.get("/user/{wallet_address}", response_model=List[Badge], response_model_by_alias=False)
async def get_user_badges(wallet_address: str):
    """
    Fetch all badges for a specific user wallet.
    """
    badges = await get_badge_collection().find({"wallet_address": wallet_address}).to_list(1000)
    return badges
