# server.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
import os
from contextlib import asynccontextmanager

# Pydantic Models
class ContactMessage(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=1000)
    created_at: Optional[datetime] = None

class ContactMessageResponse(ContactMessage):
    id: str
    created_at: datetime

class NewsletterSubscription(BaseModel):
    email: EmailStr
    subscribed_at: Optional[datetime] = None

class NewsletterResponse(NewsletterSubscription):
    id: str
    subscribed_at: datetime

class LandingPageStats(BaseModel):
    total_visitors: int
    contact_messages: int
    newsletter_subscribers: int

# Database connection
class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def get_database():
    return db.database

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db.client = AsyncIOMotorClient(mongodb_url)
    db.database = db.client.landing_page_db
    
    # Test connection
    try:
        await db.client.admin.command('ping')
        print("Connected to MongoDB successfully!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
    
    yield
    
    # Shutdown
    if db.client:
        db.client.close()

# FastAPI app
app = FastAPI(
    title="Landing Page API",
    description="Backend API for a simple landing page with contact form and newsletter subscription",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Static files (for serving landing page assets if needed)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Routes

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve a simple landing page HTML"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome - Landing Page</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
            
            /* Header */
            header { background: #2c3e50; color: white; padding: 1rem 0; position: fixed; width: 100%; top: 0; z-index: 1000; }
            nav { display: flex; justify-content: space-between; align-items: center; }
            .logo { font-size: 1.5rem; font-weight: bold; }
            .nav-links { display: flex; list-style: none; gap: 2rem; }
            .nav-links a { color: white; text-decoration: none; }
            
            /* Hero Section */
            .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 8rem 0 4rem; text-align: center; }
            .hero h1 { font-size: 3rem; margin-bottom: 1rem; }
            .hero p { font-size: 1.2rem; margin-bottom: 2rem; }
            .cta-button { display: inline-block; background: #e74c3c; color: white; padding: 1rem 2rem; text-decoration: none; border-radius: 5px; font-weight: bold; }
            
            /* Contact Section */
            .contact { padding: 4rem 0; background: #f8f9fa; }
            .contact h2 { text-align: center; margin-bottom: 2rem; }
            .form-group { margin-bottom: 1rem; }
            .form-group label { display: block; margin-bottom: 0.5rem; }
            .form-group input, .form-group textarea { width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; }
            .submit-btn { background: #27ae60; color: white; padding: 0.75rem 2rem; border: none; border-radius: 5px; cursor: pointer; }
            
            /* Footer */
            footer { background: #2c3e50; color: white; text-align: center; padding: 2rem 0; }
        </style>
    </head>
    <body>
        <!-- Header -->
        <header>
            <nav class="container">
                <div class="logo">YourBrand</div>
                <ul class="nav-links">
                    <li><a href="#home">Home</a></li>
                    <li><a href="#about">About</a></li>
                    <li><a href="#contact">Contact</a></li>
                </ul>
            </nav>
        </header>

        <!-- Hero Section -->
        <section class="hero" id="home">
            <div class="container">
                <h1>Welcome to Our Amazing Service</h1>
                <p>Transform your business with our innovative solutions</p>
                <a href="#contact" class="cta-button">Get Started Today</a>
            </div>
        </section>

        <!-- Contact Section -->
        <section class="contact" id="contact">
            <div class="container">
                <h2>Get In Touch</h2>
                <form id="contactForm" style="max-width: 600px; margin: 0 auto;">
                    <div class="form-group">
                        <label for="name">Name:</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="subject">Subject:</label>
                        <input type="text" id="subject" name="subject" required>
                    </div>
                    <div class="form-group">
                        <label for="message">Message:</label>
                        <textarea id="message" name="message" rows="5" required></textarea>
                    </div>
                    <button type="submit" class="submit-btn">Send Message</button>
                </form>
            </div>
        </section>

        <!-- Footer -->
        <footer>
            <div class="container">
                <p>&copy; 2024 YourBrand. All rights reserved. | Follow us on social media</p>
            </div>
        </footer>

        <script>
            document.getElementById('contactForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData);
                
                try {
                    const response = await fetch('/api/contact', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    
                    if (response.ok) {
                        alert('Message sent successfully!');
                        e.target.reset();
                    } else {
                        alert('Failed to send message. Please try again.');
                    }
                } catch (error) {
                    alert('Error sending message. Please try again.');
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/api/contact", response_model=ContactMessageResponse)
async def submit_contact_form(
    contact_data: ContactMessage,
    database = Depends(get_database)
):
    """Submit contact form message"""
    try:
        # Add timestamp
        contact_data.created_at = datetime.utcnow()
        
        # Insert into MongoDB
        result = await database.contact_messages.insert_one(contact_data.model_dump())
        
        # Retrieve the inserted document
        inserted_doc = await database.contact_messages.find_one({"_id": result.inserted_id})
        
        # Convert ObjectId to string
        inserted_doc["id"] = str(inserted_doc["_id"])
        del inserted_doc["_id"]
        
        return ContactMessageResponse(**inserted_doc)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit contact form: {str(e)}")

@app.get("/api/contact", response_model=List[ContactMessageResponse])
async def get_contact_messages(
    skip: int = 0,
    limit: int = 10,
    database = Depends(get_database)
):
    """Get all contact messages (admin endpoint)"""
    try:
        cursor = database.contact_messages.find().sort("created_at", -1).skip(skip).limit(limit)
        messages = []
        
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            messages.append(ContactMessageResponse(**doc))
        
        return messages
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve contact messages: {str(e)}")

@app.post("/api/newsletter", response_model=NewsletterResponse)
async def subscribe_newsletter(
    subscription: NewsletterSubscription,
    database = Depends(get_database)
):
    """Subscribe to newsletter"""
    try:
        # Check if email already exists
        existing = await database.newsletter_subscriptions.find_one({"email": subscription.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already subscribed")
        
        # Add timestamp
        subscription.subscribed_at = datetime.utcnow()
        
        # Insert into MongoDB
        result = await database.newsletter_subscriptions.insert_one(subscription.model_dump())
        
        # Retrieve the inserted document
        inserted_doc = await database.newsletter_subscriptions.find_one({"_id": result.inserted_id})
        
        # Convert ObjectId to string
        inserted_doc["id"] = str(inserted_doc["_id"])
        del inserted_doc["_id"]
        
        return NewsletterResponse(**inserted_doc)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe to newsletter: {str(e)}")

@app.get("/api/newsletter", response_model=List[NewsletterResponse])
async def get_newsletter_subscribers(
    skip: int = 0,
    limit: int = 10,
    database = Depends(get_database)
):
    """Get newsletter subscribers (admin endpoint)"""
    try:
        cursor = database.newsletter_subscriptions.find().sort("subscribed_at", -1).skip(skip).limit(limit)
        subscribers = []
        
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            subscribers.append(NewsletterResponse(**doc))
        
        return subscribers
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve newsletter subscribers: {str(e)}")

@app.delete("/api/newsletter/{email}")
async def unsubscribe_newsletter(
    email: str,
    database = Depends(get_database)
):
    """Unsubscribe from newsletter"""
    try:
        result = await database.newsletter_subscriptions.delete_one({"email": email})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Email not found in subscribers")
        
        return {"message": "Successfully unsubscribed", "email": email}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe: {str(e)}")

@app.get("/api/stats", response_model=LandingPageStats)
async def get_landing_page_stats(database = Depends(get_database)):
    """Get landing page statistics"""
    try:
        contact_count = await database.contact_messages.count_documents({})
        newsletter_count = await database.newsletter_subscriptions.count_documents({})
        
        # For visitors, you might want to implement a separate tracking mechanism
        # For now, we'll use a placeholder
        total_visitors = contact_count + newsletter_count  # Simplified calculation
        
        return LandingPageStats(
            total_visitors=total_visitors,
            contact_messages=contact_count,
            newsletter_subscribers=newsletter_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )