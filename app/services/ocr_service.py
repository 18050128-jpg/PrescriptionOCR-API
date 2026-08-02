import os

os.environ["FLAGS_use_mkldnn"] = "0"  # tắt oneDNN trước khi Paddle khởi tạo

# Dùng cache model cục bộ cho project để tránh tải model xuống mỗi lần khởi động
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_CACHE_DIR = os.getenv(
    "PADDLE_PDX_MODEL_HOME",
    os.path.join(PROJECT_ROOT, ".paddlex_models"),
)
os.environ.setdefault("PADDLE_PDX_MODEL_HOME", MODEL_CACHE_DIR)
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

# Tắt kiểm tra nguồn model khi chạy ở môi trường offline / đã có cache sẵn.
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "1")

from paddleocr import PaddleOCR

# Instance được tạo lần đầu khi gọi hàm (lazy init)
_ocr_instance = None

_MOCK_OCR_ENABLED = os.getenv("MOCK_OCR", "0").strip().lower() in {"1", "true", "yes", "on"}

_MOCK_OCR_RESULT = [
    {"text": "PHONG KHAM DA KHOA AN KHANG", "confidence": 0.99},
    {"text": "TOA THUOC BHYT", "confidence": 0.98},
    {"text": "Ho va ten: NGUYEN VAN A", "confidence": 0.97},
    {"text": "Chan doan: Viem hong cap", "confidence": 0.96},
    {"text": "Ngay 01 / 01 / 2025", "confidence": 0.95},
    {"text": "1 ) AMOXICILLIN 500mg", "confidence": 0.94},
    {"text": "SL: 21 Vien", "confidence": 0.93},
    {"text": "Ghi chu Uong: Sang 1 Vien Chieu 1 Vien Toi 1 Vien", "confidence": 0.92},
    {"text": "BS. Tran Thi B", "confidence": 0.91},
]


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        # PaddleOCR 3.x API — dùng predict() thay vì ocr()
        _ocr_instance = PaddleOCR(
            lang="en",               # đổi sang "vi" nếu cài model tiếng Việt
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )
    return _ocr_instance


def extract_text(image_path: str) -> list[dict]:
    """
    Chạy OCR trên file ảnh và trả về list các dict {text, confidence}.

    Nếu biến môi trường `MOCK_OCR=1`, trả về dữ liệu giả ổn định để test runtime
    không phụ thuộc vào model OCR hoặc mạng.
    """
    if _MOCK_OCR_ENABLED:
        return [
            {
                "text": item["text"].strip(),
                "confidence": float(item["confidence"]),
            }
            for item in _MOCK_OCR_RESULT
        ]

    ocr = _get_ocr()
    results = ocr.predict(image_path)

    texts = []
    for res in results:
        rec_texts  = res.get("rec_texts",  []) if isinstance(res, dict) else getattr(res, "rec_texts",  [])
        rec_scores = res.get("rec_scores", []) if isinstance(res, dict) else getattr(res, "rec_scores", [])

        for text, score in zip(rec_texts, rec_scores):
            if text and text.strip():
                texts.append({
                    "text":       text.strip(),
                    "confidence": float(score),
                })

    return texts
