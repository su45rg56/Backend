# app/schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

# ----------------------------
# Brand Schemas
# ----------------------------

class BrandCreate(BaseModel):
    name: str
    email: str
    password: str

class BrandOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        orm_mode = True

# ----------------------------
# Auth
# ----------------------------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ----------------------------
# Campaign Schemas
# ----------------------------

class CampaignCreate(BaseModel):
    name: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]

class CampaignOut(BaseModel):
    id: int
    name: str
    brand_id: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    manufactured: int
    distributed: int
    locations_count: int

    class Config:
        orm_mode = True

# -------------------------------------------------------------
# DailyActivity + Location schemas
# -------------------------------------------------------------
class LocationIn(BaseModel):
    location_name: str
    distributed_count: int
    lat: Optional[float] = None
    lng: Optional[float] = None

class DailyActivityBase(BaseModel):
    day: date
    manufactured_today: int
    distributed_today: int
    scan_count_today: int

class DailyActivityCreate(DailyActivityBase):
    # optional: frontend can include locations when posting daily activity
    locations: Optional[List[LocationIn]] = None

class DailyActivityOut(DailyActivityBase):
    id: int
    campaign_id: int
    locations: Optional[List[LocationIn]] = None
    _sha256: Optional[str] = None
    algorand_txid: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True

# -------------------------------------------------------------
# Aggregated response used by frontend dashboard + campaign page
# -------------------------------------------------------------
class CampaignDailySummary(BaseModel):
    campaign_id: int
    totals: dict  # Example: { "manufactured": 50000, "distributed": 30000, "scans": 4200, "locations": 10 }
    today: Optional[DailyActivityOut]
    history: List[DailyActivityOut] = []  # Sorted newest → oldest
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
