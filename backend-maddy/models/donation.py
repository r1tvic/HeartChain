from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from typing import Optional
from typing_extensions import Annotated
from datetime import datetime

# Helper for MongoDB ObjectId
PyObjectId = Annotated[str, BeforeValidator(str)]

class DonationBase(BaseModel):
    wallet_address: str = Field(..., description="Wallet address of the donor")
    campaign_id: str = Field(..., description="ID of the campaign being donated to")
    amount: float = Field(..., gt=0, description="Amount donated in ETH/tokens")
    transaction_hash: str = Field(..., description="Blockchain transaction hash")

class DonationCreate(DonationBase):
    """Schema for recording a new donation"""
    pass

class Donation(DonationBase):
    """Schema for donation response from DB"""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "wallet_address": "0x123...",
                "campaign_id": "60d5ecb8b3...",
                "amount": 1.5,
                "transaction_hash": "0xabc...",
                "created_at": "2023-01-01T12:00:00"
            }
        }
    )
