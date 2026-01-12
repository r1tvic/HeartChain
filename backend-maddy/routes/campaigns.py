from fastapi import APIRouter, Body, HTTPException, status
from typing import List, Dict
from datetime import datetime
from pydantic import BaseModel


from models.campaign import (
    IndividualCampaignCreate,
    CharityCampaignCreate,
    CampaignMetadata,
    CampaignType,
    CampaignDocument,
    EncryptedField
)
from services.ipfs_service import upload_json
from services.blockchain_service import create_campaign_on_chain
from core.encryption import get_encryption, EncryptionError

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

class CreateResponse(BaseModel):
    tx_hash: str
    cid: str
    status: str = "submitted_to_chain"

class IndividualCreateRequest(IndividualCampaignCreate):
    documents: List[CampaignDocument] = []

class CharityCreateRequest(CharityCampaignCreate):
    documents: List[CampaignDocument] = []

@router.post("/individual", response_model=CreateResponse, status_code=201)
async def create_individual_campaign(payload: IndividualCreateRequest):
    """
    Create Individual Campaign (Stateless).
    1. Encrypt PII.
    2. Upload Metadata to IPFS.
    3. Call Smart Contract.
    """
    try:
        encryption = get_encryption()
        
        # Encrypt sensitive fields
        # Note: encryption.encrypt returns Dict {nonce, ciphertext} ?? 
        # Wait, core/encryption.py likely returns raw dict or object?
        # Step 361 showed usage: `encryption.encrypt(str)` -> `{nonce:..., ciphertext:...}`?
        # Let's verify encryption.encrypt return type. 
        # Assuming it returns dict compatible with EncryptedField.
        
        # Build Metadata
        encrypted_info = {
            "beneficiary_name": encryption.encrypt(payload.beneficiary_name),
            "phone_number": encryption.encrypt(payload.phone_number),
            "residential_address": encryption.encrypt(payload.residential_address),
            "verification_notes": encryption.encrypt(payload.verification_notes) if payload.verification_notes else None
        }
        # Remove None values
        encrypted_info = {k: v for k, v in encrypted_info.items() if v is not None}
        
        metadata = CampaignMetadata(
            title=payload.title,
            description=payload.description,
            campaign_type=CampaignType.INDIVIDUAL,
            category=payload.category,
            priority=payload.priority,
            image_url=payload.image_url,
            target_amount=payload.target_amount,
            created_at=datetime.now().isoformat(),
            documents=payload.documents,
            encrypted_data=encrypted_info
        )
        
        # Upload Metadata to IPFS
        cid = await upload_json(metadata.model_dump(mode='json'))
        
        # Call Blockchain
        tx_hash = await create_campaign_on_chain(payload.target_amount, cid)
        
        return CreateResponse(tx_hash=tx_hash, cid=cid)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charity", response_model=CreateResponse, status_code=201)
async def create_charity_campaign(payload: CharityCreateRequest):
    """
    Create Charity Campaign (Stateless).
    """
    try:
        encryption = get_encryption()
        
        encrypted_info = {
            "contact_person_name": encryption.encrypt(payload.contact_person_name),
            "contact_phone_number": encryption.encrypt(payload.contact_phone_number),
            "official_address": encryption.encrypt(payload.official_address),
            "verification_notes": encryption.encrypt(payload.verification_notes) if payload.verification_notes else None
        }
        # Remove None values to satisfy Dict[str, EncryptedField]
        encrypted_info = {k: v for k, v in encrypted_info.items() if v is not None}
        
        metadata = CampaignMetadata(
            title=payload.title,
            description=payload.description,
            campaign_type=CampaignType.CHARITY,
            category=payload.category,
            priority=payload.priority,
            image_url=payload.image_url,
            organization_name=payload.organization_name, # Public
            target_amount=payload.target_amount,
            created_at=datetime.now().isoformat(),
            documents=payload.documents,
            encrypted_data=encrypted_info
        )
        
        cid = await upload_json(metadata.model_dump(mode='json'))
        tx_hash = await create_campaign_on_chain(payload.target_amount, cid)
        
        return CreateResponse(tx_hash=tx_hash, cid=cid)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


