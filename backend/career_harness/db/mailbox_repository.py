from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, text

from career_harness.core.common import utc_now


class MailboxRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def upsert_account(self, values: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        payload = {
            **values,
            "enabled": values.get("enabled", True),
            "last_tested_at": values.get("last_tested_at"),
            "last_test_status": values.get("last_test_status"),
            "last_error_code": values.get("last_error_code"),
            "updated_at": now,
            "created_at": values.get("created_at", now),
        }
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO communication_mailbox_account "
                    "(account_id,display_name,provider,username,imap_host,imap_port,security,"
                    "credential_ref,enabled,last_tested_at,last_test_status,last_error_code,"
                    "created_at,updated_at) "
                    "VALUES (:account_id,:display_name,:provider,:username,:imap_host,:imap_port,"
                    ":security,:credential_ref,:enabled,:last_tested_at,:last_test_status,"
                    ":last_error_code,:created_at,:updated_at) "
                    "ON CONFLICT(account_id) DO UPDATE SET "
                    "display_name=:display_name,provider=:provider,"
                    "username=:username,imap_host=:imap_host,imap_port=:imap_port,security=:security,"
                    "credential_ref=:credential_ref,enabled=:enabled,updated_at=:updated_at"
                ),
                payload,
            )
        return self.get_account(str(values["account_id"])) or payload

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM communication_mailbox_account WHERE account_id=:id"),
                    {"id": account_id},
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def list_accounts(self) -> tuple[dict[str, Any], ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text("SELECT * FROM communication_mailbox_account ORDER BY account_id")
                )
                .mappings()
                .all()
            )
        return tuple(dict(row) for row in rows)

    def record_test(self, account_id: str, *, status: str, error_code: str | None = None) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE communication_mailbox_account SET last_tested_at=:at,"
                    "last_test_status=:status,last_error_code=:error,updated_at=:at "
                    "WHERE account_id=:id"
                ),
                {"id": account_id, "at": utc_now(), "status": status, "error": error_code},
            )

    def save_message(self, values: dict[str, Any]) -> dict[str, Any]:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO communication_mail_message "
                    "(message_id,account_id,folder,sender,subject,received_at,preview,"
                    "opportunity_id,application_id,imported_at) "
                    "VALUES (:message_id,:account_id,:folder,:sender,:subject,:received_at,"
                    ":preview,:opportunity_id,:application_id,:imported_at) "
                    "ON CONFLICT(message_id) DO UPDATE SET "
                    "opportunity_id=:opportunity_id,application_id=:application_id"
                ),
                {**values, "imported_at": values.get("imported_at", utc_now())},
            )
        return self.get_message(str(values["message_id"])) or values

    def get_message(self, message_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM communication_mail_message WHERE message_id=:id"),
                    {"id": message_id},
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def list_messages(self, account_id: str) -> tuple[dict[str, Any], ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT * FROM communication_mail_message "
                        "WHERE account_id=:id ORDER BY received_at DESC"
                    ),
                    {"id": account_id},
                )
                .mappings()
                .all()
            )
        return tuple(dict(row) for row in rows)

    def associate_message(
        self, message_id: str, *, opportunity_id: str | None, application_id: str | None
    ) -> dict[str, Any]:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE communication_mail_message SET opportunity_id=:opportunity_id, "
                    "application_id=:application_id WHERE message_id=:message_id"
                ),
                {
                    "message_id": message_id,
                    "opportunity_id": opportunity_id,
                    "application_id": application_id,
                },
            )
        return self.get_message(message_id) or {}
