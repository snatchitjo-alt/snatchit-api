from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.subscription import SubscriptionPlan, Subscription

router = APIRouter(prefix="/api/ScratchCard", tags=["Subscription"])

@router.post("/UserSubScribtion")
def get_user_subscription(UserId: str = "", db: Session = Depends(get_db)):
    if not UserId:
        return {"data": _free_response()}
    sub = db.query(Subscription).filter(
        Subscription.user_id == UserId,
        Subscription.status == "active"
    ).order_by(Subscription.end_date.desc()).first()
    if not sub:
        return {"data": _free_response()}
    plan = sub.plan
    from datetime import datetime
    now = datetime.utcnow()
    is_expired = sub.end_date and sub.end_date < now
    if is_expired:
        return {"data": _free_response()}
    return {"data": {
        "IsFree": False,
        "LevelName": plan.name,
        "LevelPriority": 1,
        "LevelColor": "F58520",
        "ExpiryDate": sub.end_date.strftime("%Y/%m/%d %H:%M:%S") if sub.end_date else "",
        "ServerDate": now.strftime("%Y/%m/%d %H:%M:%S"),
        "IsActive": True
    }}

def _free_response():
    from datetime import datetime
    return {
        "IsFree": True,
        "LevelName": "Free",
        "LevelPriority": 0,
        "LevelColor": "808080",
        "ExpiryDate": "",
        "ServerDate": datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S"),
        "IsActive": False
    }

@router.get("/GetSubscriptionPlans")
def get_subscription_plans(db: Session = Depends(get_db)):
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).order_by(SubscriptionPlan.duration_months).all()
    return {"data": [
        {
            "Id": p.id,
            "Name": p.name,
            "DurationMonths": p.duration_months or 0,
            "Price": float(p.price),
            "AppleProductId": p.apple_product_id or "",
            "Image": p.image or ""
        } for p in plans
    ]}

@router.post("/VerifyApplePurchase")
def verify_apple_purchase(UserId: str, ProductId: str, db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.apple_product_id == ProductId).first()
    if not plan:
        return {"Message": "Plan not found", "Success": False}
    months = plan.duration_months or 1
    end_date = datetime.utcnow() + timedelta(days=30 * months)
    sub = Subscription(
        user_id=UserId,
        plan_id=plan.id,
        status="active",
        start_date=datetime.utcnow(),
        end_date=end_date
    )
    db.add(sub)
    db.commit()
    return {"Message": "Subscription activated", "Success": True, "EndDate": end_date.strftime("%Y/%m/%d %H:%M:%S")}
