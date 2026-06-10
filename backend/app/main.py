from fastapi import FastAPI

app = FastAPI(title="University AI Operating Center")


@app.get("/health")
def health():
    return {"status": "ok"}
