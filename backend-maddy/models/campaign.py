from typing import Optional
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from typing_extensions import Annotated
from enum import Enum
from datetime import datetime

# Helper for MongoDB ObjectId
PyObjectId = Annotated[str, BeforeValidator(str)]

class PriorityLevel(str, Enum):
    URGENT = "urgent"
    NORMAL = "normal"

class CampaignStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"

class CampaignBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100, description="Title of the campaign")
    description: str = Field(..., description="Detailed description of the cause")
    goal_amount: float = Field(..., gt=0, description="Target amount to raise")
    category: str = Field(..., description="Category like Education, Health, etc.")
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Urgency level")
    status: CampaignStatus = Field(default=CampaignStatus.ACTIVE, description="Current status")
    image_url: Optional[str] = Field(None, description="URL to campaign banner image")

class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign"""
    pass

class Campaign(CampaignBase):
    """Schema for campaign response from DB"""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "title": "Clean Water for Village",
                "description": "Providing clean drinking water sources for the community.",
                "goal_amount": 5000.0,
                "category": "Environment",
                "priority": "normal",
                "status": "active"
            }
        }
    )
