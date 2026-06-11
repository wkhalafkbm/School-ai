from fastapi import FastAPI

from app.routers import overview

app = FastAPI(title="University AI Operating Center")
app.include_router(overview.router)


@app.get("/health")
def health():
    return {"status": "ok"}
