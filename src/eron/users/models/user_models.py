from beanie import before_event, Replace, Save
from pydantic import EmailStr, Field
from typing import Optional
from datetime import datetime, timezone
from eron.core.base.base import BaseCollection
from eron.users.utils.account_status import AccountStatus
from eron.users.utils.user_role import UserRole
from typing import List
from beanie import Link

class UserModel(BaseCollection):

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    coins:float=50
    phone_number: Optional[str] =" "
    password: Optional[str] = None
    is_verified: bool = False
    country:Optional[str]=""
    gender:Optional[str]=""
    date_of_birth:Optional[str]=""
    bio:Optional[str]=""

    is_online: bool = Field(default=False)
    following: List[Link["UserModel"]] = [] 
    following_count: int = Field(default=0)
    followers_count: int = Field(default=0)
    total_like: int = Field(default=0)

    account_status: AccountStatus = Field(default=AccountStatus.ACTIVE)
    otp: Optional[str] = None
    role: Optional[UserRole] = Field(default=UserRole.USER)
    profile_image: Optional[str] = Field(default="https://cdn.pixabay.com/photo/2017/06/13/12/54/profile-2398783_1280.png")
    auth_provider: str =  Field(default="email")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Auto-update "updated_at" on update
    @before_event([Save, Replace])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "users"

