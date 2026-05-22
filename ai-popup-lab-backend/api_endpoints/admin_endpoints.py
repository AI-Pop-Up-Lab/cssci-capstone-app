import os
from fastapi import APIRouter, HTTPException, Header

router = APIRouter(prefix="/admin")

ADMIN_SECRET = os.environ.get("ADMIN_SECRET")

@router.post("/trigger-weekly-job")
async def trigger_job(x_admin_secret: str = Header(None)):
    """
    protected endpoint which requires X-Admin-Secret header matching the ADMIN_SECRET env variable
    doesn't run the job directly, returns a reminder to trigger the worker via GitHub Actions
    """
    if not ADMIN_SECRET or x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {"status": "trigger received, start the worker container via GitHub Actions"}