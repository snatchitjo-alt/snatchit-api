from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)              # 3 Months, 6 Months, 12 Months
    billing_cycle = Column(String, nullable=False)      # monthly, yearly
    duration_months = Column(Integer, nullable=True)    # 3, 6, 12
    price = Column(Numeric(10, 2), nullable=False)
    apple_product_id = Column(String, nullable=True)    # App Store IAP product ID
    image = Column(String, nullable=True)               # URL or path to plan image
    stripe_price_id = Column(String, nullable=True)
    features = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    stripe_subscription_id = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    status = Column(String, default="active")       # active, cancelled, expired
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")