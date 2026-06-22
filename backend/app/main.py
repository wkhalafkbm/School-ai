from fastapi import FastAPI

from app.routers import admissions, overview, recommendations, workflows

app = FastAPI(title="University AI Operating Center")
app.include_router(admissions.router)
app.include_router(overview.router)
app.include_router(recommendations.router)
app.include_router(workflows.router)


@app.get("/health")
def health():
    return {"status": "ok"}
