import firebase_admin
from firebase_admin import credentials, messaging
import os
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

_initialized = False

def _init_firebase():
    global _initialized
    if _initialized:
        return
    try:
        # Option 1: credentials as JSON string in env var (for Railway / cloud)
        cred_json = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "")
        if cred_json:
            import json
            cred = credentials.Certificate(json.loads(cred_json))
        else:
            # Option 2: credentials file path (for local development)
            cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
            if not os.path.exists(cred_path):
                logger.warning(f"Firebase credentials not found at {cred_path}. Push notifications disabled.")
                return
            cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("Firebase Admin SDK initialized.")
    except Exception as e:
        logger.error(f"Firebase init failed: {e}")


def send_push(token: str, title: str, body: str, image: str = None,
              deep_link_type: str = "none", deep_link_id: str = "") -> bool:
    """Send a push notification to a single FCM token. Returns True on success."""
    _init_firebase()
    if not _initialized:
        return False
    try:
        data = {"deep_link_type": deep_link_type or "none", "deep_link_id": deep_link_id or ""}
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body, image=image or None),
            data=data,
            token=token,
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default")
                )
            ),
        )
        messaging.send(msg)
        return True
    except Exception as e:
        logger.error(f"FCM send failed for token {token[:20]}...: {e}")
        return False


def send_push_multicast(tokens: list[str], title: str, body: str, image: str = None,
                        deep_link_type: str = "none", deep_link_id: str = "") -> int:
    """Send to multiple tokens. Returns count of successes."""
    _init_firebase()
    if not _initialized or not tokens:
        return 0
    data = {"deep_link_type": deep_link_type or "none", "deep_link_id": deep_link_id or ""}
    success = 0
    for i in range(0, len(tokens), 500):
        batch = tokens[i:i+500]
        try:
            msg = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body, image=image or None),
                data=data,
                tokens=batch,
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default")
                    )
                ),
            )
            response = messaging.send_each_for_multicast(msg)
            success += response.success_count
        except Exception as e:
            logger.error(f"FCM multicast failed: {e}")
    return success
