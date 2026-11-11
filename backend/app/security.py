"""SSRF guard. Targets must be public HTTP(S) addresses at every hop."""
import ipaddress, socket
from urllib.parse import urlparse
from fastapi import HTTPException

def validate_url(value: str) -> str:
    parsed=urlparse(value)
    if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422,"Only absolute HTTP(S) URLs without credentials are supported.")
    host=parsed.hostname.lower()
    if host in {"localhost","metadata.google.internal","instance-data","169.254.169.254"} or host.endswith(".localhost"):
        raise HTTPException(422,"Localhost and cloud metadata targets are blocked.")
    try: addresses={item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme=="https" else 80), type=socket.SOCK_STREAM)}
    except socket.gaierror as exc: raise HTTPException(422,"Hostname could not be resolved.") from exc
    for address in addresses:
        ip=ipaddress.ip_address(address)
        if not ip.is_global:
            raise HTTPException(422,"Private, loopback, link-local, reserved and non-public addresses are blocked.")
    return value
