import os
from dotenv import load_dotenv
from jose import jwt
from datetime import datetime, timedelta, timezone

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(days=90)
    to_encode.update({"exp": expire})

    encoded_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_token
