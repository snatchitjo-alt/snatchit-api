from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    description_ar = Column(Text, nullable=True)
    image = Column(String, nullable=True)
    top_image = Column(String, nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Offer type flags (can combine)
    is_flash = Column(Boolean, default=False)       # appears in flash offers tab
    is_promo = Column(Boolean, default=False)       # unlocked by promo code
    # if neither flag = general offer shown on vendor page

    # Active time window (e.g. "18:00" to "02:00"), null = always active
    active_from = Column(String, nullable=True)     # "HH:MM" in 24h format
    active_until = Column(String, nullable=True)    # "HH:MM" in 24h format

    # Flash offer timing
    flash_start = Column(DateTime, nullable=True)
    flash_end = Column(DateTime, nullable=True)

    # Promo code
    promo_code = Column(String, nullable=True)
    promo_expiry = Column(DateTime, nullable=True)

    # Subscription requirement: free, basic, premium
    required_tier = Column(String, default="free")
    level_priority = Column(Integer, default=0)     # 0=free, 1=basic, 2=premium

    # Offer details
    discount = Column(Integer, default=0)
    save_up_to = Column(Numeric(10, 2), nullable=True)
    save_up_to_currency = Column(String, nullable=True)
    points = Column(Integer, default=0)
    renew_duration = Column(Integer, nullable=True)  # days before offer resets per user
    use_times = Column(Integer, default=1)
    is_special = Column(Boolean, default=False)
    is_top = Column(Boolean, default=False)
    status = Column(String, default="active")        # active, inactive
    orders = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="offers")
    transactions = relationship("OfferTransaction", back_populates="offer")
    favourites = relationship("Favourite", back_populates="offer")

class Favourite(Base):
    __tablename__ = "favourites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favourites")
    offer = relationship("Offer", back_populates="favourites")
