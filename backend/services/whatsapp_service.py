# ✅ services/whatsapp_service.py (Improved)
import os
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(), override=False)
except Exception:
    pass

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client


class WhatsAppService:
    """
    Twilio WhatsApp sender.
    Auto-detects sandbox and enforces correct behavior.
    """

    SANDBOX_FROM = "whatsapp:+14155238886"

    def __init__(self) -> None:
        self.account_sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
        self.auth_token = (os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
        self.from_number = (os.getenv("TWILIO_WHATSAPP_FROM") or self.SANDBOX_FROM).strip()

        # ✅ Only use Messaging Service SID for production approved sender IDs
        self.messaging_service_sid = (
            os.getenv("TWILIO_MESSAGING_SERVICE_SID") or ""
        ).strip()

        if not self.account_sid or not self.auth_token:
            print("[WhatsAppService] ERROR: Missing SID or TOKEN")

        if not self.from_number.startswith("whatsapp:"):
            print("[WhatsAppService] Invalid FROM — forcing sandbox sender")
            self.from_number = self.SANDBOX_FROM

        self.client = Client(self.account_sid, self.auth_token)

    @staticmethod
    def _normalize_number(number: str) -> str:
        if not number:
            return ""
        number = number.strip()
        if number.startswith("whatsapp:"):
            return number
        if number.startswith("+"):
            return f"whatsapp:{number}"
        digits = "".join(ch for ch in number if ch.isdigit())
        return f"whatsapp:+{digits}" if digits else ""

    def _should_use_sandbox(self):
        """Check if using sandbox account SID prefix (ACxxx...)"""
        return self.from_number == self.SANDBOX_FROM

    def send_message(self, to_number: str, body: str) -> Optional[str]:

        to_wa = self._normalize_number(to_number)

        if not to_wa:
            print("[WhatsAppService] Invalid number")
            return None

        # ✅ Sandbox must have opt-in
        if self._should_use_sandbox():
            body = f"{body}\n\n👋 Reply *Hello* to stay opted-in."

        kwargs: Dict[str, Any] = {"to": to_wa, "body": body}

        # ✅ Only apply messaging service in approved environments
        if self.messaging_service_sid and not self._should_use_sandbox():
            kwargs["messaging_service_sid"] = self.messaging_service_sid
        else:
            kwargs["from_"] = self.from_number

        try:
            msg = self.client.messages.create(**kwargs)
            print(f"[WhatsAppService ✅] SID={msg.sid} → {to_wa}")
            return msg.sid

        except TwilioRestException as e:
            print(f"[WhatsAppService ❌ Twilio]")
            print(f"  Status={e.status} Code={e.code}")
            print(f"  Msg={e.msg}")
            print(f"  More={e.more_info}")
            return None

        except Exception as e:
            print(f"[WhatsAppService ❌ Unexpected] {e}")
            return None

    def user_opt_in_required(self, number: str) -> bool:
        """
        Check if this number must manually join sandbox.
        """
        return self._should_use_sandbox()
