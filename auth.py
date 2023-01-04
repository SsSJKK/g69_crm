from passlib.context import CryptContext
import os
from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt

os.environ['JWT_SECRET_KEY'] = 'sadas'   # should be kept secret
os.environ['JWT_REFRESH_SECRET_KEY'] = 'dasdas'     # should be kept secret

ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
ALGORITHM = "HS256"
JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']     # should be kept secret
# should be kept secret
JWT_REFRESH_SECRET_KEY = os.environ['JWT_REFRESH_SECRET_KEY']

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password: str) -> str:
  return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
  return password_context.verify(password, hashed_pass)


def create_access_token(user_id: int, expires_delta: int = None) -> str:
  if expires_delta is not None:
    expires_delta = datetime.utcnow() + expires_delta
  else:
    expires_delta = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  to_encode = {"exp": expires_delta,
               "user_id": user_id, "token_type": "access"}
  encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
  return encoded_jwt


def create_refresh_token(user_id: int, expires_delta: int = None) -> str:
  if expires_delta is not None:
    expires_delta = datetime.utcnow() + expires_delta
  else:
    expires_delta = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

  to_encode = {"exp": expires_delta,
               "user_id": user_id, "token_type": "refresh"}
  encoded_jwt = jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, ALGORITHM)
  return encoded_jwt
