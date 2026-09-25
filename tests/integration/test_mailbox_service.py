from email.message import EmailMessage
from pathlib import Path

from career_harness.db.mailbox_repository import MailboxRepository
from career_harness.platform.secure_store import MemorySecretStore
from career_harness.services.mailbox_service import MailboxService
from tests.integration.test_fact_service import _engine


class FakeImap:
    def __init__(self, *args, **kwargs):
        self.logged_in = False

    def login(self, username, password):
        self.logged_in = username == "person@example.com" and password == "app-password"
        return ("OK", [b"logged in"])

    def select(self, folder, readonly=True):
        assert folder == "INBOX"
        assert readonly is True
        return ("OK", [b"1"])

    def search(self, charset, query):
        assert charset is None and query == "ALL"
        return ("OK", [b"1"])

    def fetch(self, message_id, query):
        assert message_id == b"1" and query == "(RFC822)"
        message = EmailMessage()
        message["From"] = "recruiter@example.com"
        message["Subject"] = "Interview"
        message["Date"] = "Tue, 24 Sep 2026 10:00:00 +0800"
        message.set_content("Please confirm a time.")
        return ("OK", [(b"header", message.as_bytes())])

    def logout(self):
        return ("BYE", [b"logged out"])


def test_mailbox_configuration_uses_secret_store_and_read_is_manual(
    tmp_path: Path, monkeypatch
) -> None:
    repository = MailboxRepository(_engine(tmp_path))
    secrets = MemorySecretStore()
    service = MailboxService(repository, secrets)
    account = service.save_account(
        {
            "account_id": "mailbox_test",
            "display_name": "求职邮箱",
            "provider": "test",
            "username": "person@example.com",
            "imap_host": "imap.example.com",
            "imap_port": 993,
            "security": "ssl",
            "enabled": True,
        },
        "app-password",
    )
    assert account["credential_ref"] == "mailbox/mailbox_test"
    assert "app-password" not in str(account)
    monkeypatch.setattr("career_harness.services.mailbox_service.imaplib.IMAP4_SSL", FakeImap)
    assert service.test("mailbox_test")["status"] == "ok"
    messages = service.fetch("mailbox_test", "INBOX", 20)
    assert len(messages) == 1
    assert messages[0]["subject"] == "Interview"
    assert messages[0]["preview"].startswith("Please confirm")
    associated = repository.associate_message(
        messages[0]["message_id"], opportunity_id="opp_1", application_id="app_1"
    )
    assert associated["opportunity_id"] == "opp_1"
    assert associated["application_id"] == "app_1"
