from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from typing import Optional
from typing_extensions import Annotated
from datetime import datetime

# Helper for MongoDB ObjectId
PyObjectId = Annotated[str, BeforeValidator(str)]

class ImpactReportBase(BaseModel):
    campaign_id: str = Field(..., description="ID of the completed campaign")
    summary: str = Field(..., description="Summary of the impact or outcome")
    ipfs_link: Optional[str] = Field(None, description="Link to full report or images on IPFS")

class ImpactReportCreate(ImpactReportBase):
    """Schema for creating a new impact report"""
    pass

class ImpactReport(ImpactReportBase):
    """Schema for impact report response from DB"""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "campaign_id": "60d5ecb8b3...",
                "summary": "We successfully built the well and provided water to 500 villagers.",
                "ipfs_link": "ipfs://QmHash...",
                "created_at": "2023-01-01T12:00:00"
            }
        }
    )
