
from fastapi import APIRouter, HTTPException, status,Depends
from typing import List
from eron.users.models.user_models import UserModel
from eron.users.schemas.user_schemas import UserResponse
from eron.users.utils.get_current_user import get_current_user

# Define the router for User Management
user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.get("/", response_model=List[UserResponse], status_code=status.HTTP_200_OK)
async def get_all_users(skip: int = 0, limit: int = 20):
    """
    Retrieve a list of all users with pagination.

    - **skip**: Number of records to skip (default is 0)
    - **limit**: Maximum number of records to return (default is 20)
    """
    # Fetch users sorted by creation date (newest first)
    users = await UserModel.find_all().sort("-created_at").skip(skip).limit(limit).to_list()
    return users







@user_router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_user(user_id: str):
    """
    Get detailed information about a specific user by their unique ID.
    """
    # Search for the user in the database by ID
    user = await UserModel.get(user_id)

    # Check if user exists; if not, raise a 404 error
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@user_router.get("/users/my_profile", response_model=UserModel)
async def my_profile(current_user: UserModel = Depends(get_current_user)):
    return current_user




@user_router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: str):
    """
    Permanently delete a user from the database using their ID.
    """
    # First, verify if the user exists before attempting deletion
    user = await UserModel.get(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Execute the delete command via Beanie
    await user.delete()

    return {"message": "User deleted successfully"}