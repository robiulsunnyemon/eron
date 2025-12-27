from fastapi import APIRouter, HTTPException, Depends,status
from fastapi.security import OAuth2PasswordRequestForm
from eron.users.models.user_models import UserModel
from eron.users.schemas.user_schemas import UserResponse, UserCreate, VerifyOTP, ResendOTPRequest, ResetPasswordRequest
from eron.users.utils.email_config import SendOtpModel
from eron.users.utils.otp_generate import generate_otp
from eron.users.utils.password import hash_password, verify_password
from eron.users.utils.token_generate import create_access_token
from eron.users.utils.user_role import UserRole
import requests


router = APIRouter(prefix="/auth", tags=["Auth"])


# POST create new user
@router.post("/signup" ,response_model=UserResponse,status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    hashed_password = hash_password(user.password)
    db_user = await UserModel.find_one(UserModel.email == user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    otp = generate_otp()
    new_user = UserModel(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password=hashed_password,
        otp=otp
    )
    await new_user.create()
    send_otp_data = SendOtpModel(email=new_user.email, otp=new_user.otp)
    ##await send_otp(send_otp_data)
    return new_user




# POST create new user
@router.post("/signup/admin" ,response_model=UserResponse,status_code=status.HTTP_201_CREATED)
async def create_admin(user: UserCreate):
    hashed_password = hash_password(user.password)
    db_user = await UserModel.find_one(UserModel.email == user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    otp = generate_otp()
    new_user = UserModel(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone_number=user.phone_number,
        password=hashed_password,
        otp=otp,
        role=UserRole.ADMIN
    )
    await new_user.create()
    send_otp_data = SendOtpModel(email=new_user.email, otp=new_user.otp)
    ##await send_otp(send_otp_data)
    return new_user



@router.post("/otp-verify", status_code=status.HTTP_200_OK)
async def verify_otp(user:VerifyOTP):
    db_user =await UserModel.find_one(UserModel.email == user.email)
    if db_user is None :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    if user.otp != db_user.otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Wrong OTP")

    await db_user.update({"$set": {UserModel.is_verified: True}})
    return {"message":"You have  verified","data":db_user}



# Login logic update
@router.post("/login", status_code=status.HTTP_200_OK)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Flexible query for email or phone
    db_user = await UserModel.find_one(
        UserModel.email == form_data.username
    )

    if not db_user or not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not db_user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not verified")

    # str() conversion for ID is safer
    token = create_access_token(data={
        "sub": str(db_user.id),
        "email": db_user.email,
        "role": db_user.role.value
    })
    return {"access_token": token, "token_type": "bearer"}



@router.post("/resend-otp", status_code=status.HTTP_200_OK)
async def resend_otp(request: ResendOTPRequest):
    db_user = await UserModel.find_one(UserModel.email == request.email)
    if db_user is None :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")
    otp=generate_otp()
    await db_user.update({"$set":{db_user.otp:otp}})
    send_otp_data = SendOtpModel(email=db_user.email, otp=db_user.otp)
    ##await send_otp(send_otp_data)


    return {
        "message": "User registered successfully.Please check your email.A 6 digit otp has been sent.",
        "data":db_user,
        "otp":db_user.otp
    }



@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request: ResetPasswordRequest):
    db_user = await UserModel.find_one(UserModel.email == request.email)
    if db_user is None :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")

    if not db_user.is_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Your account is not verified with otp")

    hashed_password = hash_password(request.new_password)


    await db_user.update({"$set":{db_user.password:hashed_password}})
    return {"message":"successfully reset password"}



@router.post("/google-login",status_code=status.HTTP_201_CREATED)
async def google_login_token(access_token: str):

    if access_token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="please give me token")


    response = requests.get(
        f'https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}'
    )
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Google token")

    user_info = response.json()
    email = user_info["email"]
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    db_user = await UserModel.find_one(UserModel.email == email)
    if db_user is None :
        new_user = UserModel(
            first_name=name.split(" ")[0] if name else "",
            last_name=" ".join(name.split(" ")[1:]) if len(name.split(" ")) > 1 else "",
            email=email,
            phone_number="",
            password=None,
            is_verified=True,
            profile_image=picture,
            auth_provider="google",
        )
        await new_user.create()
        token = create_access_token(data={
            "sub": str(new_user.id),
            "email": new_user.email,
            "role": new_user.role.value
        })
        return {"access_token": token, "token_type": "bearer"}


    # Generate JWT token

    token = create_access_token(data={
        "sub": str(db_user.id),
        "email": db_user.email,
        "role": db_user.role.value
    })
    return {"access_token": token, "token_type": "bearer"}