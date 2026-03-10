from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.offer import Offer, Favourite
from app.api.routes.home import format_offer

router = APIRouter(prefix="/api/Favourites", tags=["Favourites"])

@router.get("/GetAll")
def get_favourites(UserId: str, db: Session = Depends(get_db)):
    favs = db.query(Favourite).filter(Favourite.user_id == UserId).all()
    offers = [db.query(Offer).filter(Offer.id == f.offer_id).first() for f in favs]
    offers = [o for o in offers if o]
    return {"data": [format_offer(o, UserId, db) for o in offers]}

@router.post("/AddFavourite")
def add_favourite(UserId: str, OfferId: int, db: Session = Depends(get_db)):
    existing = db.query(Favourite).filter(
        Favourite.user_id == UserId,
        Favourite.offer_id == OfferId
    ).first()
    if not existing:
        fav = Favourite(user_id=UserId, offer_id=OfferId)
        db.add(fav)
        db.commit()
    return {"StatusCode": True}

@router.post("/DeleteFavourite")
def delete_favourite(UserId: str, OfferId: int, db: Session = Depends(get_db)):
    fav = db.query(Favourite).filter(
        Favourite.user_id == UserId,
        Favourite.offer_id == OfferId
    ).first()
    if fav:
        db.delete(fav)
        db.commit()
    return {"StatusCode": True}
