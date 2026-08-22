from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User
from schemas import UserRegister, UserOut, Token
from auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/signup", response_model=Token, status_code=201)
async def signup(body: UserRegister, db: AsyncSession = Depends(get_db)):
    """Create an account. Signing up is optional — watching needs no account."""
    existing = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username or email already taken")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.username)
    return {"access_token": token, "user": user}


@router.post("/register", response_model=Token, status_code=201, include_in_schema=False)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    """Deprecated alias for /signup — kept so older clients keep working."""
    return await signup(body, db)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Accepts both Swagger OAuth2 form and JSON via form fields."""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token(user.id, user.username)
    return {"access_token": token, "user": user}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
