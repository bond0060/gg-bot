from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field
from enum import Enum


class TravelType(str, Enum):
    SOLO = "solo"
    COUPLE = "couple" 
    FAMILY = "family"
    GROUP = "group"
    BUSINESS = "business"


class BudgetLevel(str, Enum):
    BUDGET = "budget"
    MODERATE = "moderate"
    LUXURY = "luxury"
    UNLIMITED = "unlimited"


class ActivityType(str, Enum):
    SIGHTSEEING = "sightseeing"
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    FOOD = "food"
    RELAXATION = "relaxation"
    SHOPPING = "shopping"
    NIGHTLIFE = "nightlife"
    NATURE = "nature"


class Accommodation(BaseModel):
    name: str = Field(..., description="Name of the accommodation")
    type: str = Field(..., description="Type (hotel, hostel, apartment, etc.)")
    location: str = Field(..., description="Location/area")
    price_range: str = Field(..., description="Price range per night")
    rating: Optional[float] = Field(None, description="Rating out of 5")
    amenities: List[str] = Field(default_factory=list, description="Key amenities")
    booking_notes: Optional[str] = Field(None, description="Booking tips or notes")


class Activity(BaseModel):
    name: str = Field(..., description="Activity name")
    type: ActivityType = Field(..., description="Activity category")
    location: str = Field(..., description="Location")
    duration: str = Field(..., description="Estimated duration")
    cost: str = Field(..., description="Estimated cost")
    description: str = Field(..., description="Activity description")
    tips: Optional[str] = Field(None, description="Tips or recommendations")
    booking_required: bool = Field(default=False, description="Whether advance booking is needed")


class Transportation(BaseModel):
    method: str = Field(..., description="Transportation method")
    from_location: str = Field(..., description="Starting point")
    to_location: str = Field(..., description="Destination")
    cost: str = Field(..., description="Estimated cost")
    duration: str = Field(..., description="Travel time")
    notes: Optional[str] = Field(None, description="Additional notes")


class DayItinerary(BaseModel):
    day: int = Field(..., description="Day number")
    date: Optional[str] = Field(None, description="Date (if known)")
    theme: str = Field(..., description="Day theme or focus")
    activities: List[Activity] = Field(..., description="Activities for the day")
    meals: List[str] = Field(default_factory=list, description="Meal recommendations")
    transportation: List[Transportation] = Field(default_factory=list, description="Transportation needed")
    estimated_cost: str = Field(..., description="Estimated daily cost")
    tips: Optional[str] = Field(None, description="Daily tips")


class TravelPlan(BaseModel):
    id: str = Field(..., description="Unique plan identifier")
    title: str = Field(..., description="Travel plan title")
    destination: str = Field(..., description="Main destination")
    duration: str = Field(..., description="Trip duration")
    travel_dates: Optional[str] = Field(None, description="Travel dates if specified")
    travel_type: TravelType = Field(..., description="Type of travel")
    budget_level: BudgetLevel = Field(..., description="Budget level")
    group_size: int = Field(default=1, description="Number of travelers")
    
    # Plan sections
    overview: str = Field(..., description="Trip overview and highlights")
    accommodations: List[Accommodation] = Field(default_factory=list, description="Recommended accommodations")
    itinerary: List[DayItinerary] = Field(..., description="Day-by-day itinerary")
    
    # Practical information
    total_budget_estimate: str = Field(..., description="Total estimated budget")
    packing_list: List[str] = Field(default_factory=list, description="Essential items to pack")
    local_tips: List[str] = Field(default_factory=list, description="Local tips and customs")
    emergency_info: Dict[str, str] = Field(default_factory=dict, description="Emergency contacts and info")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field(..., description="User who created the plan")
    chat_id: int = Field(..., description="Chat where plan was created")
    version: int = Field(default=1, description="Plan version number")
    tags: List[str] = Field(default_factory=list, description="Plan tags for categorization")


class PlanSummary(BaseModel):
    """Lightweight plan summary for listings"""
    id: str
    title: str
    destination: str
    duration: str
    travel_type: TravelType
    budget_level: BudgetLevel
    created_at: datetime
    created_by: str


class PlanUpdate(BaseModel):
    """Model for plan updates/modifications"""
    plan_id: str
    updates: Dict[str, Any] = Field(..., description="Fields to update")
    update_reason: str = Field(..., description="Reason for the update")
    updated_by: str = Field(..., description="User making the update")