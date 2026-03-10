from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os, threading, time, logging
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import auth, home, vendors, offers, favourites, notifications, subscriptions
from app.api.routes import categories
from app.admin.routes import router as admin_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(home.router)
app.include_router(vendors.router)
app.include_router(categories.router)
app.include_router(offers.router)
app.include_router(favourites.router)
app.include_router(notifications.router)
app.include_router(subscriptions.router)
app.include_router(admin_router)
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Scheduled Notification Worker ────────────────────────────────────────────

def _run_scheduled_notifications():
    """Background thread: checks every 60s for notifications due to be sent."""
    from datetime import datetime
    from app.db.session import SessionLocal
    from app.models.notification import Notification, UserNotification
    from app.models.user import User, MobileDevice
    from app.services.fcm import send_push_multicast
    from app.admin.routes import _get_target_users

    time.sleep(10)  # wait for app to fully start
    while True:
        try:
            db = SessionLocal()
            now = datetime.utcnow()
            due = db.query(Notification).filter(
                Notification.sent == False,
                Notification.scheduled_at != None,
                Notification.scheduled_at <= now
            ).all()

            for notif in due:
                users = _get_target_users(notif, db)
                for u in users:
                    exists = db.query(UserNotification).filter(
                        UserNotification.user_id == u.id,
                        UserNotification.notification_id == notif.id
                    ).first()
                    if not exists:
                        db.add(UserNotification(
                            user_id=u.id, notification_id=notif.id,
                            title=notif.title, message=notif.message,
                            image=notif.image, is_read=False, created_at=now
                        ))
                user_ids = [u.id for u in users]
                devices = db.query(MobileDevice).filter(MobileDevice.user_id.in_(user_ids)).all()
                tokens = list({d.token for d in devices if d.token})
                send_push_multicast(tokens, notif.title, notif.message, notif.image,
                                    notif.deep_link_type or "none", notif.deep_link_id or "")
                notif.sent = True
                logger.info(f"Scheduled notification {notif.id} sent to {len(tokens)} devices")

            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        time.sleep(60)


@app.on_event("startup")
def start_scheduler():
    t = threading.Thread(target=_run_scheduled_notifications, daemon=True)
    t.start()
    logger.info("Notification scheduler started")


@app.get("/")
def root():
    return {"message": f"Welcome to {settings.APP_NAME} API", "version": settings.APP_VERSION}

@app.get("/health")
def health():
    return {"status": "healthy"}
