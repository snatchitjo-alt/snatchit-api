from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from app.db.base import Base

class Slider(Base):
    __tablename__ = "sliders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    image = Column(String, nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    url = Column(String, nullable=True)
    link_type = Column(String, default="web")  # web, vendor, subscription
    target_id = Column(Integer, nullable=True)  # vendor id if link_type=vendor
    slider_type = Column(Integer, default=0)
    display_order = Column(Integer, default=0)
    display_seconds = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
