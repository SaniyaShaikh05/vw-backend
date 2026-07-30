from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

# Alert routes are currently implemented under patients.py and doctors.py 
# as per the API endpoint requirements grouping.
