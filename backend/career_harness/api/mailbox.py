from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Query
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.services.mailbox_service import MailboxService


class MailboxAccountRequest(FrozenModel):
    account_id: str = Field(min_length=3, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)
    provider: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=512)
    imap_host: str = Field(min_length=1, max_length=512)
    imap_port: int = Field(default=993, ge=1, le=65535)
    security: str = Field(default="ssl", pattern="^(ssl|starttls)$")
    secret: str = Field(min_length=1, max_length=4096)


class MailboxTestRequest(FrozenModel):
    account_id: str = Field(min_length=3, max_length=128)


class MailMessageAssociationRequest(FrozenModel):
    opportunity_id: str | None = Field(default=None, max_length=128)
    application_id: str | None = Field(default=None, max_length=128)


@dataclass(frozen=True, slots=True)
class MailboxApi:
    service: MailboxService


def create_mailbox_router(api: MailboxApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/mailbox", tags=["mailbox"])

    @router.get("/accounts")
    def accounts():
        return api.service.repository.list_accounts()

    @router.post("/accounts", status_code=201)
    def save_account(request: MailboxAccountRequest):
        try:
            return api.service.save_account(request.model_dump(exclude={"secret"}), request.secret)
        except Exception as error:
            raise HTTPException(422, "邮箱账户配置未保存") from error

    @router.post("/test")
    def test(request: MailboxTestRequest):
        try:
            return api.service.test(request.account_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error

    @router.post("/{account_id}/messages")
    def fetch(
        account_id: str,
        folder: str = Query(default="INBOX", min_length=1, max_length=255),
        limit: int = Query(default=20, ge=1, le=50),
    ):
        try:
            return api.service.fetch(account_id, folder, limit)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except Exception as error:
            raise HTTPException(422, "邮件读取失败，请检查连接配置和文件夹") from error

    @router.get("/{account_id}/messages")
    def messages(account_id: str):
        return api.service.repository.list_messages(account_id)

    @router.patch("/messages/{message_id:path}/association")
    def associate(message_id: str, request: MailMessageAssociationRequest):
        try:
            return api.service.repository.associate_message(
                message_id,
                opportunity_id=request.opportunity_id,
                application_id=request.application_id,
            )
        except Exception as error:
            raise HTTPException(422, "邮件关联未保存") from error

    return router
