"""
HeartChain Backend API

A blockchain-based crowdfunding platform with application-level encryption
for sensitive data and IPFS document storage.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import connect_to_mongo, close_mongo_connection, db
from routes.campaigns import router as campaign_router
from routes.donations import router as donation_router
from routes.impact import router as impact_router
from routes.badges import router as badge_router
from routes.admin import router as admin_router
from routes.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="HeartChain API",
    description="""
## HeartChain - Blockchain Crowdfunding Platform

A secure, transparent crowdfunding platform with:
- **Two campaign types**: Individual (personal emergencies) and Charity (NGO/organizations)
- **Application-level encryption**: Sensitive data encrypted with AES-256-GCM before storage
- **IPFS document storage**: Supporting documents encrypted and stored on IPFS
- **Admin verification workflow**: All campaigns verified before going live
- **Blockchain integration**: Transaction hashes recorded for transparency

### Security Features
- Sensitive PII fields encrypted in MongoDB
- Documents encrypted before IPFS upload
- Admin-only access to decrypted data
- Full audit logging for compliance
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(campaign_router)
app.include_router(donation_router)
app.include_router(impact_router)
app.include_router(badge_router)
app.include_router(admin_router)
app.include_router(documents_router)


@app.get("/", tags=["Health"])
def read_root():
    """Root endpoint."""
    return {
        "app": "HeartChain API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Verifies database connectivity and encryption configuration.
    """
    from core.config import settings
    
    health = {
        "status": "ok",
        "database": "unknown",
        "encryption": "unknown"
    }
    
    # Check database
    try:
        await db.client.admin.command('ping')
        health["database"] = "connected"
    except Exception as e:
        health["status"] = "degraded"
        health["database"] = f"disconnected: {str(e)}"
    
    # Check encryption key
    if settings.ENCRYPTION_KEY:
        if len(settings.ENCRYPTION_KEY) == 64:  # 32 bytes = 64 hex chars
            health["encryption"] = "configured"
        else:
            health["status"] = "degraded"
            health["encryption"] = "invalid key length"
    else:
        health["status"] = "degraded"
        health["encryption"] = "not configured"
    
    return health
