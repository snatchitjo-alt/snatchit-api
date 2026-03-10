from pydantic import BaseModel
from typing import List, Optional
from app.schemas.vendor import VendorResponse
from app.schemas.offer import OfferResponse

class SliderResponse(BaseModel):
    Id: int
    Name: Optional[str] = None
    Image: Optional[str] = None
    VendorId: Optional[int] = None
    URL: Optional[str] = None
    SliderType: int = 0

    class Config:
        from_attributes = True

class HomeResponse(BaseModel):
    TopVendors: List[VendorResponse] = []
    TopOffers: List[OfferResponse] = []
    Sliders: List[SliderResponse] = []