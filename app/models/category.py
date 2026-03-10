from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    image = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Relationships
    vendors = relationship("Vendor", back_populates="category")
    children = relationship("Category", back_populates="parent")
    parent = relationship("Category", back_populates="children", remote_side=[id])