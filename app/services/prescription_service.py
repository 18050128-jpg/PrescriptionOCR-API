from fastapi import HTTPException

from app.services.ocr_service import extract_text
from app.services.extraction_service import extract_prescription
from app.repositories import prescription_repository


def process_and_save(filename: str, filepath: str,
                     user_id: str | None = None) -> dict:
    """
    Pipeline đầy đủ: OCR → extraction → lưu vào JSON store.

    Args:
        filename:  Tên file ảnh đã lưu (dùng làm metadata)
        filepath:  Đường dẫn tuyệt đối đến file ảnh
        user_id:   ID user đang đăng nhập (None nếu không xác thực)

    Returns:
        Document prescription đã được lưu (có _id, created_at).

    Raises:
        HTTPException 500 nếu OCR hoặc extraction thất bại.
    """
    try:
        ocr_result = extract_text(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR thất bại: {str(e)}")

    try:
        extracted = extract_prescription(ocr_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction thất bại: {str(e)}")

    document = prescription_repository.create(
        extracted=extracted,
        filename=filename,
        image_path=filepath,
        user_id=user_id,
    )
    return document
