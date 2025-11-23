Step 0 — Prepare a project folder and files (one-time)

If you already copied the files from Canvas into a folder (e.g., algorand-backend), skip to Step 1. If not, do this:

PowerShell / Cursor (Windows)

Open Cursor terminal (or Windows PowerShell).

Run:

# make a project folder on your desktop (or wherever you like)
cd ~
mkdir algorand-backend
cd algorand-backend

# optional: open this folder in VS Code (if you have it)
# code .


WSL (Linux shell) — same commands, run in your WSL terminal:

cd ~
mkdir algorand-backend
cd algorand-backend


Now copy each file content from the Canvas document into files on your machine. The easiest approach:

Open a text editor (Notepad, VS Code, or the editor inside Cursor).

Create these files and paste the corresponding content:

requirements.txt

docker-compose.yml

app/database.py

app/models.py

app/schemas.py

app/auth.py

app/algorand_client.py

app/main.py

README.md

If that is hard, tell me and I’ll give you a single command to create minimal working files — but manually copying is fine.

Step 1 — Start Postgres with Docker (one command)

This will create a local Postgres database you can use for development.

PowerShell (run in the algorand-backend folder):

docker compose up -d


What happens / what to expect:

Docker will download the Postgres image (may take a minute the first time).

After it runs, the DB will listen on port 5432 on your machine.

To check status, run: docker ps — you should see a container named something like algorand-backend_db_1.

If you get an error like Docker not running, open Docker Desktop and start it, then run the command again.

Step 2 — Create a Python virtual environment and install packages

I’ll show WSL/Linux commands and Windows PowerShell variants.

WSL / bash:

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt


PowerShell (Windows):

python -m venv .venv
# activate:
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt


What happens / what to expect:

python -m venv .venv creates a small private Python in the project folder.

activate switches your terminal to use that Python.

pip install -r requirements.txt will download and install libraries (FastAPI, SQLModel, algosdk...). It may print a lot of lines — that’s normal.

Step 3 — Create a .env file with secrets (very important)

Create a file named .env in the project root (same folder as docker-compose.yml) and paste these lines (replace placeholders where needed):

# For local DB (Docker). If you use a remote DB later, replace this URL.
DATABASE_URL=postgresql://fastapi_user:fastapi_pass@localhost:5432/algorand_app

# Security
SECRET_KEY=change-me-to-a-random-string

# Algorand testnet (optional now; needed only if you want to actually send txns)
ALGOD_ADDRESS=https://testnet-api.algonode.cloud
ALGOD_TOKEN=
INDEXER_ADDRESS=https://testnet-idx.algonode.cloud
INDEXER_TOKEN=

# If you want to post real proofs to Algorand TestNet (optional)
# Fill with a 25-word mnemonic of an Algorand TestNet account
PROOF_MNEMONIC=


What to do right now:

If you don’t want to send real blockchain transactions yet, leave PROOF_MNEMONIC blank. The app will still work and will store proof hashes in DB — it just won’t post to Algorand until you set the mnemonic.

Keep .env secret (don’t share it). This file stores keys.

Step 4 — Start the FastAPI server

Run this command in your project folder (with the virtualenv activated):

uvicorn app.main:app --reload --port 8000


What happens / what to expect:

Uvicorn will start the web server on port 8000.

You’ll see logs and INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit) or similar.

It also runs startup code that creates the database tables automatically.

Step 5 — Open the automatic API docs (Swagger UI)

Open your web browser and go to:

http://localhost:8000/docs


What you’ll see:

A graphical interface (Swagger) listing all endpoints (POST /brands/simple, POST /token, GET /campaigns, POST /campaigns/{id}/manufacture, etc.).

You can interact with each endpoint by expanding it, typing data, and pressing Try it out and Execute.

Step 6 — Create a brand (sign up)

We’ll create a brand account that you will use to access the dashboard APIs.

Using Swagger UI:

Open /brands/simple endpoint in the docs.

Click Try it out.

Paste JSON like:

{
  "name": "Fizzy Drinks",
  "email": "brand@example.com",
  "password": "testpassword"
}


Click Execute.

You should get a response with the brand object (id, name, email, created_at).

What this does: stores the brand in the database (password hashed).

Step 7 — Log in and get a token

Now get an access token so you can call protected endpoints.

In Swagger UI:

Open the /token endpoint.

Click Try it out.

Enter username = the email you used (e.g., brand@example.com) and password = the password you chose.

Click Execute.

You’ll get a response like:

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}


Copy the access_token string.

Authorize Swagger UI so you don’t paste the token on every request:

Click the Authorize button at top-right of the docs page, paste Bearer <access_token> (or just the token depending on UI), and press Authorize. Now protected endpoints will use this token automatically.

Step 8 — Create a campaign

In Swagger UI (POST /campaigns):

Expand /campaigns → POST.

Click Try it out.

Use JSON:

{
  "name": "Summer Promo",
  "start_date": "2025-06-01T00:00:00Z",
  "end_date": "2025-07-31T00:00:00Z"
}


Click Execute.

You’ll receive the created campaign object with id.

What happens in the DB: a new row in campaign with manufactured/distributed counts set to 0.

Step 9 — Add a manufacturing batch (and generate proof)

In Swagger UI (POST /campaigns/{campaign_id}/manufacture):

Expand that endpoint, click Try it out.

Enter the campaign_id (the numeric id returned earlier).

For request body use:

{
  "batch_number": "BATCH-001",
  "manufactured_count": 10000
}


Click Execute.

What happens in the app:

A ManufacturingBatch record is created.

Campaign.manufactured is increased by manufactured_count.

A small proof object is created (a JSON summary), hashed (SHA256), and:

If PROOF_MNEMONIC is set in .env, the hash will be posted to Algorand TestNet and you’ll get a txid.

If you left PROOF_MNEMONIC blank, txid will be null, but the proof_hash will still be saved in the DB.

You’ll see response like:

{
  "batch_id": 1,
  "proof_hash": "ab12cd34... (sha256 string)",
  "txid": null
}

Step 10 — Add a distribution location (and proof)

POST /campaigns/{campaign_id}/distribute — request body example:

{
  "location_name": "Downtown Cafe Cluster",
  "distributed_count": 2000,
  "lat": 24.8607,
  "lng": 67.0011
}


What happens:

Adds a DistributionRecord with location and count.

Increments campaign.distributed.

Adds one to campaign.locations_count.

Generates a proof hash (and posts to Algorand if mnemonic present).

Step 11 — Verify a proof by txid (optional if you posted to Algorand)

GET /proofs/{txid}

If you have a txid from Step 9 or 10, paste it into the endpoint and Execute.

The app will call the Algorand Indexer and return the note (the hash) stored in that transaction.

If txid is null, skip — you didn’t post to the blockchain yet.

Optional: Post real proofs to Algorand TestNet

If you want to actually publish a hash to Algorand TestNet (useful for real verification), you need:

A TestNet Algorand account mnemonic (25 words). You can create one with a wallet like Algorand Wallet, then switch to TestNet or create a TestNet account and get TestNet ALGO from a TestNet faucet. (If you want, I can give step-by-step instructions for creating a TestNet account and funding it.)

Put that 25-word mnemonic into .env as PROOF_MNEMONIC="word1 word2 ... word25"

Restart the server (Ctrl+C in the terminal then run the uvicorn command again). Then when you call manufacture/distribute endpoints, the code will send a transaction to Algorand and return a txid.

Important: Algorand transactions cost tiny fees (microAlgos). On TestNet you can get test ALGO for free.