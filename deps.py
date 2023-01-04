from typing import Union, Any
from datetime import datetime
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, undefer, defer
from fastapi.security import OAuth2PasswordBearer
from auth import (
    ALGORITHM,
    JWT_SECRET_KEY,
    JWT_REFRESH_SECRET_KEY,
    create_access_token,
    create_refresh_token
)

from jose import jwt
from pydantic import ValidationError
import models as md
from db_conn import get_db
from fastapi import Request

reuseable_oauth = OAuth2PasswordBearer(
    tokenUrl="/api/login_form",
    scheme_name="JWT"
)


def auth_middleware(requset: Request, db: Session = Depends(get_db), token: str = Depends(reuseable_oauth)) -> md.User:
  try:
    payload = jwt.decode(
        token, JWT_SECRET_KEY, algorithms=[ALGORITHM]
    )
    token_data = md.TokenPayload(**payload)
    if token_data.token_type != "access":
      raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="token_type is filed",
          headers={"WWW-Authenticate": "Bearer"},
      )
    # print(token_data)
    if datetime.fromtimestamp(token_data.exp) < datetime.now():
      raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="Token expired",
          headers={"WWW-Authenticate": "Bearer"},
      )
  except (jwt.JWTError, ValidationError):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
  # print(requset.url.path )
  if requset.url.path == '/api/me':
    user: md.User = db.query(md.User) .filter(
        md.User.id == token_data.user_id).first()
  else:
    user: md.User = db.query(md.User.id) .filter(
        md.User.id == token_data.user_id).first()

  if user is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Could not find user",
    )

  return user


def auth_refresh_token(db: Session = Depends(get_db), token: str = Depends(reuseable_oauth)) -> dict:
  try:
    payload = jwt.decode(
        token, JWT_REFRESH_SECRET_KEY, algorithms=[ALGORITHM]
    )
    token_data = md.TokenPayload(**payload)
    if token_data.token_type != "refresh":
      raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="token_type is filed",
          headers={"WWW-Authenticate": "Bearer"},
      )
    # print(token_data)
    if datetime.fromtimestamp(token_data.exp) < datetime.now():
      raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="Token expired",
          headers={"WWW-Authenticate": "Bearer"},
      )
  except (jwt.JWTError, ValidationError) as e:
    print(e)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

  return {
      "access_token":  create_access_token(token_data.user_id),
      "refresh_token":  create_refresh_token(token_data.user_id),
  }
