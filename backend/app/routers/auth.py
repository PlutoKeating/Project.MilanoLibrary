import os
import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "users.json")


def load_users() -> List[Dict[str, str]]:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        default_users = [{
            "uuid": str(uuid.uuid4()),
            "username": settings.auth_username,
            "password": settings.auth_password
        }]
        save_users(default_users)
        return default_users
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Legacy format check: if it is a dictionary and doesn't have "users" list
            if isinstance(data, dict) and "users" not in data:
                # Convert from {"username": "password"} legacy format
                migrated = []
                for username, password in data.items():
                    migrated.append({
                        "uuid": str(uuid.uuid4()),
                        "username": username,
                        "password": password
                    })
                save_users(migrated)
                return migrated
            elif isinstance(data, dict) and "users" in data:
                return data["users"]
            elif isinstance(data, list):
                # Wrapped list format support
                save_users(data)
                return data
            else:
                raise ValueError("Unknown users.json schema")
    except Exception:
        default_users = [{
            "uuid": str(uuid.uuid4()),
            "username": settings.auth_username,
            "password": settings.auth_password
        }]
        save_users(default_users)
        return default_users


def save_users(users: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str


class UpdateUserRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(request: LoginRequest):
    users = load_users()
    for u in users:
        if u["username"] == request.username and u["password"] == request.password:
            return {"success": True, "token": "milano-auth-token"}
    raise HTTPException(status_code=401, detail="Invalid username or password")


@router.post("/verify")
async def verify(token: str):
    if token == "milano-auth-token":
        return {"valid": True}
    return {"valid": False}


# --- CRUD Users endpoints ---

@router.get("/users")
async def list_users():
    users = load_users()
    return users


@router.post("/users")
async def create_user(request: CreateUserRequest):
    users = load_users()
    username_clean = request.username.strip()
    if not username_clean:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    
    # Check if username already exists
    for u in users:
        if u["username"] == username_clean:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = {
        "uuid": str(uuid.uuid4()),
        "username": username_clean,
        "password": request.password
    }
    users.append(new_user)
    save_users(users)
    return {"success": True, "user": new_user}


@router.put("/users/{user_uuid}")
async def update_user(user_uuid: str, request: UpdateUserRequest):
    users = load_users()
    username_clean = request.username.strip()
    if not username_clean:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    found_user = None
    for u in users:
        if u["uuid"] == user_uuid:
            found_user = u
            break
            
    if not found_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Check if new username is already taken by another user
    for u in users:
        if u["uuid"] != user_uuid and u["username"] == username_clean:
            raise HTTPException(status_code=400, detail="Username already exists")
            
    found_user["username"] = username_clean
    found_user["password"] = request.password
    save_users(users)
    return {"success": True, "message": "User updated successfully"}


@router.delete("/users/{user_uuid}")
async def delete_user(user_uuid: str):
    users = load_users()
    
    user_idx = -1
    for idx, u in enumerate(users):
        if u["uuid"] == user_uuid:
            user_idx = idx
            break
            
    if user_idx == -1:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Prevent lockout by requiring at least 1 user to remain
    if len(users) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last remaining user account")
        
    del users[user_idx]
    save_users(users)
    return {"success": True, "message": "User deleted successfully"}
