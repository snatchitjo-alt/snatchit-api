from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.category import Category
from app.api.routes.home import static_url

router = APIRouter(prefix="/api/Categories", tags=["Categories"])

@router.get("/GetCategories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return {"data": [
        {
            "Id": c.id,
            "Name": c.name or "",
            "Image": static_url(c.image),
            "ParentId": c.parent_id or 0,
            "Vendors": [{"Id": v.id} for v in c.vendors if v.is_active]
        } for c in categories
    ]}
