"""
HeartChain Backend API

A blockchain-based crowdfunding platform.
- Source of Truth: Shardeum Blockchain
- Storage: IPFS
- Backend: Stateless coordinator
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.campaigns import router as campaign_router
# from routes.donations import router as donation_router
# from routes.impact import router as impact_router
# from routes.badges import router as badge_router
from routes.admin import router as admin_router
from routes.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # No database connection needed!
    print("HeartChain Backend (Stateless) Starting...")
    yield
    print("HeartChain Backend (Stateless) Shutdown.")


app = FastAPI(
    title="HeartChain API",
    description="""
## HeartChain - Decentralized & Stateless API

- **Blockchain**: Shardeum (EVM)
- **Storage**: IPFS (Metadata & Documents)
- **Privacy**: AES-256 Encryption for sensitive data in IPFS JSON
    """,
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(campaign_router)
# app.include_router(donation_router)
# app.include_router(impact_router)
# app.include_router(badge_router)
app.include_router(admin_router)
# Documents router might need refactoring too, but we keep it for now as it handles IPFS upload logic
app.include_router(documents_router)


@app.get("/", tags=["Health"])
def read_root():
    """Root endpoint."""
    return {
        "app": "HeartChain API (Decentralized)",
        "version": "3.0.0",
        "status": "running",
        "mode": "stateless"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Verifies simple connectivity.
    """
    return {
        "status": "ok",
        "database": "removed (stateless)",
    }
