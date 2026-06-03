'''
was gonna use for some admin api commands or something but then i forgot
'''
import os
from fastapi import APIRouter, HTTPException, Header

router = APIRouter(prefix="/admin")

ADMIN_SECRET = os.environ.get("ADMIN_SECRET")

@router.post("/trigger-weekly-job")
async def trigger_job(x_admin_secret: str = Header(None)):
    """
    protected endpoint which requires X-Admin-Secret header matching the ADMIN_SECRET env variable
    """
    if not ADMIN_SECRET or x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {"status": "received"}