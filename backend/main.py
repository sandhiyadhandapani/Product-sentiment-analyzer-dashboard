from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.products import router as products_router
from routers.sentiment import router as sentiment_router

app = FastAPI(
    title="Product Sentiment Analyzer API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "status": "Backend Running",
        "message": "Product Sentiment Analyzer API",
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(sentiment_router)


@app.get("/api/health", include_in_schema=False)
async def health_check():
    return {"status": "ok", "message": "Backend is running"}
