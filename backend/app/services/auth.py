from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token_hash,
)
from app.models import RefreshToken, User, UserProfile
from app.schemas import ProfileUpdate, TokenResponse, UserRegister


class AuthService:
    """Email/password auth designed so OAuth providers can plug in later."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserRegister) -> User:
        existing = await self.db.execute(select(User).where(User.email == data.email.lower()))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
        )
        self.db.add(user)
        await self.db.flush()
        profile = UserProfile(user_id=user.id)
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(user, attribute_names=["profile"])
        return user

    async def authenticate(self, email: str, password: str) -> User:
        result = await self.db.execute(
            select(User).options(selectinload(User.profile)).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
        return user

    async def issue_tokens(self, user: User) -> TokenResponse:
        access = create_access_token(user.id, extra_claims={"email": user.email})
        refresh = create_refresh_token(user.id)
        from app.core.config import get_settings

        settings = get_settings()
        token_row = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
        self.db.add(token_row)
        await self.db.flush()
        return TokenResponse(access_token=access, refresh_token=refresh)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            ) from exc
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        user_id = UUID(payload["sub"])
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
        )
        tokens = result.scalars().all()
        matched: RefreshToken | None = None
        for row in tokens:
            if verify_token_hash(refresh_token, row.token_hash):
                matched = row
                break
        if not matched:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or unknown"
            )
        if matched.expires_at < datetime.now(timezone.utc):
            matched.revoked = True
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
            )
        matched.revoked = True
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one()
        return await self.issue_tokens(user)


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user: User) -> UserProfile:
        if user.profile:
            return user.profile
        profile = UserProfile(user_id=user.id)
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def update(self, user: User, data: ProfileUpdate) -> UserProfile:
        profile = await self.get_or_create(user)
        payload = data.model_dump()
        if "english_tests" in payload and payload["english_tests"] is not None:
            if hasattr(payload["english_tests"], "model_dump"):
                payload["english_tests"] = payload["english_tests"].model_dump()
        for key, value in payload.items():
            setattr(profile, key, value)
        required = [
            profile.nationality,
            profile.highest_degree,
            profile.target_degree,
            profile.fields,
        ]
        if all(required) and profile.fields:
            user.onboarding_completed = True
        await self.db.flush()
        await self.db.refresh(profile)
        return profile
