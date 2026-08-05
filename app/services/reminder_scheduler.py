"""
Reminder Scheduler — dùng APScheduler để kiểm tra và thông báo giờ uống thuốc.

Cơ chế:
  - Mỗi phút, scheduler chạy job `check_reminders`.
  - Job so sánh giờ hiện tại với remind_time của từng reminder đang active.
  - Nếu khớp (và đúng ngày trong tuần nếu có), ghi log + lưu notification vào
    collection "notifications" trong JSON store.

Notification document:
  {
    "_id": "<uuid>",
    "created_at": "<ISO>",
    "user_id": "<user_id>",
    "reminder_id": "<reminder_id>",
    "prescription_id": "<prescription_id>",
    "medicine_name": "<tên thuốc>",
    "remind_time": "HH:MM",
    "message": "Đến giờ uống thuốc: <tên thuốc> lúc HH:MM",
    "is_read": false
  }

Frontend có thể poll GET /api/v1/notifications để hiển thị popup/badge.
"""

import logging
import uuid
from datetime import datetime, timezone

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.repositories import reminder_repository, prescription_repository, medicine_repository
from app.database import json_store

logger = logging.getLogger(__name__)

# Đổi sang timezone phù hợp nếu cần (mặc định Asia/Ho_Chi_Minh)
LOCAL_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
NOTIF_COLLECTION = "notifications"


def _now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def check_reminders() -> None:
    """
    Được gọi mỗi phút — kiểm tra reminder nào khớp giờ hiện tại.
    Tạo notification document cho từng reminder khớp.
    """
    now = _now_local()
    current_time = now.strftime("%H:%M")
    # weekday(): 0=Monday … 6=Sunday — khớp với quy ước days_of_week của model
    current_weekday = now.weekday()

    active = reminder_repository.get_active_reminders()
    triggered = []

    for rem in active:
        if rem.get("remind_time") != current_time:
            continue

        days = rem.get("days_of_week", [])
        # days = [] nghĩa là mỗi ngày
        if days and current_weekday not in days:
            continue

        # Tạo notification
        notif = {
            "_id":             str(uuid.uuid4()),
            "created_at":      now.isoformat(timespec="seconds"),
            "user_id":         rem["user_id"],
            "reminder_id":     rem["_id"],
            "prescription_id": rem.get("prescription_id", ""),
            "medicine_name":   rem.get("medicine_name", ""),
            "remind_time":     current_time,
            "message":         f"Đến giờ uống thuốc: {rem.get('medicine_name', '')} lúc {current_time}",
            "is_read":         False,
        }
        json_store.insert(NOTIF_COLLECTION, notif)

        # Cố gắng giảm số lượng thuốc trong kho 1 đơn vị.
        # Lấy prescription để tìm `dosage` và `quantity` của medicine để xác định unit.
        try:
            presc_id = rem.get("prescription_id", "")
            presc = None
            if presc_id:
                presc = prescription_repository.get_by_id(presc_id)

            if presc:
                # Tìm medicine tương ứng theo tên (không phân biệt hoa thường)
                target = None
                for m in presc.get("medicines", []):
                    if m.get("name", "").strip().upper() == rem.get("medicine_name", "").strip().upper():
                        target = m
                        break

                if target:
                    qty_raw = target.get("quantity", "")
                    try:
                        parsed = medicine_repository._parse_quantity(qty_raw)
                        unit = parsed[1]
                    except Exception:
                        unit = ""
                    medicine_repository.decrease_quantity(target.get("name", ""), target.get("dosage", ""), unit, amount=1, prescription_id=presc_id, reminder_id=rem.get("_id"))
                else:
                    # fallback: giảm chỉ theo tên
                    medicine_repository.decrease_quantity(rem.get("medicine_name", ""), "", "", amount=1, prescription_id=presc_id, reminder_id=rem.get("_id"))
            else:
                medicine_repository.decrease_quantity(rem.get("medicine_name", ""), "", "", amount=1, prescription_id=presc_id, reminder_id=rem.get("_id"))
        except Exception:
            logger.exception("Failed to decrease medicine quantity for %s", rem.get("medicine_name", ""))
        triggered.append(rem.get("medicine_name", rem["_id"]))

    if triggered:
        logger.info("[Reminder] %d thông báo đã tạo lúc %s: %s",
                    len(triggered), current_time, ", ".join(triggered))


# ---------------------------------------------------------------------------
# Scheduler singleton
# ---------------------------------------------------------------------------

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone=LOCAL_TZ)
    # Chạy mỗi phút vào giây thứ 0
    _scheduler.add_job(
        check_reminders,
        CronTrigger(second=0, timezone=LOCAL_TZ),
        id="check_reminders",
        replace_existing=True,
        misfire_grace_time=30,
    )
    _scheduler.start()
    logger.info("[Reminder] Scheduler đã khởi động.")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Reminder] Scheduler đã dừng.")
