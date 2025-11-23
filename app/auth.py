from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Use bcrypt_sha256 to avoid 72-byte password limit
# If bcrypt_sha256 fails due to version issues, fallback to manual SHA256 + bcrypt
try:
    pwd_context = CryptContext(
        schemes=["bcrypt_sha256"],
        default="bcrypt_sha256",
        deprecated="auto"
    )
    # Test if it works
    _test_hash = pwd_context.hash("test")
    USE_BCRYPT_SHA256 = True
except Exception:
    # Fallback to regular bcrypt with manual SHA256 hashing
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        default="bcrypt",
        deprecated="auto"
    )
    USE_BCRYPT_SHA256 = False

# Password utilities
def verify_password(plain_password: str, hashed: str) -> bool:
    if USE_BCRYPT_SHA256:
        return pwd_context.verify(plain_password, hashed)
    else:
        # Manual SHA256 + bcrypt verification
        # Hash the plain password with SHA256 first, then verify against bcrypt hash
        sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        return pwd_context.verify(sha256_hash, hashed)

def get_password_hash(password: str) -> str:
    if USE_BCRYPT_SHA256:
        # bcrypt_sha256 handles long passwords safely
        return pwd_context.hash(password)
    else:
        # Manual SHA256 hashing before bcrypt to avoid 72-byte limit
        # Hash password with SHA256 first, then bcrypt the hash
        sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return pwd_context.hash(sha256_hash)

# JWT utilities
def create_access_token(data: dict, expires_delta=None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
