from fastapi import FastAPI

from app.routers import admissions, enrollment, overview, recommendations, workflows
from app.routers import students, programs, courses, cohorts, faculty, alumni
from app.routers import teaching_readiness, academic_risk, progression

app = FastAPI(title="University AI Operating Center")
app.include_router(admissions.router)
app.include_router(enrollment.router)
app.include_router(overview.router)
app.include_router(recommendations.router)
app.include_router(workflows.router)
app.include_router(students.router)
app.include_router(programs.router)
app.include_router(courses.router)
app.include_router(cohorts.router)
app.include_router(faculty.router)
app.include_router(alumni.router)
app.include_router(teaching_readiness.router)
app.include_router(academic_risk.router)
app.include_router(progression.router)


@app.get("/health")
def health():
    return {"status": "ok"}
