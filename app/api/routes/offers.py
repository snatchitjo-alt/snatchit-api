from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.offer import Offer, Favourite
from app.models.transaction import OfferTransaction, PointTransaction
from app.models.user import User
from app.models.vendor import Vendor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.api.routes.home import static_url
SYDNEY_TZ = ZoneInfo("Australia/Sydney")

router = APIRouter(prefix="/api/Offers", tags=["Offers"])

TIER_PRIORITY = {"free": 0, "basic": 1, "premium": 2}

def get_user_tier_priority(user: User) -> int:
    if not user:
        return 0
    sub = getattr(user, 'subscription', None)
    if not sub or not sub.is_active:
        return 0
    return TIER_PRIORITY.get(sub.plan or "free", 0)

def get_last_redemption(user_id: str, offer_id: int, db: Session):
    return db.query(OfferTransaction).filter(
        OfferTransaction.user_id == user_id,
        OfferTransaction.offer_id == offer_id
    ).order_by(OfferTransaction.created_at.desc()).first()

def _is_time_active(offer: Offer) -> bool:
    """Returns True if current time is within the offer's active window, or if no window is set."""
    if not offer.active_from or not offer.active_until:
        return True
    try:
        now_time = datetime.now(SYDNEY_TZ).time().replace(second=0, microsecond=0)
        from_h, from_m = map(int, offer.active_from.split(":"))
        until_h, until_m = map(int, offer.active_until.split(":"))
        from_t = now_time.replace(hour=from_h, minute=from_m)
        until_t = now_time.replace(hour=until_h, minute=until_m)
        if from_t <= until_t:
            return from_t <= now_time <= until_t
        else:  # crosses midnight e.g. 18:00 → 02:00
            return now_time >= from_t or now_time <= until_t
    except Exception:
        return True

def format_offer(offer: Offer, user_id: str, db: Session) -> dict:
    now = datetime.now(SYDNEY_TZ).replace(tzinfo=None)

    # Check if flash offer is currently active
    is_flash_active = False
    if offer.is_flash:
        if offer.flash_start and offer.flash_end:
            is_flash_active = offer.flash_start <= now <= offer.flash_end
        else:
            is_flash_active = True

    # Check if promo offer is expired
    if offer.is_promo and offer.promo_expiry and offer.promo_expiry < now:
        return None  # expired promo, skip

    # Check renewal - is offer locked for this user due to recent redemption?
    is_redeemed = False
    renew_date = None
    if user_id:
        last = get_last_redemption(user_id, offer.id, db)
        if last and offer.renew_duration:
            unlock_at = last.created_at + timedelta(days=offer.renew_duration)
            if now < unlock_at:
                is_redeemed = True
                renew_date = unlock_at.strftime("%Y-%m-%d %H:%M:%S")

    # Check subscription tier lock
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    user_priority = get_user_tier_priority(user)
    offer_priority = TIER_PRIORITY.get(offer.required_tier or "free", 0)
    is_locked = user_priority < offer_priority

    return {
        "Id": offer.id,
        "Name": offer.name or "",
        "NameAr": offer.name_ar or "",
        "Description": offer.description or "",
        "Image": static_url(offer.image),
        "TopImage": static_url(offer.top_image),
        "VendorId": offer.vendor_id,
        "Discount": offer.discount or 0,
        "SaveUpTo": str(float(offer.save_up_to or 0)),
        "SaveUpToCurrency": offer.save_up_to_currency or "",
        "Points": offer.points or 0,
        "RenewDuration": str(offer.renew_duration) if offer.renew_duration else "",
        "RequiredTier": offer.required_tier or "free",
        "LevelPriority": offer.level_priority or 0,
        "IsFlash": offer.is_flash or False,
        "IsPromo": offer.is_promo or False,
        "ServerDate": datetime.now(SYDNEY_TZ).strftime("%Y/%m/%d %H:%M:%S"),
        "FlashStart": offer.flash_start.strftime("%Y/%m/%d %H:%M:%S") if offer.flash_start else "",
        "FlashEnd": offer.flash_end.strftime("%Y/%m/%d %H:%M:%S") if offer.flash_end else "",
        "IsFlashActive": is_flash_active,
        "IsRedeemed": is_redeemed,
        "RenewDate": renew_date or "",
        "IsLocked": is_locked,
        "CanBeTaken": not is_locked and not is_redeemed,
        "IsFavourite": False,
        "ExpiryDate": offer.promo_expiry.strftime("%Y/%m/%d %H:%M:%S") if offer.promo_expiry else "",
        "PromoCode": offer.promo_code or "",
        "OfferTypeId": 1 if offer.is_flash else 2 if offer.is_promo else 0,
        "Status": 1,
        "IsTop": offer.is_top or False,
        "Orders": offer.orders or 0,
        "ActiveFrom": offer.active_from or "",
        "ActiveUntil": offer.active_until or "",
        "IsTimeActive": _is_time_active(offer),
    }

@router.get("/GetOffersByVendorId")
def get_offers_by_vendor(VendorId: int, UserId: str = "", db: Session = Depends(get_db)):
    offers = db.query(Offer).filter(
        Offer.vendor_id == VendorId,
        Offer.status == "approved",
        Offer.is_promo == False
    ).all()
    result = [format_offer(o, UserId, db) for o in offers]
    result = [r for r in result if r is not None]
    return {"data": result}

@router.get("/GetFlashOffers")
def get_flash_offers(UserId: str = "", db: Session = Depends(get_db)):
    now = datetime.now(SYDNEY_TZ).replace(tzinfo=None)
    offers = db.query(Offer).filter(
        Offer.is_flash == True,
        Offer.status == "approved"
    ).all()
    # Only return currently active flash offers
    result = []
    for o in offers:
        if o.flash_start and o.flash_end:
            if not (o.flash_start <= now <= o.flash_end):
                continue
        formatted = format_offer(o, UserId, db)
        if formatted:
            result.append(formatted)
    return {"data": result}

@router.get("/GetOffersByPromoCode")
def get_offers_by_promo(promoCode: str, UserId: str = "", db: Session = Depends(get_db)):
    now = datetime.now(SYDNEY_TZ).replace(tzinfo=None)
    offers = db.query(Offer).filter(
        Offer.is_promo == True,
        Offer.promo_code == promoCode,
        Offer.status == "approved"
    ).all()
    # Filter out expired promos
    offers = [o for o in offers if not o.promo_expiry or o.promo_expiry >= now]
    if not offers:
        raise HTTPException(status_code=404, detail="No offers found for this promo code")
    result = [format_offer(o, UserId, db) for o in offers]
    return {"data": result}

@router.post("/RedeemOffer")
def redeem_offer(OfferId: int, UserId: str, QRCode: str, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter(Offer.id == OfferId).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Verify QR code matches vendor
    vendor = db.query(Vendor).filter(Vendor.id == offer.vendor_id).first()
    if not vendor or vendor.qr_code != QRCode:
        raise HTTPException(status_code=400, detail="QR Code was not found")

    user = db.query(User).filter(User.id == UserId).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check subscription tier
    user_priority = get_user_tier_priority(user)
    offer_priority = TIER_PRIORITY.get(offer.required_tier or "free", 0)
    if user_priority < offer_priority:
        raise HTTPException(status_code=403, detail="Subscription upgrade required")

    # Check renewal lock
    last = get_last_redemption(UserId, OfferId, db)
    if last and offer.renew_duration:
        unlock_at = last.created_at + timedelta(days=offer.renew_duration)
        if datetime.utcnow() < unlock_at:
            raise HTTPException(status_code=400, detail=f"Offer locked until {unlock_at.strftime('%Y-%m-%d')}")

    # Record redemption
    transaction = OfferTransaction(
        user_id=UserId,
        offer_id=OfferId,
        created_at=datetime.utcnow()
    )
    db.add(transaction)
    offer.orders = (offer.orders or 0) + 1

    # Award points
    points_earned = offer.points or 0
    if points_earned > 0:
        user.total_points = (user.total_points or 0) + points_earned
        pt = PointTransaction(
            user_id=UserId,
            points=points_earned
        )
        db.add(pt)

    db.commit()
    return {
        "Message": "Offer redeemed successfully",
        "PointsEarned": points_earned,
        "TotalPoints": user.total_points,
        "TransactionOTP": transaction.id
    }

@router.post("/Search")
def search_offers(text: str, UserId: str = "", db: Session = Depends(get_db)):
    offers = db.query(Offer).filter(
        Offer.name.ilike(f"%{text}%"),
        Offer.status.in_(["active", "approved"])
    ).all()
    result = [format_offer(o, UserId, db) for o in offers]
    return {"data": [r for r in result if r is not None]}

@router.post("/SumSaveUpTo")
def sum_save_up_to(UserId: str = "", db: Session = Depends(get_db)):
    from sqlalchemy import func
    total = db.query(func.sum(Offer.save_up_to)).scalar() or 0
    return {"TotalSaveUpTo": float(total), "Currency": "AUD", "TotalPoints": 0}

@router.get("/GetTotalPoints")
def get_total_points(UserId: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == UserId).first()
    points = user.total_points or 0 if user else 0
    # Return ALL fields sumSaveUptoModel expects — non-optional Swift fields
    # (TotalSaveUpTo, Currency) must be present or Codable decode fails
    return {
        "TotalSaveUpTo": 0.0,
        "Currency": "AUD",
        "TotalPoints": points,
        "data": points
    }

@router.post("/RedeemPoints")
def redeem_points(UserId: str, Points: int, VendorId: str = "", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == UserId).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if (user.total_points or 0) < Points:
        raise HTTPException(status_code=400, detail="Not enough points")
    user.total_points -= Points
    pt = PointTransaction(
        user_id=UserId,
        points=-Points
    )
    db.add(pt)
    db.commit()
    return {"Message": "Points redeemed successfully", "RemainingPoints": user.total_points}
