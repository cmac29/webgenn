# server.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional, List
import os
from datetime import datetime
import uvicorn

# Pydantic Models
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class MongoBaseModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=6)

class UserResponse(MongoBaseModel):
    username: str
    email: str
    created_at: datetime
    is_active: bool = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

class ItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., gt=0)
    category: str
    user_id: str

class ItemResponse(MongoBaseModel):
    title: str
    description: Optional[str]
    price: float
    category: str
    user_id: str
    created_at: datetime
    updated_at: datetime

class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = None

# Database Configuration
class Database:
    client: AsyncIOMotorClient = None

db = Database()

async def get_database() -> AsyncIOMotorClient:
    return db.client

# FastAPI Application
app = FastAPI(
    title="FastAPI MongoDB Backend",
    description="A production-ready FastAPI backend with MongoDB integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Database Events
@app.on_event("startup")
async def startup_db_client():
    db.client = AsyncIOMotorClient(
        os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    )
    
@app.on_event("shutdown")
async def shutdown_db_client():
    db.client.close()

# Utility Functions
def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "created_at": user["created_at"],
        "is_active": user["is_active"]
    }

def item_helper(item) -> dict:
    return {
        "id": str(item["_id"]),
        "title": item["title"],
        "description": item.get("description"),
        "price": item["price"],
        "category": item["category"],
        "user_id": item["user_id"],
        "created_at": item["created_at"],
        "updated_at": item["updated_at"]
    }

# Authentication Dependency (Basic implementation)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Implement your JWT validation logic here
    # For now, this is a placeholder
    return {"user_id": "placeholder_user_id"}

# Health Check Route
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# User Routes
@app.post("/api/v1/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, client: AsyncIOMotorClient = Depends(get_database)):
    # Check if user already exists
    existing_user = await client.fastapi_db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    user_dict = user.dict()
    user_dict["created_at"] = datetime.utcnow()
    user_dict["is_active"] = True
    # Hash password here in production
    
    result = await client.fastapi_db.users.insert_one(user_dict)
    new_user = await client.fastapi_db.users.find_one({"_id": result.inserted_id})
    
    return user_helper(new_user)

@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, client: AsyncIOMotorClient = Depends(get_database)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    user = await client.fastapi_db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_helper(user)

@app.get("/api/v1/users/", response_model=List[UserResponse])
async def get_users(skip: int = 0, limit: int = 10, client: AsyncIOMotorClient = Depends(get_database)):
    users = []
    cursor = client.fastapi_db.users.find().skip(skip).limit(limit)
    async for user in cursor:
        users.append(user_helper(user))
    return users

@app.put("/api/v1/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, 
    user_update: UserUpdate, 
    client: AsyncIOMotorClient = Depends(get_database),
    current_user = Depends(get_current_user)
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    result = await client.fastapi_db.users.update_one(
        {"_id": ObjectId(user_id)}, 
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = await client.fastapi_db.users.find_one({"_id": ObjectId(user_id)})
    return user_helper(updated_user)

@app.delete("/api/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str, 
    client: AsyncIOMotorClient = Depends(get_database),
    current_user = Depends(get_current_user)
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    result = await client.fastapi_db.users.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

# Item Routes
@app.post("/api/v1/items/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item: ItemCreate, 
    client: AsyncIOMotorClient = Depends(get_database),
    current_user = Depends(get_current_user)
):
    item_dict = item.dict()
    item_dict["created_at"] = datetime.utcnow()
    item_dict["updated_at"] = datetime.utcnow()
    
    result = await client.fastapi_db.items.insert_one(item_dict)
    new_item = await client.fastapi_db.items.find_one({"_id": result.inserted_id})
    
    return item_helper(new_item)

@app.get("/api/v1/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, client: AsyncIOMotorClient = Depends(get_database)):
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid item ID")
    
    item = await client.fastapi_db.items.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return item_helper(item)

@app.get("/api/v1/items/", response_model=List[ItemResponse])
async def get_items(
    skip: int = 0, 
    limit: int = 10, 
    category: Optional[str] = None,
    client: AsyncIOMotorClient = Depends(get_database)
):
    query = {}
    if category:
        query["category"] = category
    
    items = []
    cursor = client.fastapi_db.items.find(query).skip(skip).limit(limit)
    async for item in cursor:
        items.append(item_helper(item))
    return items

@app.put("/api/v1/items/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str, 
    item_update: ItemUpdate, 
    client: AsyncIOMotorClient = Depends(get_database),
    current_user = Depends(get_current_user)
):
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid item ID")
    
    update_data = {k: v for k, v in item_update.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await client.fastapi_db.items.update_one(
        {"_id": ObjectId(item_id)}, 
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    updated_item = await client.fastapi_db.items.find_one({"_id": ObjectId(item_id)})
    return item_helper(updated_item)

@app.delete("/api/v1/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str, 
    client: AsyncIOMotorClient = Depends(get_database),
    current_user = Depends(get_current_user)
):
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid item ID")
    
    result = await client.fastapi_db.items.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

# Search Route
@app.get("/api/v1/search/items/", response_model=List[ItemResponse])
async def search_items(
    q: str, 
    skip: int = 0, 
    limit: int = 10,
    client: AsyncIOMotorClient = Depends(get_database)
):
    query = {
        "$or": [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}}
        ]
    }
    
    items = []
    cursor = client.fastapi_db.items.find(query).skip(skip).limit(limit)
    async for item in cursor:
        items.append(item_helper(item))
    return items

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )