"""
app/orchestration/onboarding_flow.py
=====================================
LangGraph-based onboarding state machine.

Integrates the 3-tier risk engine via :func:`app.services.risk_engine.process_onboarding`
to route applicants through REJECT / AUTO_APPROVE / MANUAL_REVIEW outcomes.
"""

import asyncio
import logging
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, START, END
from app.db.schemas import OnboardingState

logger = logging.getLogger(__name__)


# --- Node Functions ---


def intent_classification(state: OnboardingState) -> OnboardingState:
    logger.info(f"[{state.session_ulid}] Intent Classification Node")
    state.current_step = "intent_classification"
    return state


def conversational_node(state: OnboardingState) -> OnboardingState:
    logger.info(f"[{state.session_ulid}] Conversational Node")
    state.current_step = "conversational_node"
    return state


def request_document_upload(state: OnboardingState) -> OnboardingState:
    logger.info(f"[{state.session_ulid}] Request Document Upload Node")
    state.current_step = "request_document_upload"
    return state


def trigger_extraction(state: OnboardingState) -> OnboardingState:
    logger.info(f"[{state.session_ulid}] Document Extraction Node")
    state.current_step = "evaluate_risk"
    return state


def evaluate_risk(state: OnboardingState) -> OnboardingState:
    """
    Evaluate risk by calling the Risk Engine Orchestrator.

    Runs the async ``process_onboarding`` call synchronously within
    the LangGraph node (LangGraph nodes are synchronous by default).
    Updates ``state.risk_score``, ``state.status``, and stores the risk
    engine result in ``state.risk_result`` for downstream routing.
    """
    logger.info(
        f"[{state.session_ulid}] Evaluating risk via Risk Engine..."
    )

    from app.services.risk_engine import process_onboarding

    # Build minimal record dicts from the state for the risk agent.
    # In production, these would be enriched with DB-fetched data.
    user_record: Dict[str, Any] = {}
    telemetry_data: Dict[str, Any] = {
        "request_id": state.session_ulid,
    }
    additional_info_record: Dict[str, Any] = {}

    try:
        # Run async orchestrator from synchronous LangGraph node
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already inside an async context (e.g. FastAPI),
            # schedule as a coroutine in the existing loop.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run,
                    process_onboarding(
                        user_id=state.session_ulid or "",
                        user_record=user_record,
                        telemetry_data=telemetry_data,
                        additional_info_record=additional_info_record,
                    ),
                ).result()
        else:
            result = asyncio.run(
                process_onboarding(
                    user_id=state.session_ulid or "",
                    user_record=user_record,
                    telemetry_data=telemetry_data,
                    additional_info_record=additional_info_record,
                )
            )

        # Map risk engine action to OnboardingState fields
        action = result.get("action", "manual_review")
        if action == "reject":
            state.status = "rejected"
            state.risk_score = 100.0
        elif action == "approve":
            state.status = "approved"
            state.risk_score = 0.0
        else:
            state.status = "pending_review"
            state.risk_score = 50.0  # Indicates needs review

        logger.info(
            f"[{state.session_ulid}] Risk Engine result: "
            f"action={action} status={state.status}"
        )

    except Exception as exc:
        logger.error(
            f"[{state.session_ulid}] Risk Engine call failed: {exc}",
            exc_info=True,
        )
        # Fail-safe: escalate to manual review on error
        state.status = "pending_review"
        state.risk_score = 50.0

    return state


def auto_approve(state: OnboardingState) -> OnboardingState:
    logger.info(f"[{state.session_ulid}] Auto Approving...")
    state.status = "approved"
    return state


def reject_application(state: OnboardingState) -> OnboardingState:
    """Mark the application as rejected."""
    logger.info(f"[{state.session_ulid}] Application Rejected.")
    state.status = "rejected"
    return state


def human_review_escalation(state: OnboardingState) -> OnboardingState:
    logger.info(f"[{state.session_ulid}] Escalating to human review...")
    state.status = "pending_review"
    return state


# --- Conditional Edge Logic ---


def route_post_auth(
    state: OnboardingState,
) -> Literal["conversational_node", "request_document_upload", "trigger_extraction"]:
    """
    Routing based on Intent Capture block constraints:
    Rule 1: If intention is None, route to conversational_node to ask them.
    Rule 2: If intention is declared but docs aren't uploaded,
            route to request_document_upload.
    """
    intent = getattr(state, "intent", None)
    docs_uploaded = getattr(state, "documents_uploaded", False)

    if not intent:
        return "conversational_node"
    if intent and not docs_uploaded:
        return "request_document_upload"

    return "trigger_extraction"


def route_risk(
    state: OnboardingState,
) -> Literal["auto_approve", "reject_application", "human_review_escalation"]:
    """
    Route based on the risk engine's outcome (stored in state.status
    by the evaluate_risk node).

    Mapping:
        - status == "approved"        → auto_approve
        - status == "rejected"        → reject_application
        - status == "pending_review"  → human_review_escalation
    """
    if state.status == "approved":
        return "auto_approve"
    elif state.status == "rejected":
        return "reject_application"
    else:
        return "human_review_escalation"


# --- Graph Assembly ---

workflow = StateGraph(OnboardingState)

# Add nodes
workflow.add_node("conversational_node", conversational_node)
workflow.add_node("request_document_upload", request_document_upload)
workflow.add_node("intent_classification", intent_classification)
workflow.add_node("trigger_extraction", trigger_extraction)
workflow.add_node("evaluate_risk", evaluate_risk)

workflow.add_node("auto_approve", auto_approve)
workflow.add_node("reject_application", reject_application)
workflow.add_node("human_review_escalation", human_review_escalation)

# Add conditional edges out of START routing the logic
workflow.add_conditional_edges(
    START,
    route_post_auth,
    {
        "conversational_node": "conversational_node",
        "request_document_upload": "request_document_upload",
        "trigger_extraction": "trigger_extraction",
    },
)

# Connect intermediate blocks
workflow.add_edge("conversational_node", "intent_classification")
workflow.add_edge("intent_classification", END)  # Hand back to user for input
workflow.add_edge("request_document_upload", "trigger_extraction")
workflow.add_edge("trigger_extraction", "evaluate_risk")

# Add conditional edges from evaluate_risk (risk engine outcome)
workflow.add_conditional_edges(
    "evaluate_risk",
    route_risk,
    {
        "auto_approve": "auto_approve",
        "reject_application": "reject_application",
        "human_review_escalation": "human_review_escalation",
    },
)

workflow.add_edge("auto_approve", END)
workflow.add_edge("reject_application", END)
workflow.add_edge("human_review_escalation", END)

app_graph = workflow.compile()


# --- Execution ---


def run_agent(state: OnboardingState) -> OnboardingState:
    """
    Executes the LangGraph state machine based on the provided initial state.
    """
    # LangGraph returns a dictionary payload; we reconstruct it into our Pydantic model
    result_dict = app_graph.invoke(state)
    return result_dict
