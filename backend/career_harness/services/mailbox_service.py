from __future__ import annotations

import email
import imaplib
from contextlib import suppress
from datetime import UTC
from email.header import decode_header
from email.message import Message
from typing import Any

from career_harness.db.mailbox_repository import MailboxRepository
from career_harness.platform.secure_store import WritableSecretStore


def _header(value: str | None) -> str | None:
    if not value:
        return None
    return "".join(
        part.decode(charset or "utf-8", errors="replace") if isinstance(part, bytes) else part
        for part, charset in decode_header(value)
    )


def _preview(message: Message) -> str:
    if message.is_multipart():
        return "\n".join(
            text
            for part in message.walk()
            if part.get_content_type() == "text/plain"
            if (text := _preview(part))
        )[:4000]
    payload = message.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(message.get_content_charset() or "utf-8", errors="replace")[:4000]
    return str(payload or "")[:4000]


class MailboxService:
    def __init__(self, repository: MailboxRepository, secrets: WritableSecretStore) -> None:
        self.repository = repository
        self.secrets = secrets

    def save_account(self, values: dict[str, Any], secret: str) -> dict[str, Any]:
        account_id = str(values["account_id"])
        self.secrets.set(f"mailbox/{account_id}", secret)
        return self.repository.upsert_account({**values, "credential_ref": f"mailbox/{account_id}"})

    def _connect(self, account: dict[str, Any]) -> imaplib.IMAP4:
        secret = self.secrets.get(str(account["credential_ref"]))
        if secret is None:
            raise ValueError("邮箱凭据未配置，请重新保存账户")
        if account["security"] == "ssl":
            client: imaplib.IMAP4 = imaplib.IMAP4_SSL(
                account["imap_host"], int(account["imap_port"]), timeout=10
            )
        else:
            client = imaplib.IMAP4(account["imap_host"], int(account["imap_port"]), timeout=10)
            client.starttls()
        client.login(str(account["username"]), secret.reveal())
        return client

    def test(self, account_id: str) -> dict[str, Any]:
        account = self.repository.get_account(account_id)
        if account is None:
            raise KeyError("邮箱账户不存在")
        client = None
        try:
            client = self._connect(account)
            self.repository.record_test(account_id, status="ok")
            return {"account_id": account_id, "status": "ok"}
        except Exception as error:
            self.repository.record_test(
                account_id, status="failed", error_code=type(error).__name__
            )
            return {
                "account_id": account_id,
                "status": "failed",
                "message": "连接测试失败，请检查配置或网络",
            }
        finally:
            if client is not None:
                with suppress(Exception):
                    client.logout()

    def fetch(self, account_id: str, folder: str, limit: int = 20) -> tuple[dict[str, Any], ...]:
        if not 1 <= limit <= 50:
            raise ValueError("单次读取最多 50 封邮件")
        if not folder or len(folder) > 255:
            raise ValueError("邮箱文件夹无效")
        account = self.repository.get_account(account_id)
        if account is None:
            raise KeyError("邮箱账户不存在")
        client = self._connect(account)
        try:
            status, _ = client.select(folder, readonly=True)
            if status != "OK":
                raise ValueError("无法读取指定邮箱文件夹")
            status, data = client.search(None, "ALL")
            if status != "OK":
                raise ValueError("无法读取邮箱列表")
            ids = (data[0] or b"").split()[-limit:]
            result = []
            for raw_id in reversed(ids):
                status, payload = client.fetch(raw_id, "(RFC822)")
                if status != "OK" or not payload:
                    continue
                raw = next((item[1] for item in payload if isinstance(item, tuple)), b"")
                message = email.message_from_bytes(raw)
                message_id = f"{account_id}:{folder}:{raw_id.decode(errors='replace')}"
                received = (
                    email.utils.parsedate_to_datetime(message["Date"])
                    if message.get("Date")
                    else None
                )
                if received and received.tzinfo is None:
                    received = received.replace(tzinfo=UTC)
                result.append(
                    self.repository.save_message(
                        {
                            "message_id": message_id,
                            "account_id": account_id,
                            "folder": folder,
                            "sender": _header(message.get("From")),
                            "subject": _header(message.get("Subject")),
                            "received_at": received,
                            "preview": _preview(message),
                            "opportunity_id": None,
                            "application_id": None,
                        }
                    )
                )
            return tuple(result)
        finally:
            with suppress(Exception):
                client.logout()
