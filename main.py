import os
import sys
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config.firebase import get_firebase_status
from backend.services.firestore_service import FirestoreService
from backend.services.personalization import PersonalizationEngine
from backend.services.ai_service import AIService
from backend.collector.rss_collector import ThreatCollector
from backend.scripts.seed_threats import seed_database
from backend.scripts.validate_database import run_validation

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("trinetra.main")

app = FastAPI(
    title="TRINETRA — Cyber Threat Intelligence Platform API",
    description="Community-Centric AI-Powered Cyber Threat Intelligence REST API",
    version="2.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8001",
        "http://localhost:8001",
        "http://127.0.0.1:3000",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
db_service = FirestoreService()
personalization_engine = PersonalizationEngine(db_service)
ai_service = AIService()

# Auto-seed database on startup if threats are empty
@app.on_event("startup")
def startup_event():
    try:
        stats = db_service.get_database_stats()
        if stats["total_threats"] < 60:
            logger.info("Initializing automatic seeding to ensure 60 community threats...")
            seed_database()
        else:
            logger.info(f"Database ready with {stats['total_threats']} threats.")
    except Exception as e:
        logger.error(f"Startup error: {e}")

# --- SCHEMAS ---
class UserRegisterModel(BaseModel):
    name: str = Field(..., example="Ananya Sharma")
    email: str = Field(..., example="ananya@student.edu")
    password: str = Field(..., min_length=6, example="SecurePass123!")
    community: str = Field(..., example="STUDENT")
    region: Optional[str] = Field("National", example="Delhi / National")
    language: Optional[str] = Field("English", example="English")
    notification_preference: Optional[bool] = True

class UserLoginModel(BaseModel):
    email: str = Field(..., example="ananya@student.edu")
    password: str = Field(..., example="SecurePass123!")

class ReportModel(BaseModel):
    user_id: Optional[str] = "anonymous"
    community: str = Field(..., example="STUDENT")
    threat_type: str = Field(..., example="Fake Internship Scam")
    description: str = Field(..., example="Received suspicious WhatsApp message asking for ₹500 fee")
    platform: str = Field("WhatsApp", example="WhatsApp")
    url_or_phone: Optional[str] = "+91 9876543210"
    region: Optional[str] = "Delhi"

class ReviewModel(BaseModel):
    threat_id: str = Field(..., example="threat_fake_internship")
    threat_title: str = Field(..., example="Fake Internship Scam")
    user_alias: Optional[str] = "Concerned Student"
    community: str = Field("STUDENT", example="STUDENT")
    experience_text: str = Field(..., example="I received a similar message last week asking for payment...")
    platform: Optional[str] = "WhatsApp"
    action_taken: Optional[str] = "Reported & Blocked"

class ChatRequestModel(BaseModel):
    message: str = Field(..., example="I got an internship message asking for ₹500.")
    community: str = Field("STUDENT", example="STUDENT")
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None

# --- HEALTH & STATUS ENDPOINTS ---
@app.get("/health/firebase")
def health_firebase():
    """Verify Firebase Initialization & Firestore Connection"""
    return get_firebase_status()

@app.get("/health/database")
def health_database():
    """Detailed Database Validation (60 Threats Statistics)"""
    stats = db_service.get_database_stats()
    status = get_firebase_status()
    stats["firebase_status"] = status
    return stats

@app.get("/api/health/validate")
def run_full_validation():
    """Run full 10-point validation suite"""
    passed = run_validation()
    stats = db_service.get_database_stats()
    return {"status": "SUCCESS" if passed else "FAILED", "details": stats}

# --- AUTHENTICATION ENDPOINTS ---
@app.post("/api/auth/register")
def register_user(user: UserRegisterModel):
    existing = db_service.get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    created = db_service.create_user(user.dict())
    return {"message": "User registered successfully", "user": created}

@app.post("/api/auth/login")
def login_user(cred: UserLoginModel):
    user = db_service.get_user_by_email(cred.email)
    if not user:
        # Auto-create user for demo convenience if email not found
        demo_user = {
            "name": cred.email.split("@")[0].capitalize(),
            "email": cred.email,
            "community": "STUDENT",
            "region": "National",
            "language": "English"
        }
        user = db_service.create_user(demo_user)
    
    return {"message": "Login successful", "user": user}

# --- THREAT INTELLIGENCE ENDPOINTS ---
@app.get("/api/threats")
def list_threats(
    query: Optional[str] = Query(None),
    community: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    threat_type: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    region: Optional[str] = Query(None)
):
    results = db_service.search_threats(
        query=query or "",
        community=community,
        severity=severity,
        threat_type=threat_type,
        platform=platform,
        region=region
    )
    return {"total": len(results), "threats": results}

@app.get("/api/threats/community/{community}")
def get_threats_by_community(community: str):
    results = db_service.get_threats_by_community(community)
    return {"community": community.upper(), "total": len(results), "threats": results}

@app.get("/api/threats/{threat_id}")
def get_threat_details(threat_id: str):
    threat = db_service.get_threat(threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Threat document not found")
    return threat

# --- PERSONALIZED DASHBOARD ENDPOINT ---
@app.get("/api/dashboard")
def get_dashboard(user_id: Optional[str] = Query(None), community: Optional[str] = Query(None)):
    """Personalized Threat Feed based on Logged-In User Community"""
    dash_data = personalization_engine.get_personalized_dashboard(user_id=user_id, community_override=community)
    return dash_data

# --- REPORTING ENDPOINTS ---
@app.post("/api/reports")
def submit_report(report: ReportModel):
    created = db_service.create_report(report.dict())
    return {"message": "Report submitted successfully", "report": created}

@app.get("/api/reports")
def get_reports(user_id: Optional[str] = Query(None)):
    reports = db_service.get_reports(user_id=user_id)
    return {"total": len(reports), "reports": reports}

# --- COMMUNITY REVIEWS & EXPERIENCES ---
@app.post("/api/reviews")
def submit_review(review: ReviewModel):
    created = db_service.create_review(review.dict())
    return {"message": "Experience shared successfully", "review": created}

@app.get("/api/reviews")
def get_reviews(threat_id: Optional[str] = Query(None), community: Optional[str] = Query(None)):
    reviews = db_service.get_reviews(threat_id=threat_id, community=community)
    return {"total": len(reviews), "reviews": reviews}

# --- ALERTS ENDPOINTS ---
@app.get("/api/alerts")
def get_alerts(community: Optional[str] = Query(None), user_id: Optional[str] = Query(None)):
    alerts = db_service.get_user_alerts(user_id=user_id, community=community)
    return {"total": len(alerts), "alerts": alerts}

@app.post("/api/alerts/{alert_id}/read")
def mark_alert_read(alert_id: str):
    success = db_service.mark_alert_read(alert_id)
    return {"success": success}

# --- AI ASSISTANT ENDPOINT ---
@app.post("/api/chat")
@app.post("/api/ai/chat")
def ai_chat(chat_data: ChatRequestModel):
    logger.info(f"[AI] Received message: '{chat_data.message}', community: {chat_data.community}, cid: {chat_data.conversation_id}")
    try:
        res = ai_service.generate_chat_response(
            message=chat_data.message,
            community=chat_data.community,
            conversation_id=chat_data.conversation_id
        )
        if isinstance(res, dict):
            response_text = res.get("response", "")
            cid = res.get("conversation_id", chat_data.conversation_id)
        else:
            response_text = res
            cid = chat_data.conversation_id

        return {
            "success": True,
            "response": response_text,
            "message": response_text,
            "ai_response": response_text,
            "community": chat_data.community.upper(),
            "conversation_id": cid
        }
    except Exception as e:
        logger.error(f"[AI] Error generating AI response: {e}")
        return {
            "success": False,
            "response": "Unable to get a response right now. Please try again.",
            "message": "Unable to get a response right now. Please try again.",
            "ai_response": "Unable to get a response right now. Please try again.",
            "conversation_id": chat_data.conversation_id
        }

# --- ADMIN PIPELINE ENDPOINTS ---
@app.post("/api/admin/seed")
def trigger_seed():
    seed_database()
    return {"message": "Database re-seeded successfully", "stats": db_service.get_database_stats()}

@app.post("/api/admin/collect-feeds")
def trigger_rss_collector():
    collector = ThreatCollector()
    res = collector.fetch_and_process_feeds()
    stats = db_service.get_database_stats()
    return {"message": "OSINT feed collection completed", "collector_results": res, "stats": stats}

# --- FRONTEND STATIC FILE SERVING ---
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    def serve_frontend_root():
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        index_public = os.path.join(frontend_path, "public", "index.html")
        if os.path.exists(index_public):
            return FileResponse(index_public)
        return {"message": "TRINETRA API Running. Frontend directory found."}

    @app.get("/{full_path:path}")
    def serve_frontend_fallback(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("health/"):
            raise HTTPException(status_code=404, detail="API route not found")
        
        target = os.path.join(frontend_path, full_path)
        if os.path.exists(target) and os.path.isfile(target):
            return FileResponse(target)
        
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        index_public = os.path.join(frontend_path, "public", "index.html")
        if os.path.exists(index_public):
            return FileResponse(index_public)
        return {"message": "TRINETRA API Operational"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "127.0.0.1")
    logger.info(f"Starting TRINETRA server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
