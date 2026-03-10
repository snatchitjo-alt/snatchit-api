from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
from app.db.base import Base

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    description_ar = Column(Text, nullable=True)
    phone = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    banner_image = Column(String, nullable=True)
    qr_code = Column(String, unique=True, nullable=True)
    lat = Column(String, nullable=True)
    lon = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_top = Column(Boolean, default=False)
    orders = Column(Integer, default=0)
    is_pos = Column(Boolean, default=False)

    # Relationships
    category = relationship("Category", back_populates="vendors")
    offers = relationship("Offer", back_populates="vendor")
    users = relationship("User", back_populates="vendor")