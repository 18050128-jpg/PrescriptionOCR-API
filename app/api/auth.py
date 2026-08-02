"""
Auth API — đăng ký, đăng nhập, lấy thông tin bản thân.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.user import UserRegister, UserResponse, TokenResponse
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.repositories import user_repository
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _user_to_response(doc: dict) -> dict:
    """Chuyển user document → dict an toàn (không có hashed_password)."""
    uid = doc.get("_id", doc.get("id", ""))
    return {
        "_id":        uid,
        "id":         uid,   # alias để Pydantic v2 serialize đúng
        "created_at": doc.get("created_at", ""),
        "username":   doc["username"],
        "email":      doc["email"],
        "full_name":  doc.get("full_name"),
        "role":       doc.get("role", "user"),
        "is_active":  doc.get("is_active", True),
    }


@router.post("/register", status_code=201, response_model=TokenResponse)
async def register(body: UserRegister):
    """
    Đăng ký tài khoản mới.
    - User đầu tiên trong hệ thống tự động trở thành admin.
    - Các user tiếp theo có role = 'user'.
    """
    if user_repository.get_by_username(body.username):
        raise HTTPException(status_code=400, detail="Username đã tồn tại")
    if user_repository.get_by_email(body.email):
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    # User đầu tiên → admin
    role = "admin" if not user_repository.exists_any() else "user"

    hashed = hash_password(body.password)
    doc = user_repository.create(
        username=body.username,
        email=body.email,
        hashed_password=hashed,
        full_name=body.full_name,
        role=role,
    )

    token = create_access_token({"sub": doc["_id"], "role": doc["role"]})
    return {"access_token": token, "token_type": "bearer", "user": _user_to_response(doc)}


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Đăng nhập bằng username + password (form data, tương thích OAuth2).
    Trả về JWT access token.
    """
    doc = user_repository.get_by_username(form_data.username)
    if doc is None or not verify_password(form_data.password, doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username hoặc password không đúng",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not doc.get("is_active", True):
        raise HTTPException(status_code=400, detail="Tài khoản đã bị vô hiệu hoá")

    token = create_access_token({"sub": doc["_id"], "role": doc["role"]})
    return {"access_token": token, "token_type": "bearer", "user": _user_to_response(doc)}


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    """Lấy thông tin tài khoản đang đăng nhập."""
    return _user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Cập nhật thông tin cá nhân (full_name, email)."""
    allowed = {k: v for k, v in body.items() if k in ("full_name", "email")}
    if not allowed:
        raise HTTPException(status_code=400, detail="Không có trường hợp lệ để cập nhật")
    updated = user_repository.update(current_user["_id"], allowed)
    return _user_to_response(updated)
