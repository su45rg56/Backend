# app/main.py

# -------------------- app/main.py --------------------
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, date, time, timedelta
from sqlalchemy import and_
import os, json
from dotenv import load_dotenv
load_dotenv()

from .database import init_db, get_session, engine
from .models import Brand, Campaign, ManufacturingBatch, DistributionRecord, DailyActivity
from .schemas import (
    BrandCreate, BrandOut, Token,
    CampaignCreate, CampaignOut,
    DailyActivityCreate, DailyActivityOut,
    LocationIn, CampaignDailySummary
)
from .auth import get_password_hash, verify_password, create_access_token, decode_access_token
from .algorand_client import compute_sha256_of_object, send_proof_hash_to_algorand

# ----------------- FastAPI INSTANCE -----------------
app = FastAPI(title="Disposable Cups Backend")

# ----------------- CORS -----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Startup -----------------
@app.on_event("startup")
def on_startup():
    init_db()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# ----------------- Auth & Brand -----------------
@app.post("/brands", response_model=BrandOut)
def create_brand(brand: BrandCreate, session: Session = Depends(get_session)):
    db_brand = Brand(
        name=brand.name,
        email=brand.email,
        password_hash=get_password_hash(brand.password)
    )
    session.add(db_brand)
    session.commit()
    session.refresh(db_brand)
    return BrandOut.from_orm(db_brand)

@app.post('/brands/simple', response_model=BrandOut)
def create_brand_simple(brand: BrandCreate):
    from .auth import get_password_hash as _hash
    with Session(engine) as session:
        db_brand = Brand(name=brand.name, email=brand.email, password_hash=_hash(brand.password))
        session.add(db_brand)
        session.commit()
        session.refresh(db_brand)
        return BrandOut.from_orm(db_brand)

@app.post('/token', response_model=Token)
def login_for_token(form_data: OAuth2PasswordRequestForm = Depends()):
    with Session(engine) as session:
        statement = select(Brand).where(Brand.email == form_data.username)
        result = session.exec(statement).first()

        if not result or not verify_password(form_data.password, result.password_hash):
            raise HTTPException(400, "Incorrect email or password")

        access_token = create_access_token({"brand_id": result.id, "email": result.email})
        return {"access_token": access_token, "token_type": "bearer"}

async def get_current_brand(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")

    brand_id = payload.get("brand_id")
    with Session(engine) as session:
        brand = session.get(Brand, brand_id)
        if not brand:
            raise HTTPException(401, "Brand not found")
        return brand

# ----------------- Campaign endpoints -----------------
@app.post('/campaigns', response_model=CampaignOut)
def create_campaign(c: CampaignCreate, current_brand: Brand = Depends(get_current_brand)):
    with Session(engine) as session:
        db_campaign = Campaign(
            name=c.name,
            brand_id=current_brand.id,
            start_date=c.start_date,
            end_date=c.end_date
        )
        session.add(db_campaign)
        session.commit()
        session.refresh(db_campaign)
        return CampaignOut.from_orm(db_campaign)

@app.get('/campaigns', response_model=List[CampaignOut])
def list_campaigns(current_brand: Brand = Depends(get_current_brand)):
    with Session(engine) as session:
        statement = select(Campaign).where(Campaign.brand_id == current_brand.id)
        res = session.exec(statement).all()
        return [CampaignOut.from_orm(r) for r in res]

# ----------------- Campaign with daily summary -----------------
@app.get('/campaigns/{campaign_id}', response_model=CampaignDailySummary)
def get_campaign_with_summary(campaign_id: int, current_brand: Brand = Depends(get_current_brand)):
    with Session(engine) as session:
        campaign = session.get(Campaign, campaign_id)
        if not campaign or campaign.brand_id != current_brand.id:
            raise HTTPException(404, 'Campaign not found')

        activities = session.exec(
            select(DailyActivity)
            .where(DailyActivity.campaign_id == campaign_id)
            .order_by(DailyActivity.day.desc())
        ).all()

        # Build history records (with locations)
        history_activity = []
        for a in activities:
            day_start = datetime.combine(a.day, time.min)
            day_end = day_start + timedelta(days=1)

            d_recs = session.exec(
                select(DistributionRecord).where(
                    and_(
                        DistributionRecord.campaign_id == campaign_id,
                        DistributionRecord.distributed_at >= day_start,
                        DistributionRecord.distributed_at < day_end
                    )
                )
            ).all()

            locations = [
                {
                    "location_name": d.location_name,
                    "distributed_count": d.distributed_count,
                    "lat": d.lat,
                    "lng": d.lng
                }
                for d in d_recs
            ]

            out = DailyActivityOut.from_orm(a).dict()
            out["locations"] = locations
            history_activity.append(DailyActivityOut(**out))

        today_activity = history_activity[0] if history_activity else None

        # Calculate unique locations
        unique_locations = session.exec(
            select(DistributionRecord.location_name)
            .where(DistributionRecord.campaign_id == campaign_id)
        ).all()

        locations_count = len(set(unique_locations))

        totals = {
            "manufactured": sum(a.manufactured_today for a in activities),
            "distributed": sum(a.distributed_today for a in activities),
            "scans": sum(a.scan_count_today for a in activities),
            "locations": locations_count
        }

        return CampaignDailySummary(
            campaign_id=campaign.id,
            totals=totals,
            today=today_activity,
            history=history_activity,
            start_date=campaign.start_date,
            end_date=campaign.end_date
        )

# ----------------- Manufacturing / Distribution -----------------
from pydantic import BaseModel

class BatchIn(BaseModel):
    batch_number: str
    manufactured_count: int

@app.post('/campaigns/{campaign_id}/manufacture')
def add_manufacturing_batch(campaign_id: int, batch: BatchIn, current_brand: Brand = Depends(get_current_brand)):
    with Session(engine) as session:
        campaign = session.get(Campaign, campaign_id)
        if not campaign or campaign.brand_id != current_brand.id:
            raise HTTPException(404, 'Campaign not found')

        db_batch = ManufacturingBatch(
            campaign_id=campaign_id,
            batch_number=batch.batch_number,
            manufactured_count=batch.manufactured_count
        )
        session.add(db_batch)

        campaign.manufactured += batch.manufactured_count
        session.add(campaign)
        session.commit()

        session.refresh(db_batch)
        session.refresh(campaign)

        proof_obj = {
            "type": "manufacturing_batch",
            "campaign_id": campaign_id,
            "batch_id": db_batch.id,
            "batch_number": batch.batch_number,
            "manufactured_count": batch.manufactured_count,
        }

        hash_hex = compute_sha256_of_object(proof_obj)

        try:
            txid = send_proof_hash_to_algorand(hash_hex)
        except Exception:
            txid = None

        db_batch.proof_hash = hash_hex
        db_batch.proof_txid = txid
        session.add(db_batch)
        session.commit()

        return {"batch_id": db_batch.id, "proof_hash": hash_hex, "txid": txid}

class DistIn(BaseModel):
    location_name: str
    distributed_count: int
    lat: Optional[float] = None
    lng: Optional[float] = None

@app.post('/campaigns/{campaign_id}/distribute')
def add_distribution(campaign_id: int, d: DistIn, current_brand: Brand = Depends(get_current_brand)):
    with Session(engine) as session:
        campaign = session.get(Campaign, campaign_id)
        if not campaign or campaign.brand_id != current_brand.id:
            raise HTTPException(404, 'Campaign not found')

        rec = DistributionRecord(
            campaign_id=campaign_id,
            location_name=d.location_name,
            distributed_count=d.distributed_count,
            lat=d.lat,
            lng=d.lng
        )
        session.add(rec)

        campaign.distributed += d.distributed_count
        campaign.locations_count += 1
        session.add(campaign)
        session.commit()

        session.refresh(rec)

        proof_obj = {
            "type": "distribution",
            "campaign_id": campaign_id,
            "distribution_id": rec.id,
            "location": d.location_name,
            "distributed_count": d.distributed_count,
        }

        hash_hex = compute_sha256_of_object(proof_obj)

        try:
            txid = send_proof_hash_to_algorand(hash_hex)
        except Exception:
            txid = None

        rec.proof_hash = hash_hex
        rec.proof_txid = txid
        session.add(rec)
        session.commit()

        return {"distribution_id": rec.id, "proof_hash": hash_hex, "txid": txid}

# ----------------- Daily Activity -----------------
@app.post('/campaigns/{campaign_id}/daily-activity', response_model=DailyActivityOut)
def add_daily_activity(campaign_id: int, data: DailyActivityCreate, current_brand: Brand = Depends(get_current_brand)):
    from sqlalchemy import and_
    with Session(engine) as session:
        campaign = session.get(Campaign, campaign_id)
        if not campaign or campaign.brand_id != current_brand.id:
            raise HTTPException(404, 'Campaign not found')

        existing_activity = session.exec(
            select(DailyActivity).where(
                DailyActivity.campaign_id == campaign_id,
                DailyActivity.day == data.day
            )
        ).first()

        if existing_activity:
            campaign.manufactured -= existing_activity.manufactured_today
            campaign.distributed -= existing_activity.distributed_today

            existing_activity.manufactured_today = data.manufactured_today
            existing_activity.distributed_today = data.distributed_today
            existing_activity.scan_count_today = data.scan_count_today

            activity = existing_activity
        else:
            activity = DailyActivity(
                campaign_id=campaign_id,
                day=data.day,
                manufactured_today=data.manufactured_today,
                distributed_today=data.distributed_today,
                scan_count_today=data.scan_count_today
            )
            session.add(activity)

        campaign.manufactured += data.manufactured_today
        campaign.distributed += data.distributed_today
        session.add(campaign)

        session.commit()
        session.refresh(activity)
        session.refresh(campaign)

        # handle locations
        if getattr(data, "locations", None):
            day_start = datetime.combine(data.day, time.min)
            day_end = day_start + timedelta(days=1)

            old_dist = session.exec(
                select(DistributionRecord).where(
                    and_(
                        DistributionRecord.campaign_id == campaign_id,
                        DistributionRecord.distributed_at >= day_start,
                        DistributionRecord.distributed_at < day_end
                    )
                )
            ).all()

            for od in old_dist:
                session.delete(od)
            session.commit()

            midday = datetime.combine(data.day, time(hour=12))

            for loc in data.locations:
                rec = DistributionRecord(
                    campaign_id=campaign_id,
                    location_name=loc.location_name,
                    distributed_count=loc.distributed_count,
                    lat=loc.lat,
                    lng=loc.lng,
                    distributed_at=midday
                )
                session.add(rec)
                session.commit()

        proof_obj = {
            "type": "daily_activity",
            "campaign_id": campaign_id,
            "activity_id": activity.id,
            "date": data.day.strftime("%Y-%m-%d"),
            "manufactured_today": data.manufactured_today,
            "distributed_today": data.distributed_today,
            "scan_count_today": data.scan_count_today
        }
        hash_hex = compute_sha256_of_object(proof_obj)

        try:
            txid = send_proof_hash_to_algorand(hash_hex)
        except Exception:
            txid = None

        activity._sha256 = hash_hex
        activity.algorand_txid = txid
        session.add(activity)
        session.commit()
        session.refresh(activity)

        day_start = datetime.combine(activity.day, time.min)
        day_end = day_start + timedelta(days=1)

        d_recs = session.exec(
            select(DistributionRecord).where(
                and_(
                    DistributionRecord.campaign_id == campaign_id,
                    DistributionRecord.distributed_at >= day_start,
                    DistributionRecord.distributed_at < day_end
                )
            )
        ).all()

        locations = [
            {
                "location_name": d.location_name,
                "distributed_count": d.distributed_count,
                "lat": d.lat,
                "lng": d.lng
            }
            for d in d_recs
        ]

        out = DailyActivityOut.from_orm(activity).dict()
        out["locations"] = locations

        return DailyActivityOut(**out)

@app.get('/campaigns/{campaign_id}/daily-activities', response_model=List[DailyActivityOut])
def get_daily_activities(campaign_id: int, current_brand: Brand = Depends(get_current_brand)):
    from sqlalchemy import and_
    with Session(engine) as session:
        campaign = session.get(Campaign, campaign_id)
        if not campaign or campaign.brand_id != current_brand.id:
            raise HTTPException(404, 'Campaign not found')

        activities = session.exec(
            select(DailyActivity)
            .where(DailyActivity.campaign_id == campaign_id)
            .order_by(DailyActivity.day.desc())
        ).all()

        results = []
        for a in activities:
            day_start = datetime.combine(a.day, time.min)
            day_end = day_start + timedelta(days=1)

            d_recs = session.exec(
                select(DistributionRecord).where(
                    and_(
                        DistributionRecord.campaign_id == campaign_id,
                        DistributionRecord.distributed_at >= day_start,
                        DistributionRecord.distributed_at < day_end
                    )
                )
            ).all()

            locations = [
                {
                    "location_name": d.location_name,
                    "distributed_count": d.distributed_count,
                    "lat": d.lat,
                    "lng": d.lng
                }
                for d in d_recs
            ]

            out = DailyActivityOut.from_orm(a).dict()
            out["locations"] = locations
            results.append(DailyActivityOut(**out))

        return results

# ----------------- health -----------------
@app.get('/')
def root():
    return {"ok": True, "message": "Disposable Cups Backend running"}

# EOF
