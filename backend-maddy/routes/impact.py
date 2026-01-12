from fastapi import APIRouter, Body, HTTPException, status
from typing import List
from models.impact import ImpactReport, ImpactReportCreate
from database import db
import os
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/impact", tags=["Impact Reports"])

def get_impact_collection():
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["impact_reports"]

def get_campaign_collection():
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["campaigns"]

@router.post("/", response_model=ImpactReport, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_impact_report(report: ImpactReportCreate = Body(...)):
    """
    Add an impact report for a completed campaign.
    """
    if not ObjectId.is_valid(report.campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID")

    # Verify campaign exists
    campaign = await get_campaign_collection().find_one({"_id": ObjectId(report.campaign_id)})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    report_dict = report.model_dump()
    report_dict["created_at"] = datetime.now()
    
    new_report = await get_impact_collection().insert_one(report_dict)
    created_report = await get_impact_collection().find_one({"_id": new_report.inserted_id})
    return created_report

@router.get("/{campaign_id}", response_model=ImpactReport, response_model_by_alias=False)
async def get_impact_report(campaign_id: str):
    """
    Fetch the impact report for a specific campaign.
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
    report = await get_impact_collection().find_one({"campaign_id": campaign_id})
    if not report:
        raise HTTPException(status_code=404, detail="Impact report not found")
    
    return report
