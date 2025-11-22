from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from config import settings
import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증
    bcrypt는 72바이트 제한이 있으므로 자동으로 처리됩니다.
    """
    # bcrypt.checkpw는 bytes를 받으므로 인코딩
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')

    # bcrypt는 내부적으로 72바이트 제한을 처리
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def get_password_hash(password: str) -> str:
    """
    비밀번호 해시 생성
    bcrypt는 72바이트 제한이 있으므로 자동으로 처리됩니다.
    """
    # bcrypt.hashpw는 bytes를 받으므로 인코딩
    password_bytes = password.encode('utf-8')

    # bcrypt.gensalt()로 salt 생성하고 해시
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

    # 문자열로 디코딩하여 반환
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = verify_token(token, credentials_exception)
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user