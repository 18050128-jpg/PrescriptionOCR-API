"""
Notification API — user lấy danh sách thông báo nhắc uống thuốc.
"""

from fastapi import APIRouter, HTTPException, Depends

from app.database import json_store
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/notifications", tags=["Notification"])

NOTIF_COLLECTION = "notifications"


@router.get("/")
async def list_notifications(current_user: dict = Depends(get_current_user)):
    """
    Lấy tất cả notifications của user hiện tại, mới nhất lên đầu.
    """
    all_notifs = json_store.find_by_field(NOTIF_COLLECTION, "user_id", current_user["_id"])
    sorted_notifs = sorted(all_notifs, key=lambda n: n.get("created_at", ""), reverse=True)
    unread = sum(1 for n in sorted_notifs if not n.get("is_read", False))
    return {
        "total": len(sorted_notifs),
        "unread": unread,
        "notifications": sorted_notifs,
    }


@router.put("/{notification_id}/read", status_code=200)
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Đánh dấu một notification là đã đọc."""
    notif = json_store.find_by_id(NOTIF_COLLECTION, notification_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy notification")
    if notif.get("user_id") != current_user["_id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền")

    updated = json_store.update_by_id(NOTIF_COLLECTION, notification_id, {"is_read": True})
    return {"status": "success", "notification": updated}


@router.put("/read-all", status_code=200)
async def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    """Đánh dấu tất cả notifications của user là đã đọc."""
    all_notifs = json_store.find_by_field(NOTIF_COLLECTION, "user_id", current_user["_id"])
    count = 0
    for notif in all_notifs:
        if not notif.get("is_read", False):
            json_store.update_by_id(NOTIF_COLLECTION, notif["_id"], {"is_read": True})
            count += 1
    return {"status": "success", "marked_read": count}


@router.delete("/{notification_id}", status_code=200)
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Xóa một notification."""
    notif = json_store.find_by_id(NOTIF_COLLECTION, notification_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy notification")
    if notif.get("user_id") != current_user["_id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền")

    json_store.delete_by_id(NOTIF_COLLECTION, notification_id)
    return {"status": "success", "message": f"Đã xóa notification {notification_id}"}
