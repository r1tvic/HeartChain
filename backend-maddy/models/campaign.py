"""
Campaign Models for HeartChain (Stateless / Decentralized).

Supports two campaign types:
- INDIVIDUAL: Personal campaigns (medical emergencies, personal crises)
- CHARITY: Organization campaigns (NGOs, registered charities)

Implements Pydantic schemas for Input Validation and IPFS Metadata construction.
NO DATABASE MODELS.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from datetime import datetime


class CampaignType(str, Enum):
    """Type of campaign - immutable after creation."""
    INDIVIDUAL = "individual"
    CHARITY = "charity"


class PriorityLevel(str, Enum):
    """Campaign urgency level."""
    URGENT = "urgent"
    NORMAL = "normal"


class DocumentType(str, Enum):
    """Types of supporting documents."""
    MEDICAL_BILL = "medical_bill"
    DOCTOR_PRESCRIPTION = "doctor_prescription"
    HOSPITAL_LETTER = "hospital_letter"
    ID_PROOF = "id_proof"
    NGO_CERTIFICATE = "ngo_certificate"
    LICENSE = "license"
    TRUST_DEED = "trust_deed"
    OTHER = "other"


class EncryptedField(BaseModel):
    """Schema for encrypted field storage."""
    nonce: str = Field(..., description="Base64-encoded nonce for AES-GCM")
    ciphertext: str = Field(..., description="Base64-encoded ciphertext")


class CampaignDocument(BaseModel):
    """Schema for uploaded document reference."""
    ipfs_hash: str = Field(..., description="IPFS content identifier (CID)")
    document_type: DocumentType = Field(..., description="Type of document")
    filename: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="File MIME type")
    uploaded_at: datetime = Field(default_factory=datetime.now)


# ============== CREATE SCHEMAS (User Input) ==============

class IndividualCampaignCreate(BaseModel):
    """Input Schema for Individual Campaign."""
    # Public
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=10, max_length=5000)
    target_amount: float = Field(..., gt=0)
    duration_days: int = Field(..., gt=0, le=365)
    category: str
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL)
    image_url: Optional[str] = None
    
    # Sensitive (Will be encrypted)
    beneficiary_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    residential_address: str = Field(..., min_length=5, max_length=500)
    verification_notes: Optional[str] = None


class CharityCampaignCreate(BaseModel):
    """Input Schema for Charity Campaign."""
    # Public
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=10, max_length=5000)
    target_amount: float = Field(..., gt=0)
    duration_days: int = Field(..., gt=0, le=365)
    category: str
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL)
    image_url: Optional[str] = None
    organization_name: str = Field(..., min_length=2, max_length=200)
    
    # Sensitive (Will be encrypted)
    contact_person_name: str = Field(..., min_length=2, max_length=100)
    contact_phone_number: str = Field(..., min_length=10, max_length=20)
    official_address: str = Field(..., min_length=5, max_length=500)
    verification_notes: Optional[str] = None


# ============== IPFS METADATA SCHEMA ==============

class CampaignMetadata(BaseModel):
    """
    The JSON structure stored on IPFS.
    Replaces the MongoDB document.
    """
    title: str
    description: str
    campaign_type: CampaignType
    category: str
    priority: PriorityLevel
    image_url: Optional[str] = None
    organization_name: Optional[str] = None  # Charity only
    
    # Encrypted Data Bundle
    # Keys will be field names like 'beneficiary_name', 'phone_number'
    # Values will be { nonce: '...', ciphertext: '...' }
    encrypted_data: Dict[str, EncryptedField]
    
    # Documents
    documents: List[CampaignDocument] = []
    
    created_at: str  # ISO string
    target_amount: float # Stored for redundancy/display
