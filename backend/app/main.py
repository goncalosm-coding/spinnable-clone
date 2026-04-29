from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import workers, webhooks, chat, tenants

app = FastAPI(title="AI Workers Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenants.router, prefix="/api")
app.include_router(workers.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}