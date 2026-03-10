from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.vendor import Vendor
from app.models.offer import Offer
from app.models.slider import Slider
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["Home"])

def static_url(path: str) -> str:
    """Convert a /static/... path to a full URL."""
    if path and path.startswith("/static"):
        return f"{settings.BASE_URL}{path}"
    return path or ""

@router.get("/Home")
@router.get("/Home/GetHomeData")
def get_home(UserId: str = "", db: Session = Depends(get_db)):
    top_vendors = db.query(Vendor).filter(Vendor.is_top == True, Vendor.is_active == True).limit(10).all()
    top_offers = db.query(Offer).filter(Offer.is_top == True).limit(10).all()
    sliders = db.query(Slider).filter(Slider.is_active == True).order_by(Slider.display_order).all()

    return {"data": {
        "TopVendors": [format_vendor(v) for v in top_vendors],
        "TopOffers": [format_offer(o, UserId, db) for o in top_offers],
        "Sliders": [format_slider(s) for s in sliders]
    }}

def format_vendor(v: Vendor):
    return {
        "Id": v.id,
        "Name": v.name or "",
        "Description": v.description or "",
        "Phone": v.phone or "",
        "ProfileImage": static_url(v.profile_image),
        "BannerImage": static_url(v.banner_image),
        "QRCode": v.qr_code or "",
        "Lat": v.lat or "",
        "Lon": v.lon or "",
        "CategoryId": v.category_id or 0,
        "IsActive": v.is_active,
        "IsTop": v.is_top,
        "Orders": v.orders or 0,
        "Offers": [{"Id": o.id} for o in v.offers if o.status in ("active", "approved") and not o.is_promo]
    }

def format_offer(o: Offer, user_id: str, db: Session):
    from app.api.routes.offers import format_offer as _format_offer
    return _format_offer(o, user_id, db)

def format_slider(s: Slider):
    # Map link_type to iOS SliderType: 0=vendor, 2=web url, 4=subscription
    type_map = {"vendor": 0, "web": 2, "subscription": 4}
    slider_type = type_map.get(s.link_type or "web", 2)
    return {
        "Id": s.id,
        "Name": s.name or "",
        "Image": static_url(s.image),
        "VendorId": s.target_id or s.vendor_id or 0,
        "URL": s.url or "",
        "SliderType": slider_type,
        "DisplaySeconds": s.display_seconds or 5
    }
