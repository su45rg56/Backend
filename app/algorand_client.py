import hashlib, base64, os
from algosdk import mnemonic
from algosdk.v2client import algod, indexer
from algosdk.transaction import PaymentTxn
from dotenv import load_dotenv
load_dotenv()

ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS") or "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN") or ""
INDEXER_ADDRESS = os.getenv("INDEXER_ADDRESS") or "https://testnet-idx.algonode.cloud"
INDEXER_TOKEN = os.getenv("INDEXER_TOKEN") or ""

PROOF_MNEMONIC = os.getenv("PROOF_MNEMONIC") or ""
if PROOF_MNEMONIC:
    PRIVATE_KEY = mnemonic.to_private_key(PROOF_MNEMONIC)
    PUBLIC_ADDR = mnemonic.to_public_key(PROOF_MNEMONIC)
else:
    PRIVATE_KEY = None
    PUBLIC_ADDR = None

algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)
indexer_client = indexer.IndexerClient(INDEXER_TOKEN, INDEXER_ADDRESS)

def compute_sha256_of_object(obj: dict) -> str:
    import json
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

def send_proof_hash_to_algorand(hash_hex: str) -> str:
    if not PRIVATE_KEY or not PUBLIC_ADDR:
        raise RuntimeError("Wallet not configured")
    params = algod_client.suggested_params()
    txn = PaymentTxn(PUBLIC_ADDR, params, PUBLIC_ADDR, 0, note=hash_hex.encode())
    signed = txn.sign(PRIVATE_KEY)
    return algod_client.send_transaction(signed)

def read_hash_from_txid(txid: str):
    res = indexer_client.search_transactions(txid=txid)
    txns = res.get("transactions")
    if not txns: return None
    note_b64 = txns[0].get("note")
    if not note_b64: return None
    return base64.b64decode(note_b64).decode()
