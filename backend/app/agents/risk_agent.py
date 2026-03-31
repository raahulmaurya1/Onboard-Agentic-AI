"""
risk_agent.py – 3-Tier Risk Score Engine (Deterministic-Cognitive Pipeline)
=============================================================================
Tier 1  – The Guillotine        : Hard kills (instant REJECT)
Tier 2  – The Weighted Matrix   : Deterministic scored checks
Tier 3  – The Cognitive LLM     : Gemini AML reasoning (when score < 80)

Log sources (read-only, fully redacted before any use):
  • Gunicorn / Uvicorn access log  (JSON lines)
  • Celery worker log              (JSON lines)

Persistence is delegated to :mod:`app.db.vector_store` which owns the
``risk_evaluations`` table and pgvector pool.  This module contains ONLY
risk evaluation logic.

PRIVACY GUARANTEE
-----------------
- PII (Aadhaar numbers, PAN numbers, phone numbers, e-mail addresses) is
  redacted from log lines BEFORE parsing.
- Raw PII is NEVER written to this module's logs or to the DB.
- Only bucketed / normalised numeric features enter the vector store.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types
from rapidfuzz.distance import Levenshtein

from app.config import settings
from app.db.vector_store import store_risk_data

# ---------------------------------------------------------------------------
# Module-level logger — MUST NOT emit PII
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# IST offset
_IST = timedelta(hours=5, minutes=30)

# Burner e-mail domains (extend as needed)
_BURNER_DOMAINS: frozenset[str] = frozenset(
    {
        "temp-mail.org",
        "yopmail.com",
        "mailnator.com",
        "guerrillamail.com",
        "throwam.com",
        "trashmail.com",
        "10minutemail.com",
        "sharklasers.com",
    }
)

# ---------------------------------------------------------------------------
# 1.  REDACTION HELPERS
# ---------------------------------------------------------------------------

# Pre-compiled patterns for performance (order matters: 12-digit before 10-digit)
_REDACTION_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{12}\b"), "[REDACTED_AADHAAR]"),
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), "[REDACTED_PAN]"),
    (re.compile(r"\b\d{10}\b"), "[REDACTED_PHONE]"),
    (
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
        "[REDACTED_EMAIL]",
    ),
]


def redact_sensitive_data(text: str) -> str:
    """
    Strip Aadhaar numbers (12 digits), PAN numbers (XXXXX0000X format),
    10-digit phone numbers, and e-mail addresses from *text*.

    Returns the sanitised string.  Never raises.
    """
    for pattern, replacement in _REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# 2.  LOG PARSING (synchronous; wrapped in asyncio.to_thread by callers)
# ---------------------------------------------------------------------------

_MAX_LOG_LINES = 200  # Read only the tail to limit memory usage


def _read_log_tail(log_path: str, n_lines: int = _MAX_LOG_LINES) -> List[str]:
    """Read at most *n_lines* from the end of *log_path* safely."""
    path = Path(log_path)
    if not path.exists() or not path.is_file():
        logger.warning("Log file not found or not a file: %s", log_path)
        return []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            # Efficient tail – read all and slice (files are typically small)
            lines = fh.readlines()
        return lines[-n_lines:]
    except OSError as exc:
        logger.warning("Cannot read log file %s: %s", log_path, exc)
        return []


def parse_gunicorn_log(log_path: str) -> Dict[str, Any]:
    """
    Parse the last :data:`_MAX_LOG_LINES` lines of a Gunicorn / Uvicorn
    JSON-lines access log.

    Expected line schema (subset)::

        {
          "timestamp": "2026-01-01T12:00:00Z",
          "request_id": "...",
          "path": "/api/v1/...",
          "ip": "1.2.3.4",
          "user_agent": "...",
          "biometric_metadata": {
              "face_similarity": 92.5,
              "blink_count": 3,
              "liveness_confidence": 96.0
          }
        }

    Returns a flat dict of extracted fields, empty on failure.
    Sensitive data is redacted **before** JSON parsing.
    """
    extracted: Dict[str, Any] = {}
    lines = _read_log_tail(log_path)

    for raw_line in reversed(lines):  # Most recent first
        try:
            clean_line = redact_sensitive_data(raw_line.strip())
            if not clean_line:
                continue
            entry = json.loads(clean_line)

            # ── Timestamp → account_created_at_utc
            if "account_created_at_utc" not in extracted and entry.get("timestamp"):
                extracted.setdefault("account_created_at_utc", entry["timestamp"])

            # ── IP geolocation country (from log if present)
            if "ip_geolocation_country" not in extracted and entry.get(
                "ip_geolocation_country"
            ):
                extracted["ip_geolocation_country"] = entry["ip_geolocation_country"]

            # ── Biometric metadata block
            bio = entry.get("biometric_metadata") or {}
            if isinstance(bio, dict):
                if "face_similarity" not in extracted and "face_similarity" in bio:
                    extracted["face_similarity"] = float(bio["face_similarity"])
                if "blink_count" not in extracted and "blink_count" in bio:
                    extracted["blink_count"] = int(bio["blink_count"])
                if (
                    "liveness_confidence" not in extracted
                    and "liveness_confidence" in bio
                ):
                    extracted["liveness_confidence"] = float(
                        bio["liveness_confidence"]
                    )

            # ── Time-to-upload (ms)
            if "time_to_upload_ms" not in extracted and entry.get("time_to_upload_ms"):
                extracted["time_to_upload_ms"] = int(entry["time_to_upload_ms"])

        except (json.JSONDecodeError, ValueError, TypeError):
            # Non-JSON line or corrupt entry — skip silently
            continue

    return extracted


def parse_celery_log(log_path: str) -> Dict[str, Any]:
    """
    Parse the last :data:`_MAX_LOG_LINES` lines of a Celery worker log.

    Expected line schema (subset)::

        {
          "task_id": "...",
          "timestamp": "...",
          "kwargs": {...},
          "result": {
              "otp_retries": 1,
              "name_match": {"aadhaar_name": "...", "pan_name": "..."},
              "face_similarity": 95.0,
              "blink_count": 2,
              "liveness_confidence": 97.0
          }
        }

    Returns a flat dict of extracted fields.
    """
    extracted: Dict[str, Any] = {}
    lines = _read_log_tail(log_path)

    for raw_line in reversed(lines):
        try:
            clean_line = redact_sensitive_data(raw_line.strip())
            if not clean_line:
                continue
            entry = json.loads(clean_line)

            result: Dict[str, Any] = entry.get("result") or {}
            if not isinstance(result, dict):
                continue

            if "otp_retries" not in extracted and "otp_retries" in result:
                extracted["otp_retries"] = int(result["otp_retries"])

            # Biometrics from Celery result (lower priority than Gunicorn/telemetry)
            for field in ("face_similarity", "blink_count", "liveness_confidence"):
                if field not in extracted and field in result:
                    extracted[field] = result[field]

        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    return extracted


# ---------------------------------------------------------------------------
# 3.  ASYNC LOG WRAPPERS
# ---------------------------------------------------------------------------


async def read_gunicorn_log_async() -> Dict[str, Any]:
    """Non-blocking wrapper around :func:`parse_gunicorn_log`."""
    log_path = os.environ.get(
        "GUNICORN_LOG_PATH",
        getattr(settings, "GUNICORN_LOG_PATH", "/var/log/gunicorn/access.log"),
    )
    try:
        return await asyncio.to_thread(parse_gunicorn_log, log_path)
    except Exception as exc:  # pragma: no cover
        logger.warning("Gunicorn log read failed: %s", exc)
        return {}


async def read_celery_log_async() -> Dict[str, Any]:
    """Non-blocking wrapper around :func:`parse_celery_log`."""
    log_path = os.environ.get(
        "CELERY_LOG_PATH",
        getattr(settings, "CELERY_LOG_PATH", "/var/log/celery/worker.log"),
    )
    try:
        return await asyncio.to_thread(parse_celery_log, log_path)
    except Exception as exc:  # pragma: no cover
        logger.warning("Celery log read failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# 4.  TIER 1 – THE GUILLOTINE (Hard Kills)
# ---------------------------------------------------------------------------


def _run_tier1(merged: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Evaluate hard-kill conditions.

    Returns a REJECT result dict on any trigger, or *None* to continue.
    """
    flags: List[str] = []

    # ── Age check
    dob_raw: Optional[str] = merged.get("dob")
    age: Optional[int] = None
    if dob_raw:
        age = _parse_age(dob_raw)
        if age is not None and age < 18:
            flags.append("Underage Applicant")

    # ── Burner email check (domain only — no raw address stored)
    email_raw: Optional[str] = merged.get("email")
    if email_raw and isinstance(email_raw, str):
        domain = email_raw.split("@")[-1].lower().strip()
        if domain in _BURNER_DOMAINS:
            flags.append("Burner Email Domain")

    # ── Biometric hard kills
    face_sim: Optional[float] = _to_float(merged.get("face_similarity"))
    blink_count: Optional[int] = _to_int(merged.get("blink_count"))
    liveness_conf: Optional[float] = _to_float(merged.get("liveness_confidence"))

    if face_sim is not None and face_sim < 75.0:
        flags.append("Face match below 75% security threshold")

    if blink_count is not None and blink_count == 0:
        flags.append("Liveness Failed: 0 Blinks (Static Image/Mask)")

    if liveness_conf is not None and liveness_conf < 85.0:
        flags.append("Liveness confidence too low")

    if flags:
        logger.info("Tier 1 REJECT triggered. Flags: %s", flags)
        return {"category": "REJECT", "score": 100, "flags": flags}

    return None


# ---------------------------------------------------------------------------
# 5.  TIER 2 – THE WEIGHTED MATRIX
# ---------------------------------------------------------------------------


def _run_tier2(merged: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    Apply the weighted scoring matrix.

    Returns *(matrix_score, risk_flags)*.
    """
    matrix_score: int = 0
    risk_flags: List[str] = []

    # ── Network / Velocity / Temporal ──────────────────────────────────────
    time_to_upload: Optional[int] = _to_int(merged.get("time_to_upload_ms"))
    if time_to_upload is not None and time_to_upload < 2000:
        matrix_score += 40
        risk_flags.append("Non-Human Velocity/Bot")

    ip_country: Optional[str] = merged.get("ip_geolocation_country")
    phone_country: Optional[str] = merged.get("phone_country")
    if (
        ip_country
        and phone_country
        and ip_country.strip().upper() != phone_country.strip().upper()
    ):
        matrix_score += 30
        risk_flags.append("Geolocation Mismatch")

    account_created_raw: Optional[str] = merged.get("account_created_at_utc")
    if account_created_raw:
        hour_ist = _utc_str_to_ist_hour(account_created_raw)
        if hour_ist is not None and 1 <= hour_ist <= 5:
            matrix_score += 20
            risk_flags.append(
                "Suspicious Time of Day - late night/early morning operations"
            )

    # ── Auth Friction ───────────────────────────────────────────────────────
    otp_retries: Optional[int] = _to_int(merged.get("otp_retries"))
    if otp_retries is not None:
        if otp_retries > 4:
            matrix_score += 30
            risk_flags.append("Possible SIM Spoofing delay")
        elif otp_retries > 2:
            matrix_score += 15

    # ── Document Forensics – Name Match ─────────────────────────────────────
    aadhaar_name: Optional[str] = merged.get("aadhaar_name")
    pan_name: Optional[str] = merged.get("pan_name")
    if aadhaar_name and pan_name:
        dist = Levenshtein.distance(aadhaar_name.lower(), pan_name.lower())
        if dist <= 2:
            matrix_score += 15
        elif dist > 5 or _last_names_differ(aadhaar_name, pan_name):
            matrix_score += 50
            risk_flags.append("Name Mismatch between Aadhaar and PAN")

    # ── Advanced Biometrics ─────────────────────────────────────────────────
    face_sim: Optional[float] = _to_float(merged.get("face_similarity"))
    blink_count: Optional[int] = _to_int(merged.get("blink_count"))

    if face_sim is not None:
        if face_sim == 100.0:
            matrix_score += 100
            risk_flags.append("Replay/Injection Attack Detected")
        elif 75.0 <= face_sim <= 89.0:
            matrix_score += 10
            risk_flags.append("High Convenience Threshold used")

    if blink_count is not None and blink_count > 10:
        matrix_score += 30
        risk_flags.append("Abnormal Blink Rate - Deepfake/AI glitch")

    logger.info("Tier 2 matrix_score=%d flags=%s", matrix_score, risk_flags)
    return matrix_score, risk_flags


# ---------------------------------------------------------------------------
# 6.  TIER 3 – GEMINI AML LLM
# ---------------------------------------------------------------------------


async def _run_tier3_gemini(
    age: Optional[int],
    account_type: str,
    context_data: Dict[str, Any],
) -> Tuple[int, List[str]]:
    """
    Call Google Gemini asynchronously to get an AML risk delta.
    """
    # Build prompt based on account type
    if account_type == "sme_current":
        industry = context_data.get("industry_nic")
        turnover = context_data.get("expected_turnover")
        prompt = (
            "You are an AML analyst. Evaluate the following business context for money laundering risk.\n"
            f"Account Type: SME Current\n"
            f"Age of Applicant: {age}\n"
            f"Industry (NIC Code): {industry}\n"
            f"Expected Annual Turnover (INR): {turnover}\n"
            "Return JSON: {\"additional_risk\": int(0-40), \"aml_flags\": [\"...\"]}"
        )
    else:
        # Retail context: occupation, income, PEP status, FATCA etc.
        occ = context_data.get("occupation_type")
        inc = context_data.get("annual_income")
        pep = context_data.get("pep_status")
        prompt = (
            "You are an AML analyst. Evaluate the following personal context for money laundering risk.\n"
            f"Account Type: Retail Savings\n"
            f"Age: {age}\n"
            f"Occupation: {occ}, Annual Income: {inc}, PEP Status: {pep}\n"
            "Return JSON: {\"additional_risk\": int(0-40), \"aml_flags\": [\"...\"]}"
        )

    def _call_gemini() -> str:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        return response.text

    try:
        raw_text = await asyncio.wait_for(
            asyncio.to_thread(_call_gemini), timeout=15.0
        )
        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?\n?(.*?)```", r"\1", raw_text, flags=re.DOTALL).strip()
        parsed = json.loads(clean)
        additional_risk = int(parsed.get("additional_risk", 0))
        aml_flags: List[str] = parsed.get("aml_flags", [])
        logger.info("Tier 3 Gemini: additional_risk=%d flags=%s", additional_risk, aml_flags)
        return additional_risk, aml_flags
    except asyncio.TimeoutError:
        logger.warning("Tier 3 Gemini call timed out after 15 s — using fallback 0")
        return 0, []
    except Exception as exc:
        logger.warning("Tier 3 Gemini call failed: %s — using fallback 0", exc)
        return 0, []


# ---------------------------------------------------------------------------
# 7.  ASYNC STORAGE  –  delegated to app.db.vector_store
# ---------------------------------------------------------------------------
# store_risk_data is imported at the top of this module.
# Call it via asyncio.create_task() for fire-and-forget persistence.


# ---------------------------------------------------------------------------
# 8.  MAIN ENTRY POINT
# ---------------------------------------------------------------------------


async def evaluate_full_risk(
    user_record: Dict[str, Any],
    telemetry_data: Dict[str, Any],
    additional_info_record: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate the full 3-tier risk profile for an SME onboarding session.

    Parameters
    ----------
    user_record:
        Core identity fields — ``dob``, ``email``, ``phone_country``,
        ``aadhaar_name``, ``pan_name``, ``industry_nic``,
        ``expected_turnover``.  **Must NOT** contain raw Aadhaar / PAN IDs.
    telemetry_data:
        Real-time telemetry from the front-end SDK — ``time_to_upload_ms``,
        ``ip_geolocation_country``, ``account_created_at_utc``,
        ``otp_retries``, ``face_similarity``, ``blink_count``,
        ``liveness_confidence``.
    additional_info_record:
        Reserved for future use; merged last (lowest priority).

    Returns
    -------
    dict
        ``{"category": str, "score": int, "flags": list[str]}``
    """
    # ── 1. Read & redact logs concurrently ────────────────────────────────
    gunicorn_data, celery_data = await asyncio.gather(
        read_gunicorn_log_async(),
        read_celery_log_async(),
    )

    # ── 2. Merge  (priority: telemetry > gunicorn_log > celery_log > user_record > additional_info)
    merged: Dict[str, Any] = {
        **(additional_info_record or {}),
        **user_record,
        **celery_data,
        **gunicorn_data,
        **telemetry_data,   # highest priority — wins all conflicts
    }

    logger.info(
        "risk_agent: merged keys = %s",
        [k for k in merged if "id" not in k.lower() and "name" not in k.lower()],
    )

    # ── 3. Tier 1 – Hard Kills ────────────────────────────────────────────
    tier1_result = _run_tier1(merged)
    if tier1_result:
        asyncio.create_task(
            store_risk_data(
                request_id=telemetry_data.get("request_id"),
                merged=merged,
                age=_parse_age(merged.get("dob")),
                matrix_score=0,
                llm_additional_risk=0,
                total_score=tier1_result["score"],
                category=tier1_result["category"],
                risk_flags=tier1_result["flags"],
                llm_flags=[],
            )
        )
        return tier1_result

    # ── 4. Tier 2 – Weighted Matrix ───────────────────────────────────────
    matrix_score, risk_flags = _run_tier2(merged)

    # Clamp score before Tier 3 decision
    risk_score = matrix_score

    if risk_score >= 80:
        logger.info("Tier 2 score >= 80, returning REJECT without Tier 3.")
        final_category = "REJECT"
        asyncio.create_task(
            store_risk_data(
                request_id=telemetry_data.get("request_id"),
                merged=merged,
                age=_parse_age(merged.get("dob")),
                matrix_score=matrix_score,
                llm_additional_risk=0,
                total_score=risk_score,
                category=final_category,
                risk_flags=risk_flags,
                llm_flags=[],
            )
        )
        return {"category": final_category, "score": risk_score, "flags": risk_flags}

    # ── 5. Tier 3 – Gemini AML ────────────────────────────────────────────
    age = _parse_age(merged.get("dob"))
    account_type = merged.get("account_type", "retail_savings")
    
    llm_additional_risk = 0
    aml_flags = []

    # Digital Account Bypass: skip Tier 3 if digital_only
    if account_type == "digital_only":
        logger.info("Skipping Tier 3: Digital-Only accounts rely solely on Tier 1 and Tier 2.")
    else:
        # For SME, we still check for business context before calling Tier 3
        # For Retail, we call it with personal context
        has_context = True
        if account_type == "sme_current":
            has_context = bool(merged.get("industry_nic") or merged.get("expected_turnover"))
        
        if has_context:
            llm_additional_risk, aml_flags = await _run_tier3_gemini(
                age=age,
                account_type=account_type,
                context_data=merged
            )
        else:
            logger.info("Skipping Tier 3: No business context (Industry/Turnover) provided for SME.")
    risk_score += llm_additional_risk
    risk_flags.extend(aml_flags)

    # ── 6. Final Categorisation ───────────────────────────────────────────
    if risk_score >= 80:
        final_category = "REJECT"
    elif risk_score >= 40:
        final_category = "MANUAL_REVIEW"
    else:
        final_category = "AUTO_APPROVE"

    print(f"[risk_agent] Final Evaluation | Score: {risk_score} | Category: {final_category}")

    # ── 7. Async storage (fire-and-forget) ───────────────────────────────
    asyncio.create_task(
        store_risk_data(
            request_id=telemetry_data.get("request_id"),
            merged=merged,
            age=age,
            matrix_score=matrix_score,
            llm_additional_risk=llm_additional_risk,
            total_score=risk_score,
            category=final_category,
            risk_flags=risk_flags,
            llm_flags=aml_flags,
        )
    )

    return {"category": final_category, "score": risk_score, "flags": risk_flags}


# ---------------------------------------------------------------------------
# PRIVATE UTILITIES
# ---------------------------------------------------------------------------


def _parse_age(dob_raw: Optional[str]) -> Optional[int]:
    """
    Parse a DOB string (``DD/MM/YYYY``, ``YYYY-MM-DD``, or ``DD-MM-YYYY``)
    and return age in complete years.  Returns *None* on parse failure.
    """
    if not dob_raw:
        return None
    today = datetime.now(tz=timezone.utc).date()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            dob = datetime.strptime(dob_raw.strip(), fmt).date()
            age = (
                today.year
                - dob.year
                - ((today.month, today.day) < (dob.month, dob.day))
            )
            return age
        except ValueError:
            continue
    logger.debug("Could not parse DOB: %r", dob_raw)
    return None


def _utc_str_to_ist_hour(utc_str: str) -> Optional[int]:
    """
    Convert an ISO-8601 UTC timestamp string to an IST hour (0-23).
    Returns *None* on parse failure.
    """
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt_utc = datetime.strptime(utc_str.strip(), fmt)
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            dt_ist = dt_utc.astimezone(timezone(_IST))
            return dt_ist.hour
        except ValueError:
            continue
    return None


def _last_names_differ(name_a: str, name_b: str) -> bool:
    """Check whether the last tokens of two names differ (case-insensitive)."""
    a_parts = name_a.strip().split()
    b_parts = name_b.strip().split()
    if not a_parts or not b_parts:
        return False
    return a_parts[-1].lower() != b_parts[-1].lower()


def _to_float(value: Any) -> Optional[float]:
    """Safe coercion to float; returns *None* on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    """Safe coercion to int; returns *None* on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
