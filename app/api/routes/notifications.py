from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.notification import UserNotification
from app.models.user import MobileDevice
from datetime import datetime

router = APIRouter(prefix="/api/Notifications", tags=["Notifications"])


@router.get("/GetNotifications")
def get_notifications(UserId: str, db: Session = Depends(get_db)):
    items = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == UserId)
        .order_by(UserNotification.created_at.desc())
        .all()
    )
    data = [
        {
            "Id": n.id,
            "Title": n.title,
            "Message": n.message,
            "Body": n.message,
            "Image": n.image or "",
            "IsRead": n.is_read,
            "NotificationDate": n.created_at.strftime("%Y-%m-%d %H:%M:%S") if n.created_at else "",
            "CreatedAt": n.created_at.strftime("%Y-%m-%d %H:%M:%S") if n.created_at else "",
        }
        for n in items
    ]
    return {"data": data}


@router.post("/DeleteNotification")
def delete_notification(Id: int, db: Session = Depends(get_db)):
    n = db.query(UserNotification).filter(UserNotification.id == Id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(n)
    db.commit()
    return {"Message": "Deleted"}


@router.post("/MarkAsRead")
def mark_as_read(Id: int, db: Session = Depends(get_db)):
    n = db.query(UserNotification).filter(UserNotification.id == Id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"Message": "Marked as read"}


@router.get("/UnreadCount")
def unread_count(UserId: str, db: Session = Depends(get_db)):
    count = db.query(UserNotification).filter(
        UserNotification.user_id == UserId,
        UserNotification.is_read == False
    ).count()
    return {"Count": count}


@router.post("/MarkAllRead")
def mark_all_read(UserId: str, db: Session = Depends(get_db)):
    db.query(UserNotification).filter(
        UserNotification.user_id == UserId,
        UserNotification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"Message": "All marked as read"}
