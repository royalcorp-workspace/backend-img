import base64
import json
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from ...infrastructure.config.settings import get_settings
from ...infrastructure.logging import get_logger

logger = get_logger()

FIREBASE_CERTS_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
)
FIREBASE_CERTS_CACHE_PATH = "/tmp/firebase_certs.json"
FIREBASE_CERTS_CACHE_TTL = 3600


def _base64url_decode(data: str) -> bytes:
    padded = data + "=" * (4 - len(data) % 4) if len(data) % 4 else data
    padded = padded.replace("-", "+").replace("_", "/")
    return base64.b64decode(padded)


def _get_firebase_certs() -> dict[str, str] | None:
    now = time.time()
    try:
        if Path(FIREBASE_CERTS_CACHE_PATH).exists():
            mtime = Path(FIREBASE_CERTS_CACHE_PATH).stat().st_mtime
            if now - mtime < FIREBASE_CERTS_CACHE_TTL:
                with open(FIREBASE_CERTS_CACHE_PATH) as f:
                    return json.load(f)
    except Exception:
        pass

    req = Request(FIREBASE_CERTS_URL, headers={"User-Agent": "backend-img"})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        Path(FIREBASE_CERTS_CACHE_PATH).write_text(json.dumps(data))
        return data
    except Exception as exc:
        logger.error(f"Failed to fetch Firebase certs: {exc}")
        return None


def verify_firebase_id_token(id_token: str) -> dict[str, Any] | None:
    try:
        parts = id_token.split(".")
        if len(parts) != 3:
            logger.warning("Firebase token has invalid format")
            return None

        header_b64, payload_b64, signature_b64 = parts
        header = json.loads(_base64url_decode(header_b64))
        if header.get("alg") != "RS256":
            logger.warning(f"Firebase token alg is not RS256: {header.get('alg')}")
            return None

        kid = header.get("kid")
        if not kid:
            logger.warning("Firebase token missing kid")
            return None

        payload = json.loads(_base64url_decode(payload_b64))
        now = time.time()
        if payload.get("exp", 0) <= now:
            logger.warning(
                f"Firebase token expired: exp={payload.get('exp')}, now={int(now)}, "
                f"delta={int(now) - payload.get('exp', 0)}s"
            )
            return None
        if payload.get("iat", 0) > now:
            logger.warning(
                f"Firebase token iat in the future: iat={payload.get('iat')}, now={int(now)}"
            )
            return None

        settings = get_settings()
        project_id = getattr(settings, "FIREBASE_PROJECT_ID", "")
        if not project_id:
            logger.error(
                "FIREBASE_PROJECT_ID is not configured — set it in .env. "
                "All Firebase tokens will be rejected until this is set."
            )
            return None
        if payload.get("aud") != project_id:
            logger.warning(
                f"Firebase token aud mismatch: got='{payload.get('aud')}', "
                f"expected='{project_id}' — pastikan FIREBASE_PROJECT_ID di .env sudah benar"
            )
            return None
        expected_iss = f"https://securetoken.google.com/{project_id}"
        if payload.get("iss") != expected_iss:
            logger.warning(
                f"Firebase token iss mismatch: got='{payload.get('iss')}', "
                f"expected='{expected_iss}'"
            )
            return None
        if not payload.get("sub"):
            logger.warning("Firebase token sub missing")
            return None

        certs = _get_firebase_certs()
        if not certs or kid not in certs:
            logger.warning(
                f"Firebase cert not found for kid: {kid}. "
                f"Available kids: {list(certs.keys()) if certs else 'none (fetch failed)'}"
            )
            return None

        cert = x509.load_pem_x509_certificate(certs[kid].encode())
        public_key = cert.public_key()
        signed_data = f"{header_b64}.{payload_b64}".encode()
        signature = _base64url_decode(signature_b64)

        try:
            public_key.verify(
                signature,
                signed_data,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except Exception as exc:
            logger.warning(f"Firebase token signature invalid: {exc}")
            return None

        return payload
    except Exception as exc:
        logger.error(f"Error verifying Firebase token: {exc}", exc_info=True)
        return None
