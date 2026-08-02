import re
from typing import Optional

# ===========================================================================
# Bảng chuẩn hoá chung
# ===========================================================================

MEDICINE_NAME_CORRECTIONS = {
    "ACEMEC": "ACEMUC",
    "PROPANOLOL": "PROPRANOLOL",
    "AUMGMENTIN": "AUGMENTIN",
}

UNIT_CORRECTIONS = {
    r"\bgol\b":   "gói",
    r"\bgoi\b":   "gói",
    r"\bGol\b":   "gói",
    r"\bGoi\b":   "gói",
    r"\bGOI\b":   "gói",
    r"\bvien\b":  "viên",
    r"\bvlen\b":  "viên",
    r"\bVien\b":  "viên",
    r"\bVIEN\b":  "viên",
    r"\bViên\b":  "viên",
    r"\bVIÊN\b":  "viên",
    r"\bsang\b":  "Sáng",
    r"\bSang\b":  "Sáng",
    r"\bchieu\b": "Chiều",
    r"\bChieu\b": "Chiều",
    r"\bngay\b":  "Ngày",
    r"\bNgay\b":  "Ngày",
    r"\blan\b":   "lần",
    r"\bLan\b":   "lần",
    r"\btu01\b":  "tuổi",
    r"\btuoi\b":  "tuổi",
}

# ===========================================================================
# Helpers chung
# ===========================================================================

def _join_texts(ocr_results: list[dict]) -> list[str]:
    return [item["text"].strip() for item in ocr_results if item.get("text")]


def _normalize_units(text: str) -> str:
    for pattern, replacement in UNIT_CORRECTIONS.items():
        text = re.sub(pattern, replacement, text)
    return text


def _correct_medicine_name(name: str) -> str:
    upper = name.upper().strip()
    return MEDICINE_NAME_CORRECTIONS.get(upper, name.strip())


def _normalize_dosage(dosage: str) -> str:
    """Thêm khoảng trắng giữa số và đơn vị nếu thiếu: '500mg' → '500 mg'."""
    return re.sub(r"(\d)(mg|MG|mcg|MCG|ml|ML|g|G)\b", r"\1 \2", dosage).upper()


def _parse_date_from_lines(lines: list[str]) -> Optional[str]:
    """
    Tìm ngày trong list lines.
    Hỗ trợ:
      - "Ngay DD Thang MM Nam YYYY"
      - "Ngay DD / MM / YYYY"
      - "DD/MM/YYYY" hoặc "DD-MM-YYYY"
    """
    for line in lines:
        m = re.search(
            r"Ng[aà]y\s+(\d{1,2})\s+[/]?\s*Th[aá]ng\s+(\d{1,2})\s+[/]?\s*N[aă]m\s+(\d{4})",
            line, re.IGNORECASE
        )
        if m:
            return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"

        # "Ngay 12 / 08 / 2019"
        m = re.search(
            r"Ng[aà]y\s+(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})",
            line, re.IGNORECASE
        )
        if m:
            return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"

    for line in lines:
        m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", line)
        if m:
            return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"

    return None


def _parse_doctor_from_lines(lines: list[str]) -> Optional[str]:
    """
    Tìm tên bác sĩ. Hỗ trợ:
      - "BS. Đào Tiến Trung"  (toa BHYT in máy, có dấu tiếng Việt)
      - "Bs Chl Dinh"         (toa viết tay, OCR không dấu)
    Duyệt từ cuối lên để lấy dòng gần chữ ký nhất.
    """
    for line in reversed(lines):
        # Ưu tiên dòng có "BS." hoặc "B.S." với tên đầy đủ
        m = re.match(r"^\s*B[\.s]?[Ss][\.\s]+(.+)$", line)
        if m:
            name = m.group(1).strip().rstrip(".")
            if len(name) > 2:
                return f"BS. {name}"
    return None


# ===========================================================================
# Detector: phân loại loại toa
# ===========================================================================

def _detect_prescription_type(lines: list[str]) -> str:
    """
    Trả về:
      "bhyt"      — toa BHYT in máy (có "TOA THUOC BHYT", "Chan doan:", "SL:")
      "handwritten" — toa viết tay (có "DON THUOC", "Ho ten:", "Dieu tri:")
      "unknown"   — không xác định, dùng fallback
    """
    text_joined = " ".join(lines).upper()

    bhyt_signals = [
        r"TOA\s+THU[OÔ]C\s+BHYT",
        r"B[AÁ]O\s+HI[EÊ]M\s+Y\s+T[EÊ]",
        r"\bBHYT\b",
        r"S[OỐ]\s+PHI[EÊ]U",
        r"\bSL\s*:",
    ]
    handwritten_signals = [
        r"DON\s+THUOC",
        r"HO\s+TEN\s*:",
        r"DIEU\s+TRI\s*:",
        r"SINH\s+HIEU",
    ]

    bhyt_score = sum(1 for p in bhyt_signals if re.search(p, text_joined))
    hw_score   = sum(1 for p in handwritten_signals if re.search(p, text_joined))

    if bhyt_score >= 2:
        return "bhyt"
    if hw_score >= 2:
        return "handwritten"
    return "unknown"


# ===========================================================================
# Parser: Toa viết tay
# ===========================================================================

def _parse_handwritten(lines: list[str]) -> dict:

    def _hospital() -> Optional[str]:
        if lines:
            raw = re.sub(r"[^A-Za-z0-9\s\./]", " ", lines[0])
            return re.sub(r"\s+", " ", raw).strip().upper() or None
        return None

    def _patient_name() -> Optional[str]:
        for i, line in enumerate(lines):
            if re.search(r"Ho\s+ten\s*:", line, re.IGNORECASE):
                match = re.sub(r"Ho\s+ten\s*:", "", line, flags=re.IGNORECASE).strip()
                match = re.split(r"Tu[o0O]i\s*:", match, flags=re.IGNORECASE)[0].strip()
                if match:
                    return match.upper()
                if i + 1 < len(lines):
                    nxt = re.split(r"Tu[o0O]i\s*:", lines[i + 1], flags=re.IGNORECASE)[0].strip()
                    return nxt.upper() if nxt else None
        return None

    def _diagnosis() -> Optional[str]:
        for line in lines:
            if re.search(r"Chan\s+doan\s*:", line, re.IGNORECASE):
                raw = re.sub(r"Chan\s+doan\s*:", "", line, flags=re.IGNORECASE).strip()
                raw = re.sub(r"Vlom|Vlem", "Viêm", raw)
                raw = re.sub(r"\bcap\b", "cấp", raw)
                return raw or None
        return None

    def _medicines() -> list[dict]:
        result = []
        start = 0
        for idx, line in enumerate(lines):
            if re.search(r"Dieu\s+tri\s*:", line, re.IGNORECASE):
                start = idx + 1
                break

        i = start
        while i < len(lines):
            line = lines[i]
            med_header = re.match(
                r"^\s*(\d+)\s*[/\\.]\s*([A-Z][A-Za-z0-9\s\-]+?)\s+"
                r"(\d+(?:[.,]\d+)?\s*(?:mg|MG|mcg|MCG|ml|ML|g|G))",
                line
            )
            if med_header:
                med_name = _correct_medicine_name(med_header.group(2))
                dosage   = _normalize_dosage(med_header.group(3))
                quantity = ""
                usage    = ""

                if i + 1 < len(lines):
                    qty_line = _normalize_units(lines[i + 1])
                    qty_m = re.match(r"^\s*(\d+)\s*(gói|viên|ống|vỉ|chai)", qty_line, re.IGNORECASE)
                    if qty_m:
                        quantity = f"{qty_m.group(1)} {qty_m.group(2)}"
                        i += 1

                if i + 1 < len(lines):
                    next_raw = lines[i + 1]
                    is_next_med  = bool(re.match(r"^\s*\d+\s*[/\\.]", next_raw))
                    is_date_line = bool(re.search(r"Ngay\s+tai\s+kham|Ngay\s+\d+\s+Thang", next_raw, re.IGNORECASE))
                    if not is_next_med and not is_date_line:
                        usage = _normalize_units(next_raw).strip()
                        i += 1

                result.append({"name": med_name, "dosage": dosage,
                                "quantity": quantity, "usage": usage})
            i += 1
        return result

    return {
        "hospital":     _hospital(),
        "patient_name": _patient_name(),
        "doctor":       _parse_doctor_from_lines(lines),
        "diagnosis":    _diagnosis(),
        "date":         _parse_date_from_lines(lines),
        "medicines":    _medicines(),
    }


# ===========================================================================
# Parser: Toa BHYT in máy
# ===========================================================================

def _parse_bhyt(lines: list[str]) -> dict:

    def _hospital() -> Optional[str]:
        """
        Toa BHYT: tên cơ sở y tế thường nằm ở các dòng đầu,
        trước dòng 'TOA THUOC BHYT'.
        Ưu tiên dòng có dạng "PK Số N" hoặc "Phòng khám...".
        """
        # Ưu tiên dòng chứa "PK" hoặc "Phòng khám" hoặc "Bệnh viện"
        for line in lines[:15]:
            if re.search(
                r"^PK\s+S[Ốố6]\s*\d+|Ph[oòó]ng\s+kh[aá]m|B[eệ]nh\s+vi[eệ]n|\bPK\b",
                line, re.IGNORECASE
            ):
                return line.strip()

        # Fallback: dòng ngay trước "TOA THUOC BHYT"
        for i, line in enumerate(lines):
            if re.search(r"TOA\s+THU[OÔ]C\s+BHYT", line, re.IGNORECASE):
                for j in range(i - 1, -1, -1):
                    candidate = lines[j].strip()
                    if candidate and not re.search(
                        r"^\d+\s*/\s*\d+$|S[Ố]\s+PHI[EÊ]U",
                        candidate, re.IGNORECASE
                    ):
                        return candidate
                break

        for line in lines:
            if line.strip():
                return line.strip()
        return None

    def _patient_name() -> Optional[str]:
        """
        Toa BHYT: tên BN thường nằm ở đầu, sau mã số người bệnh
        hoặc là dòng trống đầu tiên sau header.
        Dấu hiệu: dòng chỉ gồm chữ in hoa + khoảng trắng, không có ':'.
        """
        # Tìm theo label "Ho va ten:" hoặc "Họ và tên:"
        for i, line in enumerate(lines):
            if re.search(r"H[oọ]\s+(v[aà]\s+)?t[eê]n\s*:", line, re.IGNORECASE):
                val = re.sub(r"H[oọ]\s+(v[aà]\s+)?t[eê]n\s*:", "", line, flags=re.IGNORECASE).strip()
                # Loại phần tuổi / giới tính nếu có cùng dòng
                val = re.split(r"Tu[oổ]i|Gi[oớ]i\s*t[iính]nh|N[aă]m\s+sinh", val, flags=re.IGNORECASE)[0].strip()
                if val:
                    return val.upper()
                if i + 1 < len(lines):
                    return lines[i + 1].strip().upper()
        return None

    def _diagnosis() -> Optional[str]:
        """
        Toa BHYT: "Chẩn đoán: I88 - Viêm hạch..."
        Hỗ trợ cả có dấu và không dấu.
        """
        for line in lines:
            if re.search(r"Ch[aâẩ]n\s+[dđ]o[aáà]n\s*:", line, re.IGNORECASE):
                raw = re.sub(r"Ch[aâẩ]n\s+[dđ]o[aáà]n\s*:", "", line, flags=re.IGNORECASE).strip()
                return raw or None
        return None

    def _medicines() -> list[dict]:
        """
        Toa BHYT in máy — format mỗi thuốc gồm 2-3 dòng:
          Dòng 1a: "1 )  CEFADROXIL 0,5g         SL: 20 Viên"  (SL cùng dòng)
          Dòng 1b: "1 )  CEFADROXIL 0,5g"                       (SL dòng riêng)
          Dòng 2 : "SL: 20 Viên"                                 (nếu tách dòng)
          Dòng 3 : "Ghi chú  Uống :  Sáng 2 Viên  Chiều 2 Viên"
        """
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Nhận diện dòng thuốc: "N )  TÊN THUỐC  liều"
            med_m = re.match(
                r"^\s*(\d+)\s*\)\s*"                          # "1 ) "
                r"([A-Za-zÀ-ỹ][A-Za-zÀ-ỹ0-9\s\-\.,]+?)\s+"  # tên thuốc
                r"(\d+(?:[.,]\d+)?\s*(?:mg|MG|g|G|ml|ML))",  # liều lượng
                line, re.IGNORECASE
            )
            if med_m:
                med_name = _correct_medicine_name(med_m.group(2).strip())
                dosage   = _normalize_dosage(med_m.group(3))
                quantity = ""
                usage    = ""

                # SL cùng dòng
                sl_m = re.search(r"SL\s*[:\-]\s*(\d+)\s*([A-Za-zÀ-ỹ]+)", line, re.IGNORECASE)
                if sl_m:
                    unit = _normalize_units(sl_m.group(2))
                    quantity = f"{sl_m.group(1)} {unit}"

                # Duyệt tối đa 3 dòng tiếp theo để tìm SL và usage
                consumed = 0
                for offset in range(1, 4):
                    if i + offset >= len(lines):
                        break
                    nxt = lines[i + offset]

                    # Gặp dòng thuốc tiếp theo → dừng
                    if re.match(r"^\s*\d+\s*\)", nxt):
                        break

                    # SL dòng riêng
                    if not quantity:
                        sl_m2 = re.match(r"^\s*SL\s*[:\-]\s*(\d+)\s*([A-Za-zÀ-ỹ]+)", nxt, re.IGNORECASE)
                        if sl_m2:
                            quantity = f"{sl_m2.group(1)} {_normalize_units(sl_m2.group(2))}"
                            consumed = offset
                            continue

                    # Dòng usage: "Ghi chú  Uống :"
                    # Các dòng tiếp theo có thể là: "Sáng 2 Viên", "Chiều 2 Viên"
                    if re.search(r"Ghi\s+ch[uú]|U[oô]ng|D[uù]ng", nxt, re.IGNORECASE):
                        # Bỏ "Ghi chú" ở đầu, giữ nguyên phần còn lại
                        usage_clean = re.sub(
                            r"^\s*Ghi\s+ch[uú]\s*", "",
                            nxt, flags=re.IGNORECASE
                        ).strip()
                        consumed = offset
                        # Gộp các dòng kế tiếp chứa thông tin liều (Sáng/Chiều/Tối/Ngày/Buổi)
                        for extra in range(offset + 1, offset + 5):
                            if i + extra >= len(lines):
                                break
                            nxt2 = lines[i + extra].strip()
                            # Dừng nếu gặp dòng thuốc mới hoặc dòng không liên quan
                            if re.match(r"^\s*\d+\s*\)", nxt2):
                                break
                            if re.search(
                                r"S[aá]ng|Chi[eề]u|T[oố]i|Ng[aà]y|Bu[oổ]i",
                                nxt2, re.IGNORECASE
                            ):
                                usage_clean = usage_clean + "  " + nxt2
                                consumed = extra
                            else:
                                break
                        usage = _normalize_units(usage_clean)
                        break

                i += consumed
                result.append({"name": med_name, "dosage": dosage,
                                "quantity": quantity, "usage": usage})
            i += 1
        return result

    return {
        "hospital":     _hospital(),
        "patient_name": _patient_name(),
        "doctor":       _parse_doctor_from_lines(lines),
        "diagnosis":    _diagnosis(),
        "date":         _parse_date_from_lines(lines),
        "medicines":    _medicines(),
    }


# ===========================================================================
# Hàm chính — public API
# ===========================================================================

def extract_prescription(ocr_results: list[dict]) -> dict:
    """
    Nhận vào list kết quả OCR (mỗi phần tử có 'text' và 'confidence'),
    tự động phát hiện loại toa và trả về dict có cấu trúc đơn thuốc:
    {
        "prescription_type": "bhyt" | "handwritten" | "unknown",
        "hospital": str | None,
        "patient_name": str | None,
        "doctor": str | None,
        "diagnosis": str | None,
        "date": str | None,         # format DD/MM/YYYY
        "medicines": [
            {"name": str, "dosage": str, "quantity": str, "usage": str},
            ...
        ]
    }
    """
    lines = _join_texts(ocr_results)
    prescription_type = _detect_prescription_type(lines)

    if prescription_type == "bhyt":
        data = _parse_bhyt(lines)
    elif prescription_type == "handwritten":
        data = _parse_handwritten(lines)
    else:
        # Fallback: thử cả hai, lấy kết quả có medicines nhiều hơn
        d1 = _parse_bhyt(lines)
        d2 = _parse_handwritten(lines)
        data = d1 if len(d1["medicines"]) >= len(d2["medicines"]) else d2

    data["prescription_type"] = prescription_type
    return data
