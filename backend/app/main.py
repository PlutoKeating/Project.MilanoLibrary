from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import summarize, cache, upload, models, books, notes, auth

app = FastAPI(
    title="MilanoLibrary Backend",
    description="FastAPI backend for MilanoLibrary video summarization",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(summarize.router)
app.include_router(cache.router)
app.include_router(upload.router)
app.include_router(models.router)
app.include_router(books.router)
app.include_router(notes.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.backend_port, reload=True)
