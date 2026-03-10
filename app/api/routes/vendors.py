from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.vendor import Vendor
from app.api.routes.home import format_vendor

router = APIRouter(prefix="/api/Vendors", tags=["Vendors"])

@router.get("")
def get_all_vendors(db: Session = Depends(get_db)):
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    return {"data": [format_vendor(v) for v in vendors]}

@router.get("/GetVendorsByCategoryId")
def get_vendors_by_category(CategoryId: int, db: Session = Depends(get_db)):
    vendors = db.query(Vendor).filter(
        Vendor.category_id == CategoryId,
        Vendor.is_active == True
    ).all()
    return {"data": [format_vendor(v) for v in vendors]}

@router.get("/GetVendorById")
def get_vendor_by_id(id: int, UserId: str = "", db: Session = Depends(get_db)):
    VendorId = id
    vendor = db.query(Vendor).filter(Vendor.id == VendorId).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    from app.models.offer import Offer
    from app.api.routes.offers import format_offer
    offers = db.query(Offer).filter(Offer.vendor_id == VendorId, Offer.status.in_(["active", "approved"]), Offer.is_promo == False).all()
    result = format_vendor(vendor)
    result["Offers"] = [format_offer(o, UserId, db) for o in offers]
    return result

@router.get("/Search")
def search_vendors(text: str, db: Session = Depends(get_db)):
    vendors = db.query(Vendor).filter(
        Vendor.name.ilike(f"%{text}%"),
        Vendor.is_active == True
    ).all()
    return {"data": [format_vendor(v) for v in vendors]}

@router.get("/GetPOSVendors")
def get_pos_vendors(db: Session = Depends(get_db)):
    vendors = db.query(Vendor).filter(Vendor.is_pos == True, Vendor.is_active == True).all()
    return {"data": [format_vendor(v) for v in vendors]}
