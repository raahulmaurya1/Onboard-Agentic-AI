"""
app/services/risk_engine.py
============================
Risk Engine Orchestrator — bridges the onboarding flow with the 3-tier
risk scoring pipeline and the human-review workflow.

Responsibilities
----------------
- Call :func:`app.agents.risk_agent.evaluate_full_risk` with merged
  user / telemetry / additional-info data.
- Route the outcome to one of three paths:
    • **REJECT**        → mark ``user_initial.status = 'rejected'``
    • **AUTO_APPROVE**  → mark ``user_initial.status = 'approved'``
    • **MANUAL_REVIEW** → mark ``user_initial.status = 'pending_review'``,
      collect review data for the bank reviewer interface.
- Collect and structure review data (user info, additional info,
  documents with base64 file content, risk flags) for the human
  reviewer.

PRIVACY GUARANTEE
-----------------
- Raw PII is NEVER logged by this module.
- Only redacted identifiers appear in log messages.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.agents.risk_agent import evaluate_full_risk
from app.db.base import AsyncSessionLocal
from app.db.models.user import UserInitial, AdditionalInfo
from app.db.models.document import UserDocument
from app.db.models.session import OnboardingSession
from app.storage.minio import get_minio_file

# ---------------------------------------------------------------------------
# Module-level logger — MUST NOT emit PII
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. MAIN ORCHESTRATOR
# ---------------------------------------------------------------------------


async def process_onboarding(
    user_id: str,
    user_record: Dict[str, Any],
    telemetry_data: Dict[str, Any],
    additional_info_record: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Orchestrate the risk-evaluation step of onboarding.

    Parameters
    ----------
    user_id:
        The ``user_initial.id`` (ULID) of the applicant.
    user_record:
        Core identity fields forwarded to the risk agent.
    telemetry_data:
        Real-time telemetry from the front-end SDK.
    additional_info_record:
        Regulatory / supplementary fields collected during onboarding.

    Returns
    -------
    dict
        One of:
        - ``{"action": "reject",        "message": "..."}``
        - ``{"action": "approve",       "message": "..."}``
        - ``{"action": "manual_review", "message": "...", "data": {...}}``
    """
    # ── 1. Call the 3-tier risk agent ─────────────────────────────────────
    risk_result: Dict[str, Any] = await evaluate_full_risk(
        user_record=user_record,
        telemetry_data=telemetry_data,
        additional_info_record=additional_info_record,
    )

    total_score: int = risk_result.get("score", 0)
    category: str = risk_result.get("category", "MANUAL_REVIEW")
    flags: List[str] = risk_result.get("flags", [])

    # ── 2. Log final score (no PII) ──────────────────────────────────────
    logger.info(
        "risk_engine: user=%s total_score=%d category=%s flag_count=%d",
        user_id[:8] + "…",      # redacted ULID prefix only
        total_score,
        category,
        len(flags),
    )
    print(
        f"[RiskEngine] user_id={user_id[:8]}… | "
        f"score={total_score} | category={category} | flags={flags}"
    )

    # ── 3. Route based on category ───────────────────────────────────────
    async with AsyncSessionLocal() as db:
        if category == "REJECT":
            return await _handle_reject(user_id, db)

        if category == "AUTO_APPROVE":
            return await _handle_auto_approve(user_id, db)

        # Default: MANUAL_REVIEW
        return await _handle_manual_review(user_id, flags, db)


# ---------------------------------------------------------------------------
# 2. OUTCOME HANDLERS
# ---------------------------------------------------------------------------


async def _handle_reject(
    user_id: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    REJECT path — mark the user as rejected.

    The ``user_initial`` row is preserved for audit; only the status
    is updated.  Related data (additional_info, user_documents, MinIO
    files) is intentionally **kept** so it can be reviewed later if
    needed.
    """
    await db.execute(
        update(UserInitial)
        .where(UserInitial.id == user_id)
        .values(status="rejected")
    )
    await db.commit()

    logger.info("risk_engine: REJECT applied for user=%s", user_id[:8] + "…")

    return {
        "action": "reject",
        "message": "Application rejected.",
    }


async def _handle_auto_approve(
    user_id: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    AUTO_APPROVE path — mark the user as approved.
    """
    await db.execute(
        update(UserInitial)
        .where(UserInitial.id == user_id)
        .values(status="approved")
    )
    await db.commit()

    logger.info("risk_engine: AUTO_APPROVE applied for user=%s", user_id[:8] + "…")

    return {
        "action": "approve",
        "message": "Your application has been approved!",
    }


async def _handle_manual_review(
    user_id: str,
    risk_flags: List[str],
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    MANUAL_REVIEW path — set status to ``MANUAL_REVIEW`` and collect
    all related data for the bank reviewer.
    """
    await db.execute(
        update(UserInitial)
        .where(UserInitial.id == user_id)
        .values(status="MANUAL_REVIEW")
    )
    await db.commit()

    logger.info(
        "risk_engine: MANUAL_REVIEW applied for user=%s", user_id[:8] + "…"
    )

    review_data = await collect_review_data(user_id, risk_flags=risk_flags, llm_flags=[])

    return {
        "action": "manual_review",
        "data": review_data,
        "message": "A team member of our bank will verify your application.",
    }


# ---------------------------------------------------------------------------
# 3. REVIEW DATA COLLECTOR
# ---------------------------------------------------------------------------


async def collect_review_data(
    user_id: str,
    risk_flags: List[str],
    llm_flags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Gather all data associated with *user_id* that a bank reviewer
    needs to make an approve / reject decision.

    Returns
    -------
    dict
        ::

            {
                "user_info":        { ... },
                "additional_info":  { ... } | None,
                "documents":        [ { "document_id", "file_type",
                                        "file_url", "status" }, ... ],
                "risk_flags":       [ "flag1", "flag2", ... ]
            }
    """
    async with AsyncSessionLocal() as db:
        # ── User row ─────────────────────────────────────────────────────
        user_result = await db.execute(
            select(UserInitial).where(UserInitial.id == user_id)
        )
        user_row = user_result.scalars().first()

        user_info: Dict[str, Any] = {}
        if user_row:
            user_info = {
                "id": user_row.id,
                "phone": user_row.phone,
                "email": user_row.email,
                "status": user_row.status,
                "name": user_row.name,
                "father_name": user_row.father_name,
                "address": user_row.address,
                "dob": user_row.dob,
                "aadhar_id": user_row.aadhar_id,
                "pan_id": user_row.pan_id,
                "account_type": user_row.account_type,
                "face_verified": user_row.face_verified,
                "verified_data": user_row.verified_data,
                "raw_archive": user_row.raw_archive,
                "created_at": str(user_row.created_at) if user_row.created_at else None,
            }

        # ── Additional info ──────────────────────────────────────────────
        addl_result = await db.execute(
            select(AdditionalInfo).where(
                AdditionalInfo.session_ulid == user_id
            )
        )
        addl_row = addl_result.scalars().first()
        additional_info_data: Optional[Dict[str, Any]] = (
            addl_row.data if addl_row else None
        )

        # ── Documents (join through sessions) ────────────────────────────
        # user_documents.session_id → sessions.session_id
        # sessions.user_id → user_initial.id
        session_result = await db.execute(
            select(OnboardingSession.session_id)
            .where(OnboardingSession.user_id == user_id)
        )
        session_id_list = [row[0] for row in session_result.fetchall()]

        if session_id_list:
            doc_result = await db.execute(
                select(UserDocument).where(
                    UserDocument.session_id.in_(session_id_list)
                )
            )
            doc_rows = doc_result.scalars().all()
        else:
            doc_rows = []

        documents: List[Dict[str, Any]] = []
        for doc in doc_rows:
            doc_entry: Dict[str, Any] = {
                "document_id": doc.document_id,
                "file_type": doc.file_type,
                "file_url": doc.file_url,
                "status": doc.status,
            }

            # Attempt to retrieve file content from MinIO
            if doc.file_url:
                try:
                    file_bytes = await get_minio_file(doc.file_url)
                    doc_entry["content_base64"] = base64.b64encode(
                        file_bytes
                    ).decode("utf-8")
                except Exception as exc:
                    logger.warning(
                        "risk_engine: could not retrieve MinIO file "
                        "doc_id=%s: %s",
                        doc.document_id,
                        exc,
                    )
                    doc_entry["content_base64"] = None

            documents.append(doc_entry)

    return {
        "user_info": user_info,
        "additional_info": additional_info_data,
        "documents": documents,
        "risk_flags": risk_flags,
        "llm_flags": llm_flags or [],
    }
