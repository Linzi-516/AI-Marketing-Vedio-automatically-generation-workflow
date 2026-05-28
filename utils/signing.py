"""Request signing helpers for Volcengine APIs."""

import datetime
import hashlib
import hmac


def sign_volcengine_request(
    method: str,
    path: str,
    params: dict,
    body: str,
    ak: str,
    sk: str,
    host: str = "visual.volcengineapi.com",
    region: str = "cn-north-1",
    service: str = "cv",
) -> dict:
    """Return signed Volcengine request headers."""
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%Y%m%d")
    datetime_str = now.strftime("%Y%m%dT%H%M%SZ")

    canonical_uri = path
    canonical_querystring = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    headers = {
        "content-type": "application/json",
        "host": host,
        "x-date": datetime_str,
    }
    canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted(headers.items()))
    signed_headers = ";".join(sorted(headers.keys()))
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    canonical_request = "\n".join([
        method,
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        body_hash,
    ])

    credential_scope = f"{date_str}/{region}/{service}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256",
        datetime_str,
        credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    def _hmac(key, msg):
        return hmac.new(
            key if isinstance(key, bytes) else key.encode(),
            msg.encode(),
            hashlib.sha256,
        ).digest()

    signing_key = _hmac(_hmac(_hmac(_hmac(sk, date_str), region), service), "request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )
    return {**headers, "Authorization": authorization}
