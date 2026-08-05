"""
FastAPI security dependencies — inject vào route handlers.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.services.auth_service import decode_token
from app.repositories import user_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency: giải mã JWT, trả về user document.
    Raise 401 nếu token không hợp lệ hoặc user không tồn tại / bị khoá.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = user_repository.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Tài khoản đã bị vô hiệu hoá")

    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency: yêu cầu role == 'admin'.
    Raise 403 nếu không đủ quyền.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có quyền thực hiện thao tác này",
        )
    return current_user
