from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import close_mongo_connection, connect_to_mongo, ping_database
from routers.dashboard import router as dashboard_router
from routers.products import router as products_router
from routers.sentiment import router as sentiment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await connect_to_mongo()
        app.state.db_ready = await ping_database()
        app.state.db_error = None
    except Exception as exc:
        app.state.db_ready = False
        app.state.db_error = str(exc)
    yield
    await close_mongo_connection()


app = FastAPI(
    title="Product Sentiment Analyzer API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "status": "Backend Running",
        "message": "Product Sentiment Analyzer API",
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(sentiment_router)
app.include_router(dashboard_router)


@app.get("/api/health", include_in_schema=False)
async def health_check():
    return {
        "status": "ok" if getattr(app.state, "db_ready", False) else "degraded",
        "message": "Backend is running",
        "mongodb": {
            "ready": getattr(app.state, "db_ready", False),
            "error": getattr(app.state, "db_error", None),
        },
    }
