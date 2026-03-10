from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, MobileDevice
from app.core.security import hash_password, create_access_token
import random
import uuid

router = APIRouter(prefix="/api/Account", tags=["Account"])

def format_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone:
        return ""
    if phone.startswith("+"):
        return phone
    if phone.startswith("0"):
        return "+61" + phone[1:]
    return "+61" + phone

def get_token(user: User) -> str:
    return create_access_token({"sub": user.id, "email": user.email})

@router.post("/IsHasAccount")
def is_has_account(Phone: str, db: Session = Depends(get_db)):
    phone = format_phone(Phone)
    user = db.query(User).filter(User.phone_number == phone).first()
    if not user:
        raise HTTPException(status_code=400, detail="You don't have account")
    otp = random.randint(111111, 999999)
    user.otp = otp
    db.commit()
    print(f"OTP for {phone}: {otp}")
    return {"StatusCode": True}

@router.get("/getByPhoneNumber")
def get_by_phone(Phone: str, OTP: int, db: Session = Depends(get_db)):
    phone = format_phone(Phone)
    user = db.query(User).filter(
        User.phone_number == phone,
        User.otp == OTP
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="OTP is wrong")
    user.is_active = True
    db.commit()
    token = get_token(user)
    return {"data": {
        "Id": user.id,
        "FirstName": user.first_name,
        "LastName": user.last_name,
        "Email": user.email,
        "PhoneNumber": user.phone_number,
        "ProfileImage": user.profile_image or "",
        "Token": token,
        "TotalPoints": user.total_points,
        "BirthDate": str(user.birth_date) if user.birth_date else "",
        "GenderId": 0
    }}

@router.post("/Register")
async def register(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    params = dict(request.query_params)

    FirstName = form.get("FirstName") or params.get("FirstName", "")
    LastName = form.get("LastName") or params.get("LastName", "")
    Email = form.get("Email") or params.get("Email", "")
    PhoneNumber = form.get("PhoneNumber") or form.get("Phone") or params.get("PhoneNumber") or params.get("Phone", "")
    GenderId = int(form.get("GenderId") or params.get("GenderId") or 0)
    BirthDate = form.get("BirthDate") or params.get("BirthDate", "")

    print(f"REGISTER RECEIVED: FirstName={FirstName} LastName={LastName} Email={Email} PhoneNumber={PhoneNumber}")

    phone = format_phone(PhoneNumber)
    existing = db.query(User).filter(
        (User.phone_number == phone) | (User.email == Email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone or email already exists")
    otp = random.randint(111111, 999999)
    user = User(
        id=str(uuid.uuid4()),
        first_name=FirstName,
        last_name=LastName,
        email=Email,
        phone_number=phone,
        hashed_password="",
        gender_id=GenderId,
        birth_date=BirthDate if BirthDate else None,
        otp=otp,
        is_active=False,
        total_points=0
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"OTP for {phone}: {otp}")
    token = get_token(user)
    return {"data": {
        "Id": user.id,
        "FirstName": user.first_name,
        "LastName": user.last_name,
        "Email": user.email,
        "PhoneNumber": user.phone_number,
        "ProfileImage": user.profile_image or "",
        "Token": token,
        "TotalPoints": user.total_points or 0,
        "BirthDate": str(user.birth_date) if user.birth_date else "",
        "GenderId": 0
    }}

@router.post("/RegisterDevice")
async def register_device(
    request: Request,
    db: Session = Depends(get_db)
):
    # Accept both form-encoded body AND query params
    params = dict(request.query_params)
    try:
        body = await request.form()
        params.update({k: v for k, v in body.items()})
    except Exception:
        pass

    print(f"[RegisterDevice] params={params}")

    Token = params.get("Token", "")
    UserId = params.get("UserId", "")
    DeviceId = params.get("DeviceId", str(uuid.uuid4()))
    OS = params.get("OS", "IOS")

    if not Token or not UserId:
        print(f"[RegisterDevice] MISSING Token={bool(Token)} UserId={bool(UserId)}")
        return {"StatusCode": False}

    # Verify user exists (foreign key safety)
    user = db.query(User).filter(User.id == UserId).first()
    if not user:
        print(f"[RegisterDevice] User not found: {UserId}")
        return {"StatusCode": False}

    existing = db.query(MobileDevice).filter(
        MobileDevice.user_id == UserId,
        MobileDevice.device_id == DeviceId
    ).first()
    if existing:
        existing.token = Token
        existing.os = OS
    else:
        db.add(MobileDevice(user_id=UserId, device_id=DeviceId, token=Token, os=OS))
    db.commit()
    print(f"[RegisterDevice] Saved token for user {UserId[:12]}")
    return {"StatusCode": True}

@router.post("/UpdateInfo")
def update_info(UserId: str = "", ProfileImage: str = "", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == UserId).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.profile_image = ProfileImage
    db.commit()
    db.refresh(user)
    token = get_token(user)
    return {"data": {
        "Id": user.id,
        "FirstName": user.first_name,
        "LastName": user.last_name,
        "Email": user.email,
        "PhoneNumber": user.phone_number,
        "ProfileImage": user.profile_image or "",
        "Token": token,
        "TotalPoints": user.total_points,
        "BirthDate": str(user.birth_date) if user.birth_date else "",
        "GenderId": 0
    }}

@router.post("/UpdatePhone")
def update_phone(UserId: str = "", Phone: str = "", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == UserId).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.phone_number = format_phone(Phone)
    db.commit()
    db.refresh(user)
    token = get_token(user)
    return {"data": {
        "Id": user.id,
        "FirstName": user.first_name,
        "LastName": user.last_name,
        "Email": user.email,
        "PhoneNumber": user.phone_number,
        "ProfileImage": user.profile_image or "",
        "Token": token,
        "TotalPoints": user.total_points,
        "BirthDate": str(user.birth_date) if user.birth_date else "",
        "GenderId": 0
    }}
