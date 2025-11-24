# app/models.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, date

class Brand(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    campaigns: List["Campaign"] = Relationship(back_populates="brand")

class Campaign(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    brand_id: int = Field(foreign_key="brand.id")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    manufactured: int = 0
    distributed: int = 0
    locations_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # relationships
    brand: Optional[Brand] = Relationship(back_populates="campaigns")
    daily_activities: List["DailyActivity"] = Relationship(back_populates="campaign")

class ManufacturingBatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id")
    batch_number: str
    manufactured_count: int
    produced_at: datetime = Field(default_factory=datetime.utcnow)
    proof_hash: Optional[str] = None
    proof_txid: Optional[str] = None

class DistributionRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id")
    location_name: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    distributed_count: int = 0
    distributed_at: datetime = Field(default_factory=datetime.utcnow)
    proof_hash: Optional[str] = None
    proof_txid: Optional[str] = None

class DailyActivity(SQLModel, table=True):
    """
    One row per campaign per day. This stores the daily numbers and optional
    proof/hash/algorand txid for verification.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id")
    day: date
    manufactured_today: int = 0
    distributed_today: int = 0
    scan_count_today: int = 0
    _sha256: Optional[str] = None
    algorand_txid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # relationship back to campaign
    campaign: Optional[Campaign] = Relationship(back_populates="daily_activities")

class BlockchainProof(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    related_type: str
    related_id: int
    _sha256_hash: str
    algorand_txid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)