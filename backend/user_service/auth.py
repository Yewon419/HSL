from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import hashlib
import base64

from database import get_db
from config import settings
import models

# bcrypt 호환성 문제 해결: SHA256 기반 간단한 인증
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """간단한 SHA256 기반 비밀번호 확인"""
    # bcrypt 형식 ($2b$ 등)의 해시는 bcrypt가 필요하므로 특수 처리
    if hashed_password.startswith('$2b$') or hashed_password.startswith('$2a$') or hashed_password.startswith('$2y$'):
        # bcrypt 호환성 문제로 인해 비교 불가
        # 대신 평문으로 저장된 비밀번호와 비교 (테스트 용도)
        plain_sha256 = hashlib.sha256(plain_password.encode()).hexdigest()
        # DB에서 가져온 bcrypt 해시와 비교할 수 없으므로 False 반환
        # 실제로는 새로운 SHA256 기반 해시를 DB에 저장해야 함
        return False

    # 새로운 SHA256 기반 인증
    if hashed_password.startswith('sha256:'):
        plain_hash = 'sha256:' + hashlib.sha256(plain_password.encode()).hexdigest()
        return plain_hash == hashed_password

    # 레거시: 평문 비교 (개발 환경용)
    return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    """SHA256 기반 해시 생성"""
    return 'sha256:' + hashlib.sha256(password.encode()).hexdigest()

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