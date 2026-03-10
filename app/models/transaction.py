from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class OfferTransaction(Base):
    __tablename__ = "offer_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False)
    transaction_otp = Column(Integer, nullable=True)
    transaction_date = Column(DateTime, nullable=True)
    use_times = Column(Integer, default=1)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="offer_transactions")
    offer = relationship("Offer", back_populates="transactions")

class PointTransaction(Base):
    __tablename__ = "point_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    points = Column(Integer, nullable=False)
    key = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="point_transactions")