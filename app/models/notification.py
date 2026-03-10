from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    image = Column(String, nullable=True)
    # Targeting: all | user | gender | birthday | age_above
    filter_type = Column(String, nullable=True, default="all")
    filter_value = Column(String, nullable=True)   # user_id | male/female | age number
    # Deep link: none | vendor | offer | url
    deep_link_type = Column(String, nullable=True, default="none")
    deep_link_id = Column(String, nullable=True)   # vendor id, offer id, or URL
    scheduled_at = Column(DateTime, nullable=True)
    sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    image = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)