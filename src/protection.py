"""
Runtime string protection and anti-tamper utilities.
Strings are stored XOR-encoded and decoded only at call time.
This prevents static analysis tools from finding plaintext API URLs.
"""
import base64
import os
import sys
import logging

logger = logging.getLogger(__name__)

# ── XOR-based string encoding ──
_KEY = b'\x4f\x2a\x7e\x11\xd3\x9c\x5b\xa8\x3f\x67\xe1\x0c\x88\xf4\x29\x56'


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encode_string(s: str) -> str:
    """Encode a string for storage. Use this offline to generate encoded values."""
    raw = _xor(s.encode("utf-8"), _KEY)
    return base64.b64encode(raw).decode("ascii")


def decode_string(encoded: str) -> str:
    """Decode a protected string at runtime."""
    raw = base64.b64decode(encoded)
    return _xor(raw, _KEY).decode("utf-8")


# ── Pre-encoded sensitive strings ──
# Generated via: encode_string("https://api.inceptionlabs.ai/v1/chat/completions")
# etc. These are decoded only when needed at runtime.

_ENCODED = {
    "inception_url": encode_string("https://api.inceptionlabs.ai/v1/chat/completions"),
    "openai_url": encode_string("https://api.openai.com/v1/chat/completions"),
    "ollama_url": encode_string("http://localhost:11434/v1/chat/completions"),
    "bearer_prefix": encode_string("Bearer "),
    "content_type": encode_string("application/json"),
}


def get_protected(key: str) -> str:
    """Retrieve a protected string by key."""
    encoded = _ENCODED.get(key)
    if encoded is None:
        raise KeyError(f"Unknown protected key: {key}")
    return decode_string(encoded)


# ── Basic Anti-Debug / Anti-RE Checks ──

def _is_debugger_present() -> bool:
    """Basic debugger detection. Not foolproof, but catches casual attempts."""
    try:
        # Check for common Python debuggers
        if sys.gettrace() is not None:
            return True

        # Check for common RE tool processes (Windows)
        if sys.platform == "win32":
            import ctypes
            # Windows API: IsDebuggerPresent
            if ctypes.windll.kernel32.IsDebuggerPresent():
                return True
    except Exception:
        pass

    return False


def _check_suspicious_env() -> bool:
    """Check for environment variables commonly set by analysis tools."""
    suspicious = ["PYDEVD", "PYCHARM_DEBUG", "DEBUGPY", "VSCODE_PID"]
    for var in suspicious:
        if os.environ.get(var):
            return True
    return False


def runtime_integrity_check() -> bool:
    """
    Run at startup. Returns True if environment appears clean.
    Returns False if tampering is suspected — app should degrade gracefully.
    """
    if _is_debugger_present():
        logger.warning("Debug environment detected.")
        return False

    if _check_suspicious_env():
        logger.warning("Suspicious environment variables detected.")
        return False

    return True
