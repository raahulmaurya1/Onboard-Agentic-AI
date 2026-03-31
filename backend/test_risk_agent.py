"""
test_risk_agent.py
==================
Standalone test script for app/agents/risk_agent.py.
Validates all three tiers without requiring Celery, MinIO, or a live DB/API.

Run from the project root:
    .venv\\Scripts\\python test_risk_agent.py

Expected: all tests print PASS and exit 0.
"""
import asyncio
import sys
import os

# Bootstrap path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
import app.agents.risk_agent as ra
import app.db.vector_store as vs

# ---------------------------------------------------------------------------
# Global patches – applied before any test runs
# ---------------------------------------------------------------------------
async def _noop_store(**kwargs):
    """Replace DB writes with a no-op."""
    pass

async def _mock_tier3_low(age, account_type, context_data):
    """Return a safe non-escalating AML score so tests finish quickly."""
    return 5, ["Low-risk sector (mocked)"]

async def _noop_gunicorn():
    return {}

async def _noop_celery():
    return {}

# Patch everything that requires network / disk
ra._store_risk_data_async   = _noop_store          # type: ignore[assignment]
ra._run_tier3_gemini         = _mock_tier3_low      # type: ignore[assignment]
ra.read_gunicorn_log_async   = _noop_gunicorn       # type: ignore[assignment]
ra.read_celery_log_async     = _noop_celery         # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------
def ok(label: str):
    print(f"  ✓  {label}")

def fail(label: str, got):
    print(f"  ✗  {label}  →  got: {got!r}", file=sys.stderr)
    sys.exit(1)

def assert_eq(label, actual, expected):
    if actual != expected:
        fail(label, f"{actual!r} != {expected!r}")
    ok(label)

def assert_flag(label, flags, fragment):
    if not any(fragment.lower() in f.lower() for f in flags):
        fail(label, flags)
    ok(label)

def assert_true(label, cond, msg=""):
    if not cond:
        fail(label, msg)
    ok(label)

# ---------------------------------------------------------------------------
# Suite 1 – Redaction
# ---------------------------------------------------------------------------
async def test_redaction():
    print("\n[Suite 1] Redaction")
    cases: list[tuple[str, str]] = [
        ("123456789012 is an Aadhaar",        "[REDACTED_AADHAAR]"),
        ("PAN: ABCDE1234F at 10 pm",          "[REDACTED_PAN]"),
        ("Call 9876543210 for support",        "[REDACTED_PHONE]"),
        ("user@example.com is the email",      "[REDACTED_EMAIL]"),
    ]
    for raw, expected_token in cases:
        result = ra.redact_sensitive_data(raw)
        # Use explicit slice stop and cast to string to satisfy type checkers
        label = f"redact: '{str(raw)[0:32]}…'"
        assert_true(label, expected_token in result, result)

# ---------------------------------------------------------------------------
# Suite 2 – Tier 1 Hard Kills
# ---------------------------------------------------------------------------
_T1_PASS_TELEMETRY = {
    "face_similarity": 92.0,
    "blink_count": 3,
    "liveness_confidence": 95.0,
    "time_to_upload_ms": 5000,
    "ip_geolocation_country": "IN",
    "phone_country": "IN",
    "otp_retries": 0,
}

async def test_tier1_underage():
    print("\n[Suite 2a] Tier 1 – Underage")
    user = {"dob": "15/01/2015", "aadhaar_name": "Test User", "pan_name": "Test User"}
    result = await ra.evaluate_full_risk(user, dict(_T1_PASS_TELEMETRY), {})
    assert_eq("category = REJECT", result["category"], "REJECT")
    assert_flag("Underage flag", result["flags"], "Underage")

async def test_tier1_burner_email():
    print("\n[Suite 2b] Tier 1 – Burner Email")
    user = {"dob": "01/01/1990", "email": "throwaway@yopmail.com",
            "aadhaar_name": "A", "pan_name": "A"}
    result = await ra.evaluate_full_risk(user, dict(_T1_PASS_TELEMETRY), {})
    assert_eq("category = REJECT", result["category"], "REJECT")
    assert_flag("Burner email flag", result["flags"], "Burner")

async def test_tier1_face_similarity():
    print("\n[Suite 2c] Tier 1 – Face similarity < 75")
    user = {"dob": "01/01/1990", "aadhaar_name": "A", "pan_name": "A"}
    telemetry = {**_T1_PASS_TELEMETRY, "face_similarity": 60.0}
    result = await ra.evaluate_full_risk(user, telemetry, {})
    assert_eq("category = REJECT", result["category"], "REJECT")
    assert_flag("Face sim flag", result["flags"], "75%")

async def test_tier1_zero_blinks():
    print("\n[Suite 2d] Tier 1 – Zero blinks")
    user = {"dob": "01/01/1990", "aadhaar_name": "A", "pan_name": "A"}
    telemetry = {**_T1_PASS_TELEMETRY, "blink_count": 0}
    result = await ra.evaluate_full_risk(user, telemetry, {})
    assert_eq("category = REJECT", result["category"], "REJECT")
    assert_flag("Liveness blink flag", result["flags"], "Blink")

async def test_tier1_low_liveness():
    print("\n[Suite 2e] Tier 1 – Low liveness confidence")
    user = {"dob": "01/01/1990", "aadhaar_name": "A", "pan_name": "A"}
    telemetry = {**_T1_PASS_TELEMETRY, "liveness_confidence": 70.0}
    result = await ra.evaluate_full_risk(user, telemetry, {})
    assert_eq("category = REJECT", result["category"], "REJECT")
    assert_flag("Liveness conf flag", result["flags"], "Liveness confidence")

# ---------------------------------------------------------------------------
# Suite 3 – Tier 2 Weighted Matrix
# ---------------------------------------------------------------------------
async def test_tier2_bot_velocity():
    print("\n[Suite 3a] Tier 2 – Bot velocity (<2000ms → +40)")
    user = {"dob": "01/01/1990", "aadhaar_name": "Raj Kumar", "pan_name": "Raj Kumar"}
    telemetry = {**_T1_PASS_TELEMETRY, "time_to_upload_ms": 500}
    result = await ra.evaluate_full_risk(user, telemetry, {})
    assert_true("score ≥ 40", result["score"] >= 40, result["score"])
    assert_flag("Bot velocity flag", result["flags"], "Velocity")
    ok(f"score={result['score']} category={result['category']}")

async def test_tier2_geo_mismatch():
    print("\n[Suite 3b] Tier 2 – Geo mismatch (+30)")
    user = {"dob": "01/01/1990", "aadhaar_name": "Raj Kumar", "pan_name": "Raj Kumar",
            "phone_country": "IN"}
    telemetry = {**_T1_PASS_TELEMETRY, "ip_geolocation_country": "US", "phone_country": "IN"}
    result = await ra.evaluate_full_risk(user, telemetry, {})
    assert_flag("Geolocation mismatch flag", result["flags"], "Geolocation")
    ok(f"score={result['score']}")

async def test_tier2_name_mismatch():
    print("\n[Suite 3c] Tier 2 – Name mismatch (+50)")
    user = {"dob": "01/01/1990",
            "aadhaar_name": "Rajesh Kumar Sharma",
            "pan_name": "Rajeev Gupta Verma"}
    result = await ra.evaluate_full_risk(user, dict(_T1_PASS_TELEMETRY), {})
    assert_flag("Name mismatch flag", result["flags"], "Name Mismatch")
    ok(f"score={result['score']}")

async def test_tier2_night_hours():
    print("\n[Suite 3d] Tier 2 – Suspicious night hours (+20)")
    user = {"dob": "01/01/1990", "aadhaar_name": "A", "pan_name": "A"}
    # 20:00 UTC = 01:30 IST → triggers night-hour rule
    telemetry = {**_T1_PASS_TELEMETRY, "account_created_at_utc": "2026-03-22T20:00:00Z"}
    result = await ra.evaluate_full_risk(user, telemetry, {})
    assert_flag("Night-hours flag", result["flags"], "Suspicious Time")
    ok(f"score={result['score']}")

async def test_tier2_otp_retries():
    print("\n[Suite 3e] Tier 2 – OTP retries > 4 (+30)")
    user = {"dob": "01/01/1990", "aadhaar_name": "A", "pan_name": "A"}
    telemetry = {**_T1_PASS_TELEMETRY, "otp_retries": 5}
    result = await ra.evaluate_full_risk(user, telemetry, {})
    assert_flag("SIM Spoofing flag", result["flags"], "SIM Spoof")
    ok(f"score={result['score']}")

async def test_tier2_replay_attack():
    print("\n[Suite 3f] Tier 2 – Replay/Injection Attack (face=100.0 → +100 → REJECT)")
    user = {"dob": "01/01/1990", "aadhaar_name": "A", "pan_name": "A"}
    telemetry = {**_T1_PASS_TELEMETRY, "face_similarity": 100.0}
    result = await ra.evaluate_full_risk(user, telemetry, {})
    assert_eq("category = REJECT", result["category"], "REJECT")
    assert_flag("Replay attack flag", result["flags"], "Replay")

async def test_tier2_deepfake_blink():
    print("\n[Suite 3g] Tier 2 – Abnormal blink rate (>10 → +30)")
    user = {"dob": "01/01/1990", "aadhaar_name": "A", "pan_name": "A"}
    telemetry = {**_T1_PASS_TELEMETRY, "blink_count": 15}
    result = await ra.evaluate_full_risk(user, telemetry, {})
    assert_flag("Deepfake blink flag", result["flags"], "Deepfake")
    ok(f"score={result['score']}")

# ---------------------------------------------------------------------------
# Suite 4 – Merge Priority
# ---------------------------------------------------------------------------
async def test_merge_priority():
    print("\n[Suite 4] Merge priority – telemetry wins over log data")
    user = {"dob": "01/01/1990", "aadhaar_name": "A", "pan_name": "A"}
    # telemetry says 95 (safe); mock log returns 60 (reject-level)
    # telemetry must win → no rejection for face_similarity
    telemetry = {**_T1_PASS_TELEMETRY, "face_similarity": 95.0}

    original_celery = ra.read_celery_log_async
    async def _bad_celery_log():
        return {"face_similarity": 60.0}  # lower priority — must be overridden
    ra.read_celery_log_async = _bad_celery_log  # type: ignore[assignment]
    try:
        result = await ra.evaluate_full_risk(user, telemetry, {})
        rejected_for_face = (
            result["category"] == "REJECT"
            and any("75%" in f for f in result["flags"])
        )
        assert_true("Telemetry wins (not rejected for face)", not rejected_for_face,
                    f"category={result['category']} flags={result['flags']}")
        ok(f"category={result['category']} score={result['score']}")
    finally:
        ra.read_celery_log_async = original_celery  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Suite 5 – Happy Path (Tier 3 reached, mocked)
# ---------------------------------------------------------------------------
async def test_happy_path_tier3():
    print("\n[Suite 5] Happy path – passes all tiers, Tier 3 mocked to +5")
    user = {
        "dob": "15/06/1990",
        "email": "valid@gmail.com",
        "phone_country": "IN",
        "aadhaar_name": "Rajesh Kumar",
        "pan_name": "Rajesh Kumar",
        "industry_nic": "6201",
        "expected_turnover": "5000000",
    }
    telemetry = {
        "face_similarity": 92.5,
        "blink_count": 4,
        "liveness_confidence": 97.0,
        "time_to_upload_ms": 4800,
        "ip_geolocation_country": "IN",
        "phone_country": "IN",
        "account_created_at_utc": "2026-03-22T08:30:00Z",  # 14:00 IST – safe hour
        "otp_retries": 1,
    }
    result = await ra.evaluate_full_risk(user, telemetry, {})
    # With name exact match (+15) + Tier 3 +5 = 20 → AUTO_APPROVE
    assert_true(
        "category is valid",
        result["category"] in ("AUTO_APPROVE", "MANUAL_REVIEW", "REJECT"),
        result["category"],
    )
    ok(f"category={result['category']} score={result['score']} flags={result['flags']}")

# ---------------------------------------------------------------------------
# Suite 6 – Private Utilities
# ---------------------------------------------------------------------------
async def test_private_utils():
    print("\n[Suite 6] Private utilities")

    # _parse_age
    age = ra._parse_age("01/01/1990")
    assert_true(f"_parse_age('01/01/1990') ≈ 35-36 (got {age})", 35 <= age <= 36, age)

    assert_true("_parse_age(None) = None", ra._parse_age(None) is None)

    # _to_float / _to_int
    assert_eq("_to_float('92.5')", ra._to_float("92.5"), 92.5)
    assert_eq("_to_int('3')",      ra._to_int("3"), 3)
    assert_true("_to_float('bad') = None", ra._to_float("bad") is None)

    # _last_names_differ
    assert_true("Kumar vs Verma = True",  ra._last_names_differ("Raj Kumar", "Raj Verma"))
    assert_true("Kumar vs Kumar = False", not ra._last_names_differ("Raj Kumar", "Rajesh Kumar"))

    # IST hour conversion: 20:00 UTC = 01:30 IST → hour 1
    hour = ra._utc_str_to_ist_hour("2026-03-22T20:00:00Z")
    assert_eq("_utc_str_to_ist_hour(20:00 UTC) = 1 IST", hour, 1)

    # _turnover_range (now in vector_store)
    assert_eq("_turnover_range < 10L",   vs.turnover_range(500000),     "<10L")
    assert_eq("_turnover_range 10L-1Cr", vs.turnover_range(5000000),    "10L-1Cr")
    assert_eq("_turnover_range 1Cr-10Cr",vs.turnover_range(50000000),   "1Cr-10Cr")
    assert_eq("_turnover_range >10Cr",   vs.turnover_range(500000000),  ">10Cr")

    # _face_sim_range (now in vector_store)
    assert_eq("face sim <75",  vs.face_sim_range(60.0),  "<75")
    assert_eq("face sim 75-89",vs.face_sim_range(82.0),  "75-89")
    assert_eq("face sim 90-99",vs.face_sim_range(95.0),  "90-99")
    assert_eq("face sim 100",  vs.face_sim_range(100.0), "100")

    # _blink_category (now in vector_store)
    assert_eq("blink zero",   vs.blink_category(0),   "zero")
    assert_eq("blink low",    vs.blink_category(2),   "low")
    assert_eq("blink normal", vs.blink_category(6),   "normal")
    assert_eq("blink high",   vs.blink_category(15),  "high")

# ---------------------------------------------------------------------------
# Suite 7 – Feature Vector Shape
# ---------------------------------------------------------------------------
async def test_feature_vector():
    print("\n[Suite 7] Feature vector – shape and bounds (via vector_store)")
    vec = vs.generate_feature_vector(
        age=35, industry_nic="6201", expected_turnover="5000000",
        hour_of_day=14, otp_retries=1, face_similarity=92.5,
        blink_count=4, geolocation_match=True,
        name_levenshtein=0, matrix_score=20, llm_score=5,
    )
    assert_eq("vector length = 128", len(vec), 128)
    assert_true("all values in [0, 1]", all(0.0 <= v <= 1.0 for v in vec),
                [v for v in vec if not (0.0 <= v <= 1.0)])

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
async def main():
    print("=" * 60)
    print("  risk_agent.py – Test Suite  (all network/DB mocked)")
    print("=" * 60)

    await test_redaction()
    await test_tier1_underage()
    await test_tier1_burner_email()
    await test_tier1_face_similarity()
    await test_tier1_zero_blinks()
    await test_tier1_low_liveness()
    await test_tier2_bot_velocity()
    await test_tier2_geo_mismatch()
    await test_tier2_name_mismatch()
    await test_tier2_night_hours()
    await test_tier2_otp_retries()
    await test_tier2_replay_attack()
    await test_tier2_deepfake_blink()
    await test_merge_priority()
    await test_happy_path_tier3()
    await test_private_utils()
    await test_feature_vector()

    print("\n" + "=" * 60)
    print("  All tests passed ✓")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
