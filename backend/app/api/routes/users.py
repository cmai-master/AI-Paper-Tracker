"""User API routes"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.user import UserCreate, UserResponse
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Create a new user.

    - **email**: User email (must be unique)
    - **username**: Username (must be unique)
    - **password**: User password (min 8 characters)
    - **full_name**: Optional full name
    """
    # Check if user already exists
    stmt = select(User).where(
        (User.email == user_data.email) | (User.username == user_data.username)
    )
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists",
        )

    # Create new user (password hashing should be done here)
    # For now, we'll store it as-is (NOT PRODUCTION READY)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=user_data.password,  # TODO: Hash password
        full_name=user_data.full_name,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info("User created", user_id=new_user.id, email=new_user.email)

    return new_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get a user by ID.

    - **user_id**: User ID
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> List[User]:
    """
    List all users with pagination.

    - **skip**: Number of users to skip
    - **limit**: Maximum number of users to return
    """
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return list(users)
