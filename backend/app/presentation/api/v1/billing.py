"""Billing API — Stripe integration, subscription management, API keys.

Endpoints:
- GET    /billing/plans              — List available plans
- GET    /billing/subscription       — Current user's subscription
- POST   /billing/subscribe          — Create Stripe checkout session
- POST   /billing/portal             — Open Stripe customer portal
- POST   /billing/cancel             — Cancel subscription
- GET    /billing/invoices           — Invoice history
- GET    /billing/api-keys           — List API keys
- POST   /billing/api-keys           — Create API key
- DELETE /billing/api-keys/{key_id}  — Revoke API key
- POST   /billing/webhook            — Stripe webhook handler
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, update, func

from app.application.shared import UnitOfWork
from app.infrastructure.database.orm.billing import (
    BillingPlanModel,
    SubscriptionModel,
    InvoiceModel,
    ApiKeyModel,
    OrganizationModel,
    OrganizationMemberModel,
)
from app.presentation.dependencies import get_current_user_id, get_uow
from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Billing"])


# ============================================================
# Response Models
# ============================================================


class PlanResponse(BaseModel):
    slug: str
    name: str
    description: str | None
    price_cents: int
    currency: str
    interval: str
    features: dict
    max_users: int
    max_api_calls: int
    max_study_sessions: int


class PlansListResponse(BaseModel):
    plans: list[PlanResponse]


class SubscriptionResponse(BaseModel):
    plan_slug: str
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool


class CheckoutResponse(BaseModel):
    url: str
    session_id: str


class PortalResponse(BaseModel):
    url: str


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime


class ApiKeyCreatedResponse(BaseModel):
    id: UUID
    key: str  # Only returned once on creation
    name: str
    key_prefix: str
    scopes: list[str]


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=list)


class InvoiceResponse(BaseModel):
    id: UUID
    amount_cents: int
    currency: str
    status: str
    pdf_url: str | None
    hosted_url: str | None
    paid_at: datetime | None
    period_start: datetime | None
    period_end: datetime | None


# ============================================================
# Plans
# ============================================================


@router.get("/billing/plans", response_model=PlansListResponse)
async def list_plans(
    uow: UnitOfWork = Depends(get_uow),
) -> PlansListResponse:
    """List all active billing plans."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(BillingPlanModel)
                .where(BillingPlanModel.is_active == True)
                .order_by(BillingPlanModel.sort_order)
            )
            plans = result.scalars().all()

            # If no plans in DB, return default plans
            if not plans:
                return PlansListResponse(plans=_default_plans())

            return PlansListResponse(plans=[
                PlanResponse(
                    slug=p.slug,
                    name=p.name,
                    description=p.description,
                    price_cents=p.price_cents,
                    currency=p.currency,
                    interval=p.interval,
                    features=p.features if isinstance(p.features, dict) else {},
                    max_users=p.max_users,
                    max_api_calls=p.max_api_calls,
                    max_study_sessions=p.max_study_sessions,
                )
                for p in plans
            ])
    except Exception:
        return PlansListResponse(plans=_default_plans())


def _default_plans() -> list[PlanResponse]:
    """Default plans when DB is empty."""
    return [
        PlanResponse(
            slug="free",
            name="Free",
            description="Perfect for getting started",
            price_cents=0,
            currency="usd",
            interval="month",
            features={
                "study_sessions": "10 per month",
                "ai_explanations": "Basic only",
                "analytics": "Limited",
                "support": "Community",
            },
            max_users=1,
            max_api_calls=100,
            max_study_sessions=10,
        ),
        PlanResponse(
            slug="pro",
            name="Pro",
            description="For serious learners",
            price_cents=1999,
            currency="usd",
            interval="month",
            features={
                "study_sessions": "Unlimited",
                "ai_explanations": "Full access",
                "analytics": "Advanced",
                "support": "Priority email",
                "custom_templates": True,
                "export_data": True,
            },
            max_users=1,
            max_api_calls=10000,
            max_study_sessions=999999,
        ),
        PlanResponse(
            slug="team",
            name="Team",
            description="For teams and classrooms",
            price_cents=4999,
            currency="usd",
            interval="month",
            features={
                "study_sessions": "Unlimited",
                "ai_explanations": "Full access",
                "analytics": "Team dashboard",
                "support": "Priority + Slack",
                "custom_templates": True,
                "export_data": True,
                "shared_curriculum": True,
                "instructor_analytics": True,
            },
            max_users=25,
            max_api_calls=50000,
            max_study_sessions=999999,
        ),
    ]


# ============================================================
# Subscription Management
# ============================================================


@router.get("/billing/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> SubscriptionResponse:
    """Get the current user's subscription."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(SubscriptionModel)
                .where(
                    and_(
                        SubscriptionModel.user_id == user_id,
                        SubscriptionModel.status.in_(["active", "trialing", "past_due"]),
                    )
                )
                .order_by(SubscriptionModel.created_at.desc())
                .limit(1)
            )
            sub = result.scalar_one_or_none()

            if not sub:
                return SubscriptionResponse(
                    plan_slug="free",
                    status="active",
                    current_period_start=None,
                    current_period_end=None,
                    cancel_at_period_end=False,
                )

            return SubscriptionResponse(
                plan_slug=sub.plan_slug,
                status=sub.status,
                current_period_start=sub.current_period_start,
                current_period_end=sub.current_period_end,
                cancel_at_period_end=sub.cancel_at_period_end,
            )
    except Exception:
        return SubscriptionResponse(
            plan_slug="free",
            status="active",
            current_period_start=None,
            current_period_end=None,
            cancel_at_period_end=False,
        )


@router.post("/billing/subscribe", response_model=CheckoutResponse)
async def create_checkout(
    request: Request,
    plan_slug: str = "pro",
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> CheckoutResponse:
    """Create a Stripe Checkout Session for subscription."""
    settings = get_settings()
    stripe_secret = getattr(settings, "stripe_secret_key", None) or ""

    # If no Stripe key configured, return a mock URL
    if not stripe_secret:
        # Create/update subscription record directly (free tier or dev mode)
        try:
            async with uow as _uow:
                session = _uow._session  # type: ignore[union-attr]
                # Cancel existing active subscriptions
                await session.execute(
                    update(SubscriptionModel)
                    .where(
                        and_(
                            SubscriptionModel.user_id == user_id,
                            SubscriptionModel.status == "active",
                        )
                    )
                    .values(status="canceled", canceled_at=datetime.now(timezone.utc))
                )
                # Create new subscription
                new_sub = SubscriptionModel(
                    user_id=user_id,
                    plan_slug=plan_slug,
                    status="active",
                    current_period_start=datetime.now(timezone.utc),
                    current_period_end=None,
                )
                session.add(new_sub)
                await session.flush()
                await session.commit()

            return CheckoutResponse(
                url=f"{settings.frontend_base_url}/portal/billing?success=true&plan={plan_slug}",
                session_id="dev_mode",
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    # Real Stripe integration
    try:
        import stripe
        stripe.api_key = stripe_secret

        # Get the plan from DB
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(BillingPlanModel).where(BillingPlanModel.slug == plan_slug)
            )
            plan = result.scalar_one_or_none()

        if not plan or not plan.stripe_price_id:
            raise HTTPException(status_code=404, detail=f"Plan '{plan_slug}' not configured for Stripe")

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=f"{settings.frontend_base_url}/portal/billing?success=true",
            cancel_url=f"{settings.frontend_base_url}/portal/billing?canceled=true",
            client_reference_id=str(user_id),
            metadata={"user_id": str(user_id), "plan_slug": plan_slug},
        )

        return CheckoutResponse(url=checkout_session.url, session_id=checkout_session.id)
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/billing/portal", response_model=PortalResponse)
async def create_portal_session(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> PortalResponse:
    """Create a Stripe Customer Portal session."""
    settings = get_settings()
    stripe_secret = getattr(settings, "stripe_secret_key", None) or ""

    if not stripe_secret:
        return PortalResponse(url=f"{settings.frontend_base_url}/portal/billing")

    try:
        import stripe
        stripe.api_key = stripe_secret

        # Get Stripe customer ID
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(SubscriptionModel)
                .where(SubscriptionModel.user_id == user_id)
                .order_by(SubscriptionModel.created_at.desc())
                .limit(1)
            )
            sub = result.scalar_one_or_none()

        if not sub or not sub.stripe_customer_id:
            raise HTTPException(status_code=404, detail="No Stripe customer found")

        portal_session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=f"{settings.frontend_base_url}/portal/billing",
        )

        return PortalResponse(url=portal_session.url)
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/billing/cancel")
async def cancel_subscription(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Cancel the current subscription."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(SubscriptionModel)
                .where(
                    and_(
                        SubscriptionModel.user_id == user_id,
                        SubscriptionModel.status == "active",
                    )
                )
                .values(
                    status="canceled",
                    canceled_at=datetime.now(timezone.utc),
                    cancel_at_period_end=False,
                )
            )
            await session.commit()

        return {"message": "Subscription canceled successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Invoices
# ============================================================


@router.get("/billing/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[InvoiceResponse]:
    """List invoices for the current user."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(InvoiceModel)
                .where(InvoiceModel.user_id == user_id)
                .order_by(InvoiceModel.created_at.desc())
                .limit(50)
            )
            invoices = result.scalars().all()
            return [
                InvoiceResponse(
                    id=inv.id,
                    amount_cents=inv.amount_cents,
                    currency=inv.currency,
                    status=inv.status,
                    pdf_url=inv.pdf_url,
                    hosted_url=inv.hosted_url,
                    paid_at=inv.paid_at,
                    period_start=inv.period_start,
                    period_end=inv.period_end,
                )
                for inv in invoices
            ]
    except Exception:
        return []


# ============================================================
# API Keys
# ============================================================


def _hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_api_key() -> str:
    """Generate a new API key."""
    return f"mos_{secrets.token_urlsafe(32)}"


@router.get("/billing/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ApiKeyResponse]:
    """List API keys for the current user."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            result = await session.execute(
                select(ApiKeyModel)
                .where(
                    and_(
                        ApiKeyModel.user_id == user_id,
                        ApiKeyModel.revoked_at.is_(None),
                    )
                )
                .order_by(ApiKeyModel.created_at.desc())
            )
            keys = result.scalars().all()
            return [
                ApiKeyResponse(
                    id=k.id,
                    name=k.name,
                    key_prefix=k.key_prefix,
                    scopes=k.scopes if isinstance(k.scopes, list) else [],
                    last_used_at=k.last_used_at,
                    expires_at=k.expires_at,
                    is_active=k.is_active,
                    created_at=k.created_at,
                )
                for k in keys
            ]
    except Exception:
        return []


@router.post("/billing/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    request: CreateApiKeyRequest,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> ApiKeyCreatedResponse:
    """Create a new API key."""
    raw_key = _generate_api_key()
    key_hash = _hash_api_key(raw_key)
    key_prefix = raw_key[:12] + "..."

    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            new_key = ApiKeyModel(
                user_id=user_id,
                name=request.name,
                key_hash=key_hash,
                key_prefix=key_prefix,
                scopes=request.scopes,
                is_active=True,
            )
            session.add(new_key)
            await session.flush()
            await session.commit()

            return ApiKeyCreatedResponse(
                id=new_key.id,
                key=raw_key,
                name=new_key.name,
                key_prefix=key_prefix,
                scopes=request.scopes,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/billing/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Revoke an API key."""
    try:
        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]
            await session.execute(
                update(ApiKeyModel)
                .where(
                    and_(
                        ApiKeyModel.id == key_id,
                        ApiKeyModel.user_id == user_id,
                    )
                )
                .values(revoked_at=datetime.now(timezone.utc), is_active=False)
            )
            await session.commit()

        return {"message": "API key revoked successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# Stripe Webhook
# ============================================================


@router.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    """Handle Stripe webhook events."""
    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    settings = get_settings()
    stripe_secret = getattr(settings, "stripe_secret_key", None) or ""
    webhook_secret = getattr(settings, "stripe_webhook_secret", None) or ""

    if not stripe_secret or not webhook_secret:
        # Dev mode — just acknowledge
        return {"received": True}

    try:
        import stripe
        stripe.api_key = stripe_secret
        event = stripe.Webhook.construct_event(body, sig_header, webhook_secret)

        async with uow as _uow:
            session = _uow._session  # type: ignore[union-attr]

            if event["type"] == "checkout.session.completed":
                client_ref = event["data"]["object"].get("client_reference_id")
                if client_ref:
                    user_id = UUID(client_ref)
                    plan_slug = event["data"]["object"].get("metadata", {}).get("plan_slug", "pro")
                    sub_id = event["data"]["object"].get("subscription")
                    customer_id = event["data"]["object"].get("customer")

                    # Cancel existing
                    await session.execute(
                        update(SubscriptionModel)
                        .where(
                            and_(
                                SubscriptionModel.user_id == user_id,
                                SubscriptionModel.status == "active",
                            )
                        )
                        .values(status="canceled")
                    )

                    # Create new subscription
                    new_sub = SubscriptionModel(
                        user_id=user_id,
                        plan_slug=plan_slug,
                        stripe_subscription_id=sub_id,
                        stripe_customer_id=customer_id,
                        status="active",
                    )
                    session.add(new_sub)

            elif event["type"] == "customer.subscription.deleted":
                sub_id = event["data"]["object"].get("id")
                await session.execute(
                    update(SubscriptionModel)
                    .where(SubscriptionModel.stripe_subscription_id == sub_id)
                    .values(status="canceled", canceled_at=datetime.now(timezone.utc))
                )

            elif event["type"] == "invoice.paid":
                # Record invoice
                inv_data = event["data"]["object"]
                user_ref = inv_data.get("customer_email")  # Or use metadata
                # ... create InvoiceModel record

            await session.commit()

        return {"received": True}
    except Exception as exc:
        logger.error("stripe_webhook_error", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
