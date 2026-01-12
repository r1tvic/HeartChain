"""
Campaign Models for HeartChain.

Supports two campaign types:
- INDIVIDUAL: Personal campaigns (medical emergencies, personal crises)
- CHARITY: Organization campaigns (NGOs, registered charities)

Implements mixed-field storage with encrypted sensitive data.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict, field_validator
from typing_extensions import Annotated
from enum import Enum
from datetime import datetime

# Helper for MongoDB ObjectId
PyObjectId = Annotated[str, BeforeValidator(str)]


class CampaignType(str, Enum):
    """Type of campaign - immutable after creation."""
    INDIVIDUAL = "individual"
    CHARITY = "charity"


class CampaignStatus(str, Enum):
    """Campaign lifecycle status."""
    DRAFT = "draft"
    PENDING_VERIFICATION = "pending_verification"
    APPROVED = "approved"
    ACTIVE = "active"
    CLOSED = "closed"
    REJECTED = "rejected"


class PriorityLevel(str, Enum):
    """Campaign urgency level."""
    URGENT = "urgent"
    NORMAL = "normal"


class DocumentType(str, Enum):
    """Types of supporting documents."""
    # Individual campaign documents
    MEDICAL_BILL = "medical_bill"
    DOCTOR_PRESCRIPTION = "doctor_prescription"
    HOSPITAL_LETTER = "hospital_letter"
    ID_PROOF = "id_proof"
    # Charity campaign documents
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
    """
    Schema for creating an Individual/Personal campaign.
    Sensitive fields are provided as plain strings and encrypted in backend.
    """
    # Public fields (NOT encrypted)
    title: str = Field(..., min_length=3, max_length=150, description="Campaign title")
    description: str = Field(..., min_length=10, max_length=5000, description="Campaign description")
    target_amount: float = Field(..., gt=0, description="Target amount to raise")
    duration_days: int = Field(..., gt=0, le=365, description="Campaign duration in days")
    category: str = Field(..., description="Category like Medical, Emergency, etc.")
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Urgency level")
    image_url: Optional[str] = Field(None, description="Campaign banner image URL")
    
    # Sensitive fields (WILL BE encrypted)
    beneficiary_name: str = Field(..., min_length=2, max_length=100, description="Full name of beneficiary")
    phone_number: str = Field(..., min_length=10, max_length=15, description="Contact phone number")
    residential_address: str = Field(..., min_length=10, max_length=500, description="Residential address")
    verification_notes: Optional[str] = Field(None, max_length=2000, description="Internal notes for verification")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Help Ravi Fight Cancer",
                "description": "Ravi is a 35-year-old father of two who has been diagnosed with stage 3 lung cancer...",
                "target_amount": 500000.0,
                "duration_days": 90,
                "category": "Medical",
                "priority": "urgent",
                "beneficiary_name": "Ravi Kumar",
                "phone_number": "9876543210",
                "residential_address": "123, Main Street, Chennai, Tamil Nadu 600001"
            }
        }
    )


class CharityCampaignCreate(BaseModel):
    """
    Schema for creating a Charity/Organization campaign.
    Sensitive fields are provided as plain strings and encrypted in backend.
    """
    # Public fields (NOT encrypted)
    title: str = Field(..., min_length=3, max_length=150, description="Campaign title")
    description: str = Field(..., min_length=10, max_length=5000, description="Campaign description")
    target_amount: float = Field(..., gt=0, description="Target amount to raise")
    duration_days: int = Field(..., gt=0, le=365, description="Campaign duration in days")
    category: str = Field(..., description="Category like Education, Health, Environment, etc.")
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Urgency level")
    image_url: Optional[str] = Field(None, description="Campaign banner image URL")
    organization_name: str = Field(..., min_length=2, max_length=200, description="Organization/NGO name")
    
    # Sensitive fields (WILL BE encrypted)
    contact_person_name: str = Field(..., min_length=2, max_length=100, description="Contact person name")
    contact_phone_number: str = Field(..., min_length=10, max_length=15, description="Contact phone number")
    official_address: str = Field(..., min_length=10, max_length=500, description="Registered office address")
    verification_notes: Optional[str] = Field(None, max_length=2000, description="Internal notes for verification")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Build 100 Schools in Rural India",
                "description": "Our NGO aims to provide education access to underprivileged children...",
                "target_amount": 5000000.0,
                "duration_days": 180,
                "category": "Education",
                "organization_name": "Education For All Foundation",
                "contact_person_name": "Dr. Priya Sharma",
                "contact_phone_number": "9123456789",
                "official_address": "NGO Complex, Block A, New Delhi 110001"
            }
        }
    )


# ============== RESPONSE SCHEMAS (Public View) ==============

class CampaignPublicResponse(BaseModel):
    """
    Public campaign response - NO sensitive data exposed.
    Used for listing campaigns and public viewing.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    campaign_type: CampaignType
    title: str
    description: str
    target_amount: float
    raised_amount: float = Field(default=0.0)
    duration_days: int
    category: str
    priority: PriorityLevel
    status: CampaignStatus
    image_url: Optional[str] = None
    organization_name: Optional[str] = None  # Only for charity campaigns
    documents_count: int = Field(default=0, description="Number of supporting documents")
    created_at: datetime
    end_date: datetime
    blockchain_tx_hash: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class CampaignAdminResponse(BaseModel):
    """
    Admin campaign response - includes decrypted sensitive data.
    Used ONLY in admin verification routes.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    campaign_type: CampaignType
    
    # Public fields
    title: str
    description: str
    target_amount: float
    raised_amount: float = Field(default=0.0)
    duration_days: int
    category: str
    priority: PriorityLevel
    status: CampaignStatus
    image_url: Optional[str] = None
    organization_name: Optional[str] = None
    
    # Decrypted sensitive fields (Individual)
    beneficiary_name: Optional[str] = None
    phone_number: Optional[str] = None
    residential_address: Optional[str] = None
    
    # Decrypted sensitive fields (Charity)
    contact_person_name: Optional[str] = None
    contact_phone_number: Optional[str] = None
    official_address: Optional[str] = None
    
    # Common sensitive
    verification_notes: Optional[str] = None
    
    # Documents with full details
    documents: List[CampaignDocument] = []
    
    # Metadata
    created_at: datetime
    end_date: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


# ============== DATABASE SCHEMA ==============

class CampaignInDB(BaseModel):
    """
    Full campaign schema as stored in MongoDB.
    Sensitive fields are stored as EncryptedField objects.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    campaign_type: CampaignType
    
    # Public fields (plain text)
    title: str
    description: str
    target_amount: float
    raised_amount: float = Field(default=0.0)
    duration_days: int
    category: str
    priority: PriorityLevel
    status: CampaignStatus = Field(default=CampaignStatus.DRAFT)
    image_url: Optional[str] = None
    organization_name: Optional[str] = None  # Public for charity
    
    # Encrypted fields (Individual campaign)
    beneficiary_name: Optional[Dict[str, str]] = None  # {nonce, ciphertext}
    phone_number: Optional[Dict[str, str]] = None
    residential_address: Optional[Dict[str, str]] = None
    
    # Encrypted fields (Charity campaign)
    contact_person_name: Optional[Dict[str, str]] = None
    contact_phone_number: Optional[Dict[str, str]] = None
    official_address: Optional[Dict[str, str]] = None
    
    # Common encrypted field
    verification_notes: Optional[Dict[str, str]] = None
    
    # Documents (stored as encrypted on IPFS, only hash stored here)
    documents: List[CampaignDocument] = []
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # Blockchain reference
    blockchain_tx_hash: Optional[str] = None
    
    # Creator reference
    created_by: Optional[str] = None  # User ID

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


# ============== STATUS UPDATE SCHEMAS ==============

class CampaignSubmitForVerification(BaseModel):
    """Schema for submitting a campaign for verification."""
    campaign_id: str = Field(..., description="Campaign ID to submit")


class CampaignApproval(BaseModel):
    """Schema for admin to approve/reject a campaign."""
    approved: bool = Field(..., description="True to approve, False to reject")
    rejection_reason: Optional[str] = Field(None, description="Reason if rejected")
    admin_notes: Optional[str] = Field(None, description="Internal admin notes")


class CampaignStatusUpdate(BaseModel):
    """Schema for updating campaign status."""
    status: CampaignStatus
    reason: Optional[str] = None


# ============== CONSTANTS ==============

# Fields that must be encrypted for Individual campaigns
INDIVIDUAL_ENCRYPTED_FIELDS = [
    "beneficiary_name",
    "phone_number", 
    "residential_address",
    "verification_notes"
]

# Fields that must be encrypted for Charity campaigns
CHARITY_ENCRYPTED_FIELDS = [
    "contact_person_name",
    "contact_phone_number",
    "official_address",
    "verification_notes"
]

# All sensitive fields combined
ALL_ENCRYPTED_FIELDS = list(set(INDIVIDUAL_ENCRYPTED_FIELDS + CHARITY_ENCRYPTED_FIELDS))
