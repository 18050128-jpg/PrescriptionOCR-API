import os
import uuid
import shutil

from fastapi import UploadFile, HTTPException

UPLOAD_FOLDER = "app/uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def validate_and_save(file: UploadFile) -> tuple[str, str]:
    """
    Kiểm tra định dạng file và lưu lên disk.

    Returns:
        (filename, filepath) — tên file đã lưu và đường dẫn tuyệt đối.

    Raises:
        HTTPException 400 nếu định dạng không hợp lệ.
    """
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ jpg, jpeg, png"
        )

    filename = f"{uuid.uuid4()}{extension}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return filename, filepath
