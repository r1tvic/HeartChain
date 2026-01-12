from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from typing import Optional
from typing_extensions import Annotated
from datetime import datetime

# Helper for MongoDB ObjectId
PyObjectId = Annotated[str, BeforeValidator(str)]

class BadgeBase(BaseModel):
    wallet_address: str = Field(..., description="Wallet address of the badge holder")
    badge_name: str = Field(..., description="Name of the badge")
    description: str = Field(..., description="Description of what the badge represents")
    token_id: str = Field(..., description="Token ID on the blockchain")
    image_url: Optional[str] = Field(None, description="URL or IPFS hash of the badge image")

class BadgeCreate(BadgeBase):
    """Schema for storing new badge metadata"""
    pass

class Badge(BadgeBase):
    """Schema for badge response from DB"""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "wallet_address": "0x123...",
                "badge_name": "Early Donor",
                "description": "Donated to the first 10 campaigns.",
                "token_id": "1",
                "image_url": "ipfs://QmBadge...",
                "created_at": "2023-01-01T12:00:00"
            }
        }
    )
