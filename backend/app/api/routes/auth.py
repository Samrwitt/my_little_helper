from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.schemas import RefreshRequest, TokenResponse, UserOut, UserRegister
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: DbSession) -> UserOut:
    user = await AuthService(db).register(data)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    service = AuthService(db)
    user = await service.authenticate(form_data.username, form_data.password)
    return await service.issue_tokens(user)


@router.post("/login/json", response_model=TokenResponse)
async def login_json(data: dict, db: DbSession) -> TokenResponse:
    """JSON login for frontend convenience (email/password)."""
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=422, detail="email and password required")
    service = AuthService(db)
    user = await service.authenticate(email, password)
    return await service.issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: DbSession) -> TokenResponse:
    return await AuthService(db).refresh(data.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
