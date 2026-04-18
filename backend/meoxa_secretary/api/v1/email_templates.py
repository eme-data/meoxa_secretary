"""CRUD des templates d'emails par tenant."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from meoxa_secretary.core.deps import (
    CurrentAuth,
    TenantDB,
    require_active_subscription,
)
from meoxa_secretary.models.email_template import EmailTemplate

router = APIRouter(dependencies=[Depends(require_active_subscription)])


class TemplateIn(BaseModel):
    name: str
    description: str = ""
    prompt: str


class TemplateOut(BaseModel):
    id: UUID
    name: str
    description: str
    prompt: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TemplateOut])
def list_templates(db: TenantDB, _: CurrentAuth) -> list[TemplateOut]:
    rows = db.scalars(select(EmailTemplate).order_by(EmailTemplate.name)).all()
    return [TemplateOut.model_validate(r) for r in rows]


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    body: TemplateIn, db: TenantDB, auth: CurrentAuth
) -> TemplateOut:
    template = EmailTemplate(
        tenant_id=auth.tenant_id,  # type: ignore[arg-type]
        name=body.name,
        description=body.description,
        prompt=body.prompt,
    )
    db.add(template)
    db.flush()
    db.refresh(template)
    return TemplateOut.model_validate(template)


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: UUID, body: TemplateIn, db: TenantDB, _: CurrentAuth
) -> TemplateOut:
    template = db.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template introuvable")
    template.name = body.name
    template.description = body.description
    template.prompt = body.prompt
    db.commit()
    db.refresh(template)
    return TemplateOut.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: UUID, db: TenantDB, _: CurrentAuth) -> None:
    template = db.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template introuvable")
    db.delete(template)
    db.commit()


class ApplyTemplateRequest(BaseModel):
    thread_id: UUID


@router.post("/{template_id}/apply", response_model=dict)
def apply_template(
    template_id: UUID,
    body: ApplyTemplateRequest,
    db: TenantDB,
    auth: CurrentAuth,
) -> dict:
    """Relance draft_reply avec le prompt du template comme override."""
    from meoxa_secretary.models.email import EmailStatus, EmailThread
    from meoxa_secretary.workers.tasks.emails import draft_reply

    template = db.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template introuvable")
    thread = db.get(EmailThread, body.thread_id)
    if not thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread introuvable")

    thread.status = EmailStatus.PENDING
    thread.suggested_reply = None
    db.commit()

    draft_reply.delay(
        thread_id=str(thread.id),
        tenant_id=str(auth.tenant_id),
        user_id=str(auth.user.id),
        template_prompt=template.prompt,
    )
    return {"status": "queued", "template": template.name}
