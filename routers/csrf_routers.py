from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
import secrets
from typing import Dict, Any
import time
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/csrf-token",
    tags=["CSRF"],
    responses={404: {"description": "Not found"}}
)

# Store of CSRF tokens with expiration
# Structure: {user_id/email: {"token": string, "expires": timestamp}}
csrf_tokens: Dict[str, Dict[str, Any]] = {}

# Token expiration in seconds (30 minutes)
TOKEN_EXPIRATION = 30 * 60

class TokenRequest(BaseModel):
    email: str

# Helper to clean expired tokens
def clean_expired_tokens():
    now = time.time()
    to_delete = []
    
    for user_id, token_data in csrf_tokens.items():
        if token_data["expires"] < now:
            to_delete.append(user_id)
    
    for user_id in to_delete:
        del csrf_tokens[user_id]

# Generate and store CSRF token
@router.post("/")
@limiter.limit("10/minute")
async def get_csrf_token(request: Request, token_request: TokenRequest):
    # Rate limiting applied to prevent abuse
    
    # Clean expired tokens first
    clean_expired_tokens()
    
    # Generate a secure random token
    token = secrets.token_hex(32)
    expires = time.time() + TOKEN_EXPIRATION
    
    # Store token with user identifier
    user_id = token_request.email
    csrf_tokens[user_id] = {"token": token, "expires": expires}
    
    return {"csrf_token": token, "expires_in": TOKEN_EXPIRATION}

# Validate CSRF token
def validate_csrf_token(user_id: str, token: str) -> bool:
    # Clean expired tokens first
    clean_expired_tokens()
    
    # Check if token exists and matches
    if user_id in csrf_tokens and csrf_tokens[user_id]["token"] == token:
        # Token is valid, but we don't remove it since we want it to be usable
        # for multiple operations within the session
        return True
    
    return False 