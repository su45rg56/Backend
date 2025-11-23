# Disposable Cups — FastAPI Backend (Starter)

This project is a beginner-friendly FastAPI backend that stores campaign data and anchors proofs to Algorand.

## What this scaffold includes
- FastAPI app with endpoints for brands and campaigns
- SQLModel models (Brand, Campaign, ManufacturingBatch, DistributionRecord, BlockchainProof)
- Simple JWT auth (brand login)
- Algorand client helper (send proof as txn note) using `algosdk`
- Docker compose to run a local Postgres (useful for development)

## Your environment (based on what you told me)
You have: Windows + WSL, Python, Docker, Node, Cursor. We'll run commands in WSL/PowerShell depending on preference. I will assume WSL or PowerShell is fine.

## Quick start (commands to run in your terminal)
1. Create project folder and files (copy files from this canvas into your machine).
2. Start Postgres with Docker:
   ```bash
   docker compose up -d
   ```
3. Create a Python virtual environment and install deps:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
5. Open http://localhost:8000/docs

## Notes
- For production use Neon.
