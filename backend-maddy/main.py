from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import connect_to_mongo, close_mongo_connection, db
from routes.campaigns import router as campaign_router
from routes.donations import router as donation_router
from routes.impact import router as impact_router
from routes.badges import router as badge_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title="HeartChain API",
    description="Backend API for HeartChain Blockchain Crowdfunding Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(campaign_router)
app.include_router(donation_router)
app.include_router(impact_router)
app.include_router(badge_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
async def health_check():
    try:
        # Ping the database to verify connection
        await db.client.admin.command('ping')
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": "disconnected", "detail": str(e)}
