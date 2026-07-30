from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import auth, patients, doctors, devices, readings, alerts

settings = get_settings()

app = FastAPI(title="VitalWatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(devices.router)
app.include_router(readings.router)
app.include_router(alerts.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
