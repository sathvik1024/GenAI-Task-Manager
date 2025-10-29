# services/whatsapp_service.py
import os
from typing import Optional, Dict, Any

# ✅ Load .env even when imported from a REPL or a one-off script
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(), override=False)  # looks for .env up the tree
except Exception:
    pass  # if python-dotenv isn't installed, we just rely on real env vars

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client


class WhatsAppService:
    """
    Twilio WhatsApp sender with sandbox-safe defaults and rich error logging.
    Works with:
      - Sandbox "from": whatsapp:+14155238886
      - Phone numbers formatted as E.164, ALWAYS prefixed by 'whatsapp:'
    """

    def __init__(self) -> None:
        self.account_sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
        self.auth_token  = (os.getenv("TWILIO_AUTH_TOKEN")  or "").strip()

        # In sandbox this MUST be 'whatsapp:+14155238886'
        self.from_number = (os.getenv("TWILIO_WHATSAPP_FROM") or "whatsapp:+14155238886").strip()

        # Optional Messaging Service SID (only if your WA sender is attached to it)
        self.messaging_service_sid = (os.getenv("TWILIO_MESSAGING_SERVICE_SID") or "").strip()

        if not self.account_sid or not self.auth_token:
            print("[WhatsAppService] Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN")
        if not self.from_number.startswith("whatsapp:"):
            self.from_number = "whatsapp:+14155238886"
            print("[WhatsAppService] Forcing sandbox FROM to 'whatsapp:+14155238886'")

        # This will still raise if creds are missing — that's good (fast fail)
        self.client = Client(self.account_sid, self.auth_token)

    @staticmethod
    def _as_whatsapp_e164(number: str) -> str:
        number = (number or "").strip()
        if not number:
            return ""
        if number.startswith("whatsapp:"):
            return number
        if number.startswith("+"):
            return f"whatsapp:{number}"
        digits = "".join(ch for ch in number if ch.isdigit())
        return f"whatsapp:+{digits}" if digits else ""

    def send_message(self, to_number: str, body: str) -> Optional[str]:
        to_wa = self._as_whatsapp_e164(to_number)
        if not to_wa:
            print("[WhatsAppService] Invalid destination number")
            return None
        try:
            kwargs: Dict[str, Any] = {"to": to_wa, "body": body}
            if self.messaging_service_sid:
                kwargs["messaging_service_sid"] = self.messaging_service_sid
            else:
                kwargs["from_"] = self.from_number
            msg = self.client.messages.create(**kwargs)
            print(f"[WhatsAppService] Sent message SID={msg.sid} to {to_wa}")
            return msg.sid
        except TwilioRestException as e:
            print("[WhatsAppService] Twilio error:")
            print(f"  status={getattr(e, 'status', None)} code={getattr(e, 'code', None)}")
            print(f"  msg={str(e)}")
            print(f"  more_info={getattr(e, 'more_info', None)}")
            return None
        except Exception as e:
            print(f"[WhatsAppService] Unexpected error: {e}")
            return None

    def send_template_message(self, to_number: str, content_sid: str, content_variables: Dict[str, str]) -> Optional[str]:
        to_wa = self._as_whatsapp_e164(to_number)
        if not to_wa:
            print("[WhatsAppService] Invalid destination number")
            return None
        try:
            kwargs: Dict[str, Any] = {
                "to": to_wa,
                "content_sid": content_sid,
                "content_variables": content_variables,
            }
            if self.messaging_service_sid:
                kwargs["messaging_service_sid"] = self.messaging_service_sid
            else:
                kwargs["from_"] = self.from_number
            msg = self.client.messages.create(**kwargs)
            print(f"[WhatsAppService] Sent template SID={msg.sid} to {to_wa}")
            return msg.sid
        except TwilioRestException as e:
            print("[WhatsAppService] Twilio template error:")
            print(f"  status={getattr(e, 'status', None)} code={getattr(e, 'code', None)}")
            print(f"  msg={str(e)}")
            print(f"  more_info={getattr(e, 'more_info', None)}")
            return None
        except Exception as e:
            print(f"[WhatsAppService] Unexpected template error: {e}")
            return None
