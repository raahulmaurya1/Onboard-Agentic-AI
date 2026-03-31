"""
app/db/vector_store.py
======================
pgvector persistence layer for anonymised risk evaluation data.

Responsibilities
----------------
- Own the ``risk_evaluations`` table DDL and index definitions.
- Manage a shared asyncpg connection pool (lazily initialised singleton).
- Expose :func:`store_risk_data` for fire-and-forget async writes.
- Expose :func:`generate_feature_vector` so callers can build the 128-dim
  feature vector without depending on this module's internal state.

PRIVACY GUARANTEE
-----------------
No raw PII (Aadhaar IDs, PAN IDs, names, emails, phone numbers) is accepted
by any function in this module.  All inputs are bucketed / normalised numbers.

Table: ``risk_evaluations``
---------------------------
Relational columns (for SQL queries / dashboards):
    id, request_id, age_bucket, industry_nic, turnover_range,
    ip_geolocation_country, hour_of_day, otp_retries,
    face_similarity_range, blink_rate_category

Score columns:
    matrix_score, llm_additional_risk, total_score, category

Flag columns:
    risk_flags TEXT[], llm_flags TEXT[]

Vector column (pgvector, IVFFLAT index):
    feature_vector vector(128)

Outcome tracking (for supervised ML):
    actual_outcome TEXT  -- NULL until ops team verifies
    outcome_verified_at TIMESTAMPTZ

Metadata:
    created_at TIMESTAMPTZ DEFAULT NOW()
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import asyncpg
from rapidfuzz.distance import Levenshtein

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TABLE DDL
# ---------------------------------------------------------------------------

_DDL = """
-- risk_evaluations: anonymised feature store for ML model training
-- and operational risk dashboards.  Contains NO raw PII.
CREATE TABLE IF NOT EXISTS risk_evaluations (
    -- ── Metadata ──────────────────────────────────────────────────────────
    id                     TEXT PRIMARY KEY,         -- UUID v4
    request_id             TEXT,                     -- correlates to on-boarding session

    -- ── Anonymised Relational Columns ─────────────────────────────────────
    age_bucket             TEXT,                     -- e.g. "30s" (decade)
    industry_nic           TEXT,                     -- NIC code string, not name
    turnover_range         TEXT,                     -- "<10L" | "10L-1Cr" | "1Cr-10Cr" | ">10Cr"
    ip_geolocation_country TEXT,                     -- ISO country code
    hour_of_day            INTEGER,                  -- 0-23, IST
    otp_retries            INTEGER,
    face_similarity_range  TEXT,                     -- "<75" | "75-89" | "90-99" | "100"
    blink_rate_category    TEXT,                     -- "zero" | "low" | "normal" | "high"

    -- ── Score Columns ─────────────────────────────────────────────────────
    matrix_score           INTEGER,
    llm_additional_risk    INTEGER,
    total_score            INTEGER,
    category               TEXT,                     -- "AUTO_APPROVE" | "MANUAL_REVIEW" | "REJECT"

    -- ── Flag Columns ──────────────────────────────────────────────────────
    risk_flags             TEXT[],                   -- deterministic tier flags
    llm_flags              TEXT[],                   -- Gemini AML flags

    -- ── pgvector Column (128-dim) ─────────────────────────────────────────
    feature_vector         vector(128),              -- normalised feature embedding for ML

    -- ── Outcome Tracking (supervised learning labels) ─────────────────────
    actual_outcome         TEXT,                     -- NULL until ops team verifies
    outcome_verified_at    TIMESTAMPTZ,

    -- ── Timestamps ────────────────────────────────────────────────────────
    created_at             TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS risk_evaluations_created_at_idx
    ON risk_evaluations (created_at);

CREATE INDEX IF NOT EXISTS risk_evaluations_category_idx
    ON risk_evaluations (category);

CREATE INDEX IF NOT EXISTS risk_evaluations_total_score_idx
    ON risk_evaluations (total_score);

-- IVFFLAT index for approximate nearest-neighbour similarity search
-- lists=100 suits up to ~1 M rows; tune as the dataset grows.
CREATE INDEX IF NOT EXISTS risk_evaluations_feature_vector_idx
    ON risk_evaluations
    USING ivfflat (feature_vector vector_cosine_ops)
    WITH (lists = 100);
"""

# ---------------------------------------------------------------------------
# CONNECTION POOL  (module-level lazily-initialised singleton)
# ---------------------------------------------------------------------------

_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()


def _build_dsn() -> str:
    """
    Derive a plain asyncpg DSN from environment / settings.

    Priority:
    1. Individual env vars: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    2. settings.DATABASE_URL (strips the SQLAlchemy "+asyncpg" driver prefix)
    """
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT")
    name = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")

    if all([host, port, name, user, password]):
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    # Fall back to DATABASE_URL, strip SQLAlchemy driver tag
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def get_pool() -> asyncpg.Pool:
    """
    Return (or lazily create) the shared asyncpg connection pool.

    On first call, automatically creates the ``risk_evaluations``
    table and indexes if they do not already exist.
    """
    global _pool
    if _pool is not None:
        return _pool

    async with _pool_lock:
        if _pool is not None:          # double-check after acquiring lock
            return _pool

        dsn = _build_dsn()
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)

        # Bootstrap schema on first connection
        async with _pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute(_DDL)

        logger.info("vector_store: risk_evaluations table ensured, pool ready")
    return _pool


# ---------------------------------------------------------------------------
# FEATURE VECTOR BUILDER
# ---------------------------------------------------------------------------

def generate_feature_vector(
    age: Optional[int],
    industry_nic: Optional[str],
    expected_turnover: Optional[Any],
    hour_of_day: Optional[int],
    otp_retries: Optional[int],
    face_similarity: Optional[float],
    blink_count: Optional[int],
    geolocation_match: bool,
    name_levenshtein: Optional[int],
    matrix_score: int,
    llm_score: int,
) -> List[float]:
    """
    Build a 128-dimensional normalised feature vector from anonymised inputs.

    Encoding layout (128 dims total):
    ┌─────────────────────────────────────────────────────────────────┐
    │  Dims  0-9   : age decade one-hot (10 buckets: 0s…90s+)        │
    │  Dims 10-29  : NIC code hash-bucket one-hot (20 buckets)        │
    │  Dims 30-39  : turnover million-INR bucket one-hot (10 buckets) │
    │  Dims 40-47  : normalised scalars (8 values)                    │
    │  Dims 48-127 : zero-pad                                         │
    └─────────────────────────────────────────────────────────────────┘

    All values are in [0.0, 1.0].  No raw PII enters this function.

    Parameters
    ----------
    age:
        Applicant age in complete years (derived from DOB, no DOB stored).
    industry_nic:
        NIC code string (not the industry name).
    expected_turnover:
        Numeric or string representation of annual turnover in INR.
    hour_of_day:
        IST hour (0-23) at which the session was created.
    otp_retries:
        Number of OTP retry attempts.
    face_similarity:
        Biometric face similarity score (0-100).
    blink_count:
        Number of blinks detected during liveness check.
    geolocation_match:
        True if IP country matches phone registration country.
    name_levenshtein:
        Levenshtein distance between Aadhaar name and PAN name.
    matrix_score:
        Tier 2 weighted matrix score.
    llm_score:
        Tier 3 Gemini AML additional risk (0-40).

    Returns
    -------
    list[float]
        Exactly 128 float values in [0.0, 1.0].
    """
    def _norm(value: Optional[float], max_val: float) -> float:
        if value is None:
            return 0.0
        return min(float(value) / max_val, 1.0)

    # ── Dims 0-9: age decade one-hot ────────────────────────────────────────
    age_buckets = [0.0] * 10
    if age is not None:
        bucket = min(int(age // 10), 9)   # 0-9→0, 10-19→1, …, 90+→9
        age_buckets[bucket] = 1.0

    # ── Dims 10-29: NIC code hash bucket one-hot ────────────────────────────
    nic_slots = [0.0] * 20
    if industry_nic:
        slot = hash(str(industry_nic)) % 20
        nic_slots[slot] = 1.0

    # ── Dims 30-39: turnover million-INR bucket one-hot ─────────────────────
    turnover_slots = [0.0] * 10
    try:
        tv = float(str(expected_turnover).replace(",", "").strip().split()[0])
        tb = min(int(tv // 1_000_000), 9)   # bucket by million INR
        turnover_slots[tb] = 1.0
    except (ValueError, TypeError, IndexError):
        pass

    # ── Dims 40-47: normalised scalars ───────────────────────────────────────
    scalars: List[float] = [
        _norm(hour_of_day,       23.0),
        _norm(otp_retries,       10.0),
        _norm(face_similarity,  100.0),
        _norm(blink_count,       30.0),
        1.0 if geolocation_match else 0.0,
        _norm(name_levenshtein,  20.0),
        _norm(matrix_score,     200.0),
        _norm(llm_score,         40.0),
    ]

    vector = age_buckets + nic_slots + turnover_slots + scalars   # 48 dims
    vector += [0.0] * (128 - len(vector))                          # pad to 128
    return vector[:128]


# ---------------------------------------------------------------------------
# BUCKETING HELPERS  (pure functions, no I/O)
# ---------------------------------------------------------------------------

def turnover_range(expected_turnover: Optional[Any]) -> str:
    """Bucket expected annual turnover into a readable range string."""
    try:
        tv = float(str(expected_turnover).replace(",", "").strip().split()[0])
        if tv < 1_000_000:
            return "<10L"
        elif tv < 10_000_000:
            return "10L-1Cr"
        elif tv < 100_000_000:
            return "1Cr-10Cr"
        return ">10Cr"
    except Exception:
        return "unknown"


def face_sim_range(face_similarity: Optional[float]) -> str:
    """Bucket face similarity into a readable range string."""
    if face_similarity is None:
        return "unknown"
    if face_similarity < 75:
        return "<75"
    elif face_similarity <= 89:
        return "75-89"
    elif face_similarity < 100:
        return "90-99"
    return "100"


def blink_category(blink_count: Optional[int]) -> str:
    """Categorise blink count into a risk-meaningful label."""
    if blink_count is None:
        return "unknown"
    if blink_count == 0:
        return "zero"
    elif blink_count <= 4:
        return "low"
    elif blink_count <= 10:
        return "normal"
    return "high"


# ---------------------------------------------------------------------------
# MAIN WRITE FUNCTION
# ---------------------------------------------------------------------------

async def store_risk_data(
    *,
    request_id: Optional[str],
    merged: Dict[str, Any],
    age: Optional[int],
    matrix_score: int,
    llm_additional_risk: int,
    total_score: int,
    category: str,
    risk_flags: List[str],
    llm_flags: List[str],
) -> None:
    """
    Persist an anonymised risk evaluation row to ``risk_evaluations``.

    Designed to be called via ``asyncio.create_task()`` — errors are logged
    but never propagated so the main onboarding flow is never blocked.

    Parameters
    ----------
    request_id:
        Optional correlation ID from the request (e.g. session ULID).
    merged:
        The merged data dict produced by ``evaluate_full_risk``.
        Only non-PII numeric/enumerated fields are extracted from it.
    age:
        Pre-computed applicant age (integer years).
    matrix_score:
        Tier 2 weighted matrix score.
    llm_additional_risk:
        Tier 3 Gemini AML additional risk score.
    total_score:
        Final combined risk score.
    category:
        Final category string: "AUTO_APPROVE", "MANUAL_REVIEW", or "REJECT".
    risk_flags:
        List of deterministic flag strings from Tiers 1 & 2.
    llm_flags:
        List of AML flag strings from Tier 3 Gemini.
    """
    try:
        pool = await get_pool()

        # ── Extract anonymised numeric features from merged ─────────────────
        face_similarity = _safe_float(merged.get("face_similarity"))
        blink_count     = _safe_int(merged.get("blink_count"))
        otp_retries     = _safe_int(merged.get("otp_retries"))
        industry_nic    = merged.get("industry_nic")
        expected_turnover = merged.get("expected_turnover")

        hour_of_day: Optional[int] = None
        account_created_raw = merged.get("account_created_at_utc")
        if account_created_raw:
            hour_of_day = _utc_str_to_ist_hour(account_created_raw)

        ip_country    = merged.get("ip_geolocation_country")
        phone_country = merged.get("phone_country")
        geo_match = bool(
            ip_country
            and phone_country
            and ip_country.strip().upper() == phone_country.strip().upper()
        )

        # Name Levenshtein (uses only anonymised string, no PII stored)
        aadhaar_name = merged.get("aadhaar_name")
        pan_name     = merged.get("pan_name")
        name_lev: Optional[int] = None
        if aadhaar_name and pan_name:
            name_lev = Levenshtein.distance(aadhaar_name.lower(), pan_name.lower())

        # Age bucket label (e.g. "30s")
        age_bucket = f"{(age // 10) * 10}s" if age is not None else "unknown"

        # Build 128-dim feature vector
        feature_vector = generate_feature_vector(
            age=age,
            industry_nic=industry_nic,
            expected_turnover=expected_turnover,
            hour_of_day=hour_of_day,
            otp_retries=otp_retries,
            face_similarity=face_similarity,
            blink_count=blink_count,
            geolocation_match=geo_match,
            name_levenshtein=name_lev,
            matrix_score=matrix_score,
            llm_score=llm_additional_risk,
        )

        row_id = str(uuid.uuid4())

        # asyncpg has no built-in pgvector codec, so serialise the list to
        # the pgvector text format:  '[f0,f1,...,f127]'
        vector_str = "[" + ",".join(f"{v:.6f}" for v in feature_vector) + "]"

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO risk_evaluations (
                    id, request_id,
                    age_bucket, industry_nic, turnover_range,
                    ip_geolocation_country, hour_of_day, otp_retries,
                    face_similarity_range, blink_rate_category,
                    matrix_score, llm_additional_risk, total_score, category,
                    risk_flags, llm_flags,
                    feature_vector
                ) VALUES (
                    $1, $2,
                    $3, $4, $5,
                    $6, $7, $8,
                    $9, $10,
                    $11, $12, $13, $14,
                    $15, $16,
                    $17::vector
                )
                """,
                row_id,
                request_id,
                age_bucket,
                str(industry_nic) if industry_nic else None,
                turnover_range(expected_turnover),
                ip_country,
                hour_of_day,
                otp_retries,
                face_sim_range(face_similarity),
                blink_category(blink_count),
                matrix_score,
                llm_additional_risk,
                total_score,
                category,
                risk_flags,
                llm_flags,
                vector_str,
            )

        logger.info(
            "vector_store: row stored id=%s category=%s total_score=%d",
            row_id, category, total_score,
        )

    except Exception as exc:
        logger.error(
            "vector_store: failed to store risk evaluation: %s", exc, exc_info=True
        )


async def get_risk_flags_for_request(request_id: str) -> Dict[str, List[str]]:
    """
    Retrieve deterministic and LLM risk flags for a specific request.
    
    Parameters
    ----------
    request_id:
        The session ULID (user_id) passed during store_risk_data.
    
    Returns
    -------
    dict
        ``{"risk_flags": [...], "llm_flags": [...]}``
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT risk_flags, llm_flags FROM risk_evaluations WHERE request_id = $1 ORDER BY created_at DESC LIMIT 1",
                request_id
            )
            
            if not row:
                return {"risk_flags": [], "llm_flags": []}
                
            return {
                "risk_flags": list(row.get("risk_flags") or []),
                "llm_flags": list(row.get("llm_flags") or []),
            }
            
    except Exception as exc:
        logger.error(
            "vector_store: failed to retrieve risk flags for %s: %s", request_id, exc
        )
        return {"risk_flags": [], "llm_flags": []}


# ---------------------------------------------------------------------------
# PRIVATE UTILITY FUNCTIONS  (used only within this module)
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _utc_str_to_ist_hour(utc_str: str) -> Optional[int]:
    """Convert an ISO-8601 UTC timestamp to IST hour (0-23)."""
    from datetime import datetime, timezone, timedelta
    _IST = timedelta(hours=5, minutes=30)
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(utc_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone(_IST)).hour
        except ValueError:
            continue
    return None
