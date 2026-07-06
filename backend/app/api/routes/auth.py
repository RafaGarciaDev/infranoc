from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.application import auth_service
from app.core.db import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends(), session=Depends(get_session)):
    result = await auth_service.login(session, form.username, form.password)
    if not result:
        raise HTTPException(401, "Credenciais invalidas")
    return result
