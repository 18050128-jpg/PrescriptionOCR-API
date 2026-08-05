import json
from app.services.extraction_service import extract_prescription

# ---------------------------------------------------------------------------
# Test 1: Toa viết tay (đã có từ trước)
# ---------------------------------------------------------------------------
ocr_handwritten = [
    {"text": "PHONG KHAM NOIBS.CKIDINH CHI", "confidence": 0.94},
    {"text": "Dja chi: 120 Nguyen Xien, Long Blnh, Thu Duc.", "confidence": 0.98},
    {"text": "DON THUOC", "confidence": 0.99},
    {"text": "Ho ten:", "confidence": 0.98},
    {"text": "TRAN NAM VAN HOANG Tuoi:", "confidence": 0.91},
    {"text": "Chan doan: J02 - Vlom hong cap", "confidence": 0.97},
    {"text": "Dieu tri:", "confidence": 0.95},
    {"text": "1/ACEMUC 100 mg gol", "confidence": 0.99},
    {"text": "06 Gol", "confidence": 0.88},
    {"text": "sang 1 gol - chieu 1 gol", "confidence": 0.94},
    {"text": "2/PROPANOLOL 40 mg", "confidence": 0.99},
    {"text": "03 Vien", "confidence": 0.99},
    {"text": " Ngay 1/2v x 2 lan", "confidence": 0.94},
    {"text": "3/AUMGMENTIN 320MG", "confidence": 0.98},
    {"text": "06 vien", "confidence": 0.99},
    {"text": "sang 1 gol - chieu 1 gol", "confidence": 0.96},
    {"text": "Ngay 16 Thang 1 Nam 2024", "confidence": 0.99},
    {"text": "Bs Chl Dinh", "confidence": 0.95},
]

# ---------------------------------------------------------------------------
# Test 2: Toa BHYT in máy (OCR sẽ đọc từng vùng text riêng)
# ---------------------------------------------------------------------------
ocr_bhyt = [
    {"text": "1/1", "confidence": 0.99},
    {"text": "PK Số 1 [Ngoại]", "confidence": 0.97},
    {"text": "Số phiếu 50338/2019", "confidence": 0.99},
    {"text": "TOA THUOC BHYT", "confidence": 0.99},
    {"text": "Thẻ bảo hiểm y tế GB 4 35 208 00329", "confidence": 0.96},
    {"text": "Chẩn đoán: I88 - Viêm hạch bạch huyết không đặc hiệu (viêm hạch góc hàm phải)", "confidence": 0.99},
    # Thuốc 1 — SL tách dòng
    {"text": "1 )  CEFADROXIL 0,5g", "confidence": 0.99},
    {"text": "SL: 20 Viên", "confidence": 0.99},
    {"text": "Ghi chú  Uống :  Sáng 2 Viên  Chiều 2 Viên", "confidence": 0.98},
    # Thuốc 2 — SL tách dòng
    {"text": "2 )  VIPREDNI 16MG 16mg", "confidence": 0.99},
    {"text": "SL: 10 Viên", "confidence": 0.99},
    {"text": "Ghi chú  Uống :  Sáng 2 Viên", "confidence": 0.98},
    # Thuốc 3 — SL tách dòng
    {"text": "3 )  MYPARA 500 500mg", "confidence": 0.99},
    {"text": "SL: 10 Viên", "confidence": 0.99},
    {"text": "Ghi chú  Uống :  Sáng 1 Viên  Chiều 1 Viên", "confidence": 0.97},
    {"text": "Ngay 12 / 08 / 2019", "confidence": 0.99},
    {"text": "BS. Đào Tiến Trung", "confidence": 0.99},
]

print("=" * 60)
print("TEST 1: Toa viết tay")
print("=" * 60)
r1 = extract_prescription(ocr_handwritten)
print(json.dumps(r1, ensure_ascii=False, indent=2))

print()
print("=" * 60)
print("TEST 2: Toa BHYT in máy")
print("=" * 60)
r2 = extract_prescription(ocr_bhyt)
print(json.dumps(r2, ensure_ascii=False, indent=2))


def test_parse_usage_times_vietnamese_variants():
    from app.services.extraction_service import _parse_usage_times

    assert _parse_usage_times("sáng 1 gói - chiều 1 gói") == ["08:00", "14:00"]
    assert _parse_usage_times("Ngày 1/2v x 2 lần") == ["08:00", "20:00"]
    assert _parse_usage_times("1/2v x 2 lan") == ["08:00", "20:00"]
    assert _parse_usage_times("Uông Sáng 2 viên - Chiều 1 viên") == ["08:00", "14:00"]
    assert _parse_usage_times("Uông Sáng 2 viên - Chiu 1 viên") == ["08:00", "14:00"]
    assert _parse_usage_times("Uông Trưa 1 viên - Chiều 1 viên") == ["12:00", "14:00"]
    assert _parse_usage_times("Uông Sáng 2 viên - Chiều 1 viên - Trưa 1 viên") == ["08:00", "14:00", "12:00"]
