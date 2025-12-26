
from pydantic import BaseModel, EmailStr
from email.message import EmailMessage
import aiosmtplib

# 🔹 Pydantic v2 model
class SendOtpModel(BaseModel):
    email: EmailStr
    otp: str

    model_config = {"from_attributes": True}


async def send_otp(otp_user: SendOtpModel):
    """
    Send OTP to user's email asynchronously
    """
    message = EmailMessage()
    message["From"] = "robiulsunyemon111@gmail.com"
    message["To"] = otp_user.email
    message["Subject"] = "🔑 Your OTP Code"
    message.set_content(f"Your OTP code is: {otp_user.otp}")

    await aiosmtplib.send(
        message,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username="robiulsunyemon111@gmail.com",
        password="bpbs pqqp lcwl tzur",
    )