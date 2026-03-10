from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    gender_id = Column(Integer, nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    is_active = Column(Boolean, default=False)
    total_points = Column(Integer, default=0)
    otp = Column(Integer, nullable=True)
    role = Column(String, default="client")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="users")
    subscriptions = relationship("Subscription", back_populates="user")
    offer_transactions = relationship("OfferTransaction", back_populates="user")
    point_transactions = relationship("PointTransaction", back_populates="user")
    mobile_devices = relationship("MobileDevice", back_populates="user")
    favourites = relationship("Favourite", back_populates="user")

class MobileDevice(Base):
    __tablename__ = "mobile_devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    device_id = Column(String, nullable=False)
    token = Column(String, nullable=False)
    os = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="mobile_devices")