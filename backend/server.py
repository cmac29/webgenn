from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import uuid
import base64

# Import services
from s3_service import S3Service
from ai_service import AIService
from project_manager import ProjectManager

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize services
s3_service = S3Service(
    access_key=os.getenv('AWS_ACCESS_KEY_ID'),
    secret_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region=os.getenv('AWS_REGION', 'us-east-1'),
    bucket_name=os.getenv('S3_BUCKET_NAME', 'code-weaver-assets')
)

ai_service = AIService(
    api_key=os.getenv('EMERGENT_LLM_KEY')
)

# Initialize project manager
project_manager = ProjectManager()

# Create the main app
app = FastAPI(title="Code Weaver API")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class Session(BaseModel):
    model_config = ConfigDict(extra="ignore")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str = "Untitled Project"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProjectFile(BaseModel):
    """Represents a single file in the generated project"""
    filename: str
    content: str
    file_type: str  # 'html', 'css', 'js', 'python', 'json', 'md'
    description: str = ""

class GeneratedWebsite(BaseModel):
    model_config = ConfigDict(extra="ignore")
    website_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    html_content: Optional[str] = None
    css_content: Optional[str] = None
    js_content: Optional[str] = None
    python_backend: Optional[str] = None
    requirements_txt: Optional[str] = None
    package_json: Optional[str] = None
    readme: Optional[str] = None
    framework: str = "html"  # html, react, or nextjs
    preview_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    structure: Optional[Dict[str, Any]] = None
    files: Optional[List[Dict[str, Any]]] = None  # List of all project files

class UploadedAsset(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    file_url: str
    file_type: str
    original_filename: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request/Response Models
class SessionCreate(BaseModel):
    project_name: Optional[str] = "Untitled Project"

class ChatRequest(BaseModel):
    session_id: str
    message: str
    model: str = "gpt-5"  # changed default to gpt-5

class ChatResponse(BaseModel):
    message_id: str
    content: str
    website_data: Optional[GeneratedWebsite] = None
    image_urls: Optional[List[str]] = None

class GenerateWebsiteRequest(BaseModel):
    session_id: str
    prompt: str
    model: str = "gpt-5"  # changed default to gpt-5
    framework: str = "html"

# API Endpoints

@api_router.get("/")
async def root():
    return {"message": "Code Weaver API", "status": "running"}

@api_router.post("/session/create", response_model=Session)
async def create_session(input: SessionCreate):
    """Create a new session"""
    session = Session(project_name=input.project_name)
    
    doc = session.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['last_updated'] = doc['last_updated'].isoformat()
    
    await db.sessions.insert_one(doc)
    logger.info(f"Created session: {session.session_id}")
    
    return session

@api_router.get("/session/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """Get session details"""
    session_doc = await db.sessions.find_one({"session_id": session_id}, {"_id": 0})
    
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if isinstance(session_doc['created_at'], str):
        session_doc['created_at'] = datetime.fromisoformat(session_doc['created_at'])
    if isinstance(session_doc['last_updated'], str):
        session_doc['last_updated'] = datetime.fromisoformat(session_doc['last_updated'])
    
    return Session(**session_doc)

@api_router.get("/session/{session_id}/messages", response_model=List[Message])
async def get_session_messages(session_id: str):
    """Get all messages for a session"""
    messages = await db.messages.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", 1).to_list(1000)
    
    for msg in messages:
        if isinstance(msg['timestamp'], str):
            msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
    
    return [Message(**msg) for msg in messages]

@api_router.post("/chat/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message and get AI response"""
    # Save user message
    user_message = Message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    
    user_doc = user_message.model_dump()
    user_doc['timestamp'] = user_doc['timestamp'].isoformat()
    await db.messages.insert_one(user_doc)
    
    # Get the latest generated website code for context
    latest_website = None
    try:
        websites = await db.generated_websites.find(
            {"session_id": request.session_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(1).to_list(1)
        
        if websites:
            latest_website = websites[0]
            logger.info(f"Found latest website for session {request.session_id}")
    except Exception as e:
        logger.warning(f"Could not retrieve latest website: {str(e)}")
    
    # Get AI response with website context
    ai_response = await ai_service.generate_response(
        prompt=request.message,
        model=request.model,
        session_id=request.session_id,
        current_website=latest_website
    )
    
    # Save AI message
    assistant_message = Message(
        session_id=request.session_id,
        role="assistant",
        content=ai_response['content']
    )
    
    assistant_doc = assistant_message.model_dump()
    assistant_doc['timestamp'] = assistant_doc['timestamp'].isoformat()
    await db.messages.insert_one(assistant_doc)
    
    # Update session timestamp
    await db.sessions.update_one(
        {"session_id": request.session_id},
        {"$set": {"last_updated": datetime.now(timezone.utc).isoformat()}}
    )
    
    return ChatResponse(
        message_id=assistant_message.message_id,
        content=ai_response['content'],
        website_data=ai_response.get('website_data'),
        image_urls=ai_response.get('image_urls')
    )

@api_router.post("/generate/website", response_model=GeneratedWebsite)
async def generate_website(request: GenerateWebsiteRequest):
    """Generate complete website with backend and save to file system"""
    logger.info(f"Generating website for session {request.session_id}")
    
    # Get conversation history
    messages = await db.messages.find(
        {"session_id": request.session_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(100)
    
    # Get the latest generated website for context (for iterative editing)
    current_website = None
    try:
        websites = await db.generated_websites.find(
            {"session_id": request.session_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(1).to_list(1)
        
        if websites:
            current_website = websites[0]
            logger.info(f"Found existing website for session {request.session_id} - will use for iterative editing")
    except Exception as e:
        logger.warning(f"Could not retrieve existing website: {str(e)}")
    
    # Generate website using AI with full project structure
    website_data = await ai_service.generate_complete_project(
        prompt=request.prompt,
        model=request.model,
        framework=request.framework,
        conversation_history=messages,
        current_website=current_website
    )
    
    # Save files to disk for proper serving
    file_paths = project_manager.save_project_files(
        session_id=request.session_id,
        html_content=website_data.get('html_content', ''),
        css_content=website_data.get('css_content', ''),
        js_content=website_data.get('js_content', ''),
        python_backend=website_data.get('python_backend'),
        requirements_txt=website_data.get('requirements_txt'),
        package_json=website_data.get('package_json'),
        readme=website_data.get('readme')
    )
    
    logger.info(f"Saved project files to disk: {file_paths}")
    
    # Generate preview URL
    preview_url = f"/api/preview/{request.session_id}/"
    
    # Save generated website to database
    website = GeneratedWebsite(
        session_id=request.session_id,
        html_content=website_data.get('html_content'),
        css_content=website_data.get('css_content'),
        js_content=website_data.get('js_content'),
        python_backend=website_data.get('python_backend'),
        requirements_txt=website_data.get('requirements_txt'),
        package_json=website_data.get('package_json'),
        readme=website_data.get('readme'),
        framework=request.framework,
        preview_url=preview_url,
        structure=website_data.get('structure'),
        files=website_data.get('files', [])
    )
    
    doc = website.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.generated_websites.insert_one(doc)
    
    logger.info(f"Website saved with {len(website.files or [])} files, preview: {preview_url}")
    
    return website

@api_router.get("/website/{session_id}/latest", response_model=GeneratedWebsite)
async def get_latest_website(session_id: str):
    """Get the latest generated website for a session"""
    websites = await db.generated_websites.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(1).to_list(1)
    
    if not websites:
        raise HTTPException(status_code=404, detail="No website found for this session")
    
    website_doc = websites[0]
    
    if isinstance(website_doc['created_at'], str):
        website_doc['created_at'] = datetime.fromisoformat(website_doc['created_at'])
    
    return GeneratedWebsite(**website_doc)

@api_router.post("/upload/asset")
async def upload_asset(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """Upload an asset file"""
    try:
        # Upload to S3
        file_url = await s3_service.upload_file(file, folder=f"sessions/{session_id}")
        
        # Save asset metadata
        asset = UploadedAsset(
            session_id=session_id,
            file_url=file_url,
            file_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "unknown"
        )
        
        doc = asset.model_dump()
        doc['uploaded_at'] = doc['uploaded_at'].isoformat()
        await db.uploaded_assets.insert_one(doc)
        
        return {"asset_id": asset.asset_id, "file_url": file_url}
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@api_router.get("/assets/{session_id}")
async def get_session_assets(session_id: str):
    """Get all assets for a session"""
    assets = await db.uploaded_assets.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(100)
    
    return {"assets": assets}

@api_router.post("/generate/image")
async def generate_image(prompt: str = Form(...), session_id: str = Form(...)):
    """Generate an image using AI"""
    try:
        image_url = await ai_service.generate_image(prompt)
        return {"image_url": image_url, "prompt": prompt}
    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

@api_router.get("/models")
async def get_available_models():
    """Get list of available AI models"""
    return {
        "models": [
            {"id": "gpt-5", "name": "GPT-5", "provider": "openai", "recommended": True},
            {"id": "claude-sonnet-4", "name": "Claude Sonnet 4", "provider": "anthropic", "recommended": True},
            {"id": "gpt-5-mini", "name": "GPT-5 Mini", "provider": "openai"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "gemini"}
        ]
    }

# ============================================================================
# PREVIEW ENDPOINTS - Serve generated projects as proper websites
# ============================================================================

@api_router.get("/preview/{session_id}/")
@api_router.get("/preview/{session_id}/index.html")
async def preview_html(session_id: str):
    """Serve the main HTML file for a project"""
    project_dir = project_manager.get_project_dir(session_id)
    html_path = project_dir / "index.html"
    
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    return FileResponse(html_path, media_type="text/html")

@api_router.get("/preview/{session_id}/static/styles.css")
async def preview_css(session_id: str):
    """Serve the CSS file for a project"""
    project_dir = project_manager.get_project_dir(session_id)
    css_path = project_dir / "static" / "styles.css"
    
    if not css_path.exists():
        raise HTTPException(status_code=404, detail="CSS file not found")
    
    return FileResponse(css_path, media_type="text/css")

@api_router.get("/preview/{session_id}/static/app.js")
async def preview_js(session_id: str):
    """Serve the JavaScript file for a project"""
    project_dir = project_manager.get_project_dir(session_id)
    js_path = project_dir / "static" / "app.js"
    
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="JavaScript file not found")
    
    return FileResponse(js_path, media_type="application/javascript")

@api_router.post("/preview/{session_id}/backend/start")
async def start_project_backend(session_id: str):
    """Start the generated backend server for a project"""
    result = project_manager.start_backend(session_id)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result

@api_router.post("/preview/{session_id}/backend/stop")
async def stop_project_backend(session_id: str):
    """Stop the generated backend server for a project"""
    result = project_manager.stop_backend(session_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()