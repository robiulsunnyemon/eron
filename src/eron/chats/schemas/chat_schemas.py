from pydantic import BaseModel, Field

class ChatSendMessage(BaseModel):
    receiver_id: str = Field(..., description="যাকে মেসেজ পাঠানো হচ্ছে তার Database ID", example="658af123456789")
    message: str = Field(..., min_length=1, description="মেসেজের টেক্সট", example="হ্যালো, কেমন আছেন?")