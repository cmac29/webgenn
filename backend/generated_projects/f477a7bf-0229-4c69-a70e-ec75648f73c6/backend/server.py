# server.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Pydantic models
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

class ServiceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price_range: Optional[str] = Field(None, max_length=50)
    duration: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    is_active: bool = Field(default=True)

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price_range: Optional[str] = Field(None, max_length=50)
    duration: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

class Service(ServiceBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Database connection
class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def get_database():
    return db.database

async def connect_to_mongo():
    """Create database connection"""
    db.client = AsyncIOMotorClient(
        os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    )
    db.database = db.client[os.getenv("DATABASE_NAME", "flooring_services")]

async def close_mongo_connection():
    """Close database connection"""
    db.client.close()

# FastAPI app
app = FastAPI(
    title="Flooring Services API",
    description="API for managing flooring services including epoxy flooring",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Events
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    
    # Insert default services including epoxy flooring
    services_collection = db.database["services"]
    
    # Check if services already exist
    existing_count = await services_collection.count_documents({})
    
    if existing_count == 0:
        default_services = [
            {
                "name": "Epoxy Flooring",
                "description": "High-quality epoxy floor coating for garages, warehouses, and commercial spaces. Durable, chemical-resistant, and easy to maintain.",
                "price_range": "$3-8 per sq ft",
                "duration": "1-3 days",
                "category": "Commercial/Industrial",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "name": "Hardwood Installation",
                "description": "Professional hardwood flooring installation with premium materials and expert craftsmanship.",
                "price_range": "$8-15 per sq ft",
                "duration": "2-5 days",
                "category": "Residential",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "name": "Tile Installation",
                "description": "Ceramic, porcelain, and natural stone tile installation for kitchens, bathrooms, and living spaces.",
                "price_range": "$5-20 per sq ft",
                "duration": "2-4 days",
                "category": "Residential",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "name": "Carpet Installation",
                "description": "Professional carpet installation with padding and finishing for residential and commercial properties.",
                "price_range": "$3-10 per sq ft",
                "duration": "1-2 days",
                "category": "Residential",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "name": "Vinyl/LVP Installation",
                "description": "Luxury vinyl plank and vinyl flooring installation. Waterproof and durable solution for any room.",
                "price_range": "$4-12 per sq ft",
                "duration": "1-3 days",
                "category": "Residential",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        await services_collection.insert_many(default_services)

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Flooring Services API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/services", response_model=List[Service])
async def get_services(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    database=Depends(get_database)
):
    """Get all services with optional filtering"""
    collection = database["services"]
    
    # Build filter
    filter_dict = {}
    if category:
        filter_dict["category"] = {"$regex": category, "$options": "i"}
    if is_active is not None:
        filter_dict["is_active"] = is_active
    
    # Get services
    cursor = collection.find(filter_dict).skip(skip).limit(limit).sort("created_at", -1)
    services = await cursor.to_list(length=limit)
    
    return services

@app.get("/services/{service_id}", response_model=Service)
async def get_service(service_id: str, database=Depends(get_database)):
    """Get a specific service by ID"""
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=400, detail="Invalid service ID format")
    
    collection = database["services"]
    service = await collection.find_one({"_id": ObjectId(service_id)})
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return service

@app.post("/services", response_model=Service, status_code=201)
async def create_service(service: ServiceCreate, database=Depends(get_database)):
    """Create a new service"""
    collection = database["services"]
    
    # Check if service with same name already exists
    existing = await collection.find_one({"name": {"$regex": f"^{service.name}$", "$options": "i"}})
    if existing:
        raise HTTPException(status_code=400, detail="Service with this name already exists")
    
    # Create service document
    service_dict = service.dict()
    service_dict["created_at"] = datetime.utcnow()
    service_dict["updated_at"] = datetime.utcnow()
    
    result = await collection.insert_one(service_dict)
    
    # Get the created service
    created_service = await collection.find_one({"_id": result.inserted_id})
    return created_service

@app.put("/services/{service_id}", response_model=Service)
async def update_service(
    service_id: str,
    service_update: ServiceUpdate,
    database=Depends(get_database)
):
    """Update a service"""
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=400, detail="Invalid service ID format")
    
    collection = database["services"]
    
    # Check if service exists
    existing_service = await collection.find_one({"_id": ObjectId(service_id)})
    if not existing_service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Prepare update data
    update_data = {k: v for k, v in service_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    # Check for name conflicts if name is being updated
    if "name" in update_data:
        name_conflict = await collection.find_one({
            "name": {"$regex": f"^{update_data['name']}$", "$options": "i"},
            "_id": {"$ne": ObjectId(service_id)}
        })
        if name_conflict:
            raise HTTPException(status_code=400, detail="Service with this name already exists")
    
    update_data["updated_at"] = datetime.utcnow()
    
    # Update service
    await collection.update_one(
        {"_id": ObjectId(service_id)},
        {"$set": update_data}
    )
    
    # Return updated service
    updated_service = await collection.find_one({"_id": ObjectId(service_id)})
    return updated_service

@app.delete("/services/{service_id}")
async def delete_service(service_id: str, database=Depends(get_database)):
    """Delete a service"""
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=400, detail="Invalid service ID format")
    
    collection = database["services"]
    
    # Check if service exists
    existing_service = await collection.find_one({"_id": ObjectId(service_id)})
    if not existing_service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Delete service
    result = await collection.delete_one({"_id": ObjectId(service_id)})
    
    if result.deleted_count == 1:
        return {"message": "Service deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete service")

@app.get("/services/category/{category}", response_model=List[Service])
async def get_services_by_category(
    category: str,
    skip: int = 0,
    limit: int = 100,
    database=Depends(get_database)
):
    """Get services by category"""
    collection = database["services"]
    
    cursor = collection.find({
        "category": {"$regex": category, "$options": "i"},
        "is_active": True
    }).skip(skip).limit(limit).sort("name", 1)
    
    services = await cursor.to_list(length=limit)
    return services

@app.get("/services/search/{query}", response_model=List[Service])
async def search_services(
    query: str,
    skip: int = 0,
    limit: int = 100,
    database=Depends(get_database)
):
    """Search services by name or description"""
    collection = database["services"]
    
    search_filter = {
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ],
        "is_active": True
    }
    
    cursor = collection.find(search_filter).skip(skip).limit(limit)
    services = await cursor.to_list(length=limit)
    return services

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )