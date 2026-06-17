from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.assistant import (
    AssistantAnswer,
    DeniedAnswer,
    _EMPLOYEE_DENIAL,
    answer_question,
)
from app.services.rag_logistics import (
    GraphEdge,
    GraphNode,
    LogisticsAnswer,
    ProcurementGraph,
    ShipmentNotFoundError,
    classify_intent,
)
from app.services.rag_policy import MixedAnswer, PolicyAnswer

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_GOLDEN_PATH = _FIXTURES_DIR / "assistant_golden.json"


def _load_golden_cases() -> list[dict[str, Any]]:
    with open(_GOLDEN_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data["version"] == "1.0.0", f"Unsupported golden version: {data['version']}"
    return data["cases"]


GOLDEN_CASES = _load_golden_cases()
GOLDEN_IDS = [c["id"] for c in GOLDEN_CASES]

_RETRIEVED_AT = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def _mock_logistics_answer(tracking_code: str) -> LogisticsAnswer:
    return LogisticsAnswer(
        answer=f"Shipment {tracking_code} is currently in transit.",
        graph=ProcurementGraph(
            nodes=[
                GraphNode(id="s1", type="shipment", label=tracking_code),
                GraphNode(id="v1", type="vendor", label="Acme Corp"),
            ],
            edges=[GraphEdge(source="v1", target="s1", relationship="ships_via")],
            highlighted_path=["v1", "s1"],
            retrieved_at=_RETRIEVED_AT,
        ),
        follow_ups=[
            "Would you like the full shipment timeline?",
            "Do you want details on the products in this shipment?",
            "Should I check the related purchase order status?",
        ],
    )


def _mock_policy_answer() -> PolicyAnswer:
    return PolicyAnswer(
        answer="The policy states that items may be returned within 30 days.",
        citations=[
            {
                "source_title": "Returns Policy",
                "document_id": 1,
                "chunk_id": 10,
                "section": "Returns",
                "page_number": 2,
                "excerpt": "Items may be returned within 30 days.",
                "score": 0.92,
            }
        ],
    )


def _mock_mixed_answer(tracking_code: str) -> MixedAnswer:
    return MixedAnswer(
        answer=f"{tracking_code} is in transit. The return policy applies.",
        graph=ProcurementGraph(
            nodes=[
                GraphNode(id="s1", type="shipment", label=tracking_code),
                GraphNode(id="v1", type="vendor", label="Acme Corp"),
            ],
            edges=[GraphEdge(source="v1", target="s1", relationship="ships_via")],
            highlighted_path=["v1", "s1"],
            retrieved_at=_RETRIEVED_AT,
        ),
        citations=[
            {
                "source_title": "Returns Policy",
                "document_id": 1,
                "chunk_id": 10,
                "section": None,
                "page_number": None,
                "excerpt": "Returns within 30 days.",
                "score": 0.88,
            }
        ],
    )


def _mock_fallback_logistics_answer(tracking_code: str) -> LogisticsAnswer:
    return LogisticsAnswer(
        answer=f"Shipment {tracking_code} is currently 'in_transit'.",
        graph=ProcurementGraph(
            nodes=[
                GraphNode(id="s1", type="shipment", label=tracking_code),
                GraphNode(id="v1", type="vendor", label="Acme Corp"),
            ],
            edges=[GraphEdge(source="v1", target="s1", relationship="ships_via")],
            highlighted_path=["v1", "s1"],
            retrieved_at=_RETRIEVED_AT,
        ),
        follow_ups=[
            "Would you like the full shipment timeline?",
            "Do you want details on the products in this shipment?",
            "Should I check the related purchase order status?",
        ],
    )


def _mock_fallback_policy_answer() -> PolicyAnswer:
    return PolicyAnswer(
        answer="Returns Policy, Returns, p. 2: Items may be returned within 30 days.",
        citations=[
            {
                "source_title": "Returns Policy",
                "document_id": 1,
                "chunk_id": 10,
                "section": "Returns",
                "page_number": 2,
                "excerpt": "Items may be returned within 30 days.",
                "score": 0.92,
            }
        ],
    )


# ---------------------------------------------------------------------------
# Intent classification tests
# ---------------------------------------------------------------------------


class TestGoldenIntentClassification:

    @pytest.mark.parametrize("case", GOLDEN_CASES, ids=GOLDEN_IDS)
    def test_intent_matches(self, case: dict[str, Any]) -> None:
        routing = classify_intent(case["question"])
        assert routing.intent == case["expected_intent"], (
            f"[{case['id']}] Expected intent={case['expected_intent']!r}, "
            f"got {routing.intent!r}"
        )

    @pytest.mark.parametrize("case", GOLDEN_CASES, ids=GOLDEN_IDS)
    def test_tracking_codes_match(self, case: dict[str, Any]) -> None:
        routing = classify_intent(case["question"])
        assert routing.tracking_codes == case["expected_tracking_codes"], (
            f"[{case['id']}] Expected tracking_codes={case['expected_tracking_codes']!r}, "
            f"got {routing.tracking_codes!r}"
        )

    @pytest.mark.parametrize("case", GOLDEN_CASES, ids=GOLDEN_IDS)
    def test_po_numbers_match(self, case: dict[str, Any]) -> None:
        routing = classify_intent(case["question"])
        assert routing.purchase_order_numbers == case["expected_po_numbers"], (
            f"[{case['id']}] Expected po_numbers={case['expected_po_numbers']!r}, "
            f"got {routing.purchase_order_numbers!r}"
        )

    @pytest.mark.parametrize(
        "case",
        [c for c in GOLDEN_CASES if "expected_confidence_below" in c],
        ids=[c["id"] for c in GOLDEN_CASES if "expected_confidence_below" in c],
    )
    def test_low_confidence_for_ambiguous(self, case: dict[str, Any]) -> None:
        routing = classify_intent(case["question"])
        assert routing.confidence < case["expected_confidence_below"], (
            f"[{case['id']}] Expected confidence < {case['expected_confidence_below']}, "
            f"got {routing.confidence}"
        )


# ---------------------------------------------------------------------------
# Mock configuration
# ---------------------------------------------------------------------------


def _configure_mocks(
    case: dict[str, Any],
    mock_grounded_logistics: AsyncMock,
    mock_grounded_policy: AsyncMock,
    mock_grounded_mixed: AsyncMock,
    mock_lookup: AsyncMock,
) -> None:
    answer_type = case["expected_answer_type"]
    tracking_codes = case["expected_tracking_codes"]
    primary_code = tracking_codes[0] if tracking_codes else ""

    if answer_type == "ShipmentNotFoundError":
        mock_grounded_logistics.side_effect = ShipmentNotFoundError(
            f"no shipment found for tracking code {primary_code!r}"
        )
        return

    if answer_type == "LogisticsAnswer":
        if case.get("llm_behavior") == "error":
            mock_grounded_logistics.return_value = _mock_fallback_logistics_answer(
                primary_code
            )
        else:
            mock_grounded_logistics.return_value = _mock_logistics_answer(primary_code)

    if answer_type == "PolicyAnswer":
        if case.get("llm_behavior") == "error":
            mock_grounded_policy.return_value = _mock_fallback_policy_answer()
        else:
            mock_grounded_policy.return_value = _mock_policy_answer()

    if answer_type == "MixedAnswer":
        mock_grounded_logistics.return_value = _mock_logistics_answer(primary_code)
        mock_grounded_policy.return_value = _mock_policy_answer()
        mock_grounded_mixed.return_value = _mock_mixed_answer(primary_code)
        mock_lookup.return_value = MagicMock()


_ANSWER_TYPE_MAP: dict[str, type] = {
    "LogisticsAnswer": LogisticsAnswer,
    "PolicyAnswer": PolicyAnswer,
    "MixedAnswer": MixedAnswer,
    "DeniedAnswer": DeniedAnswer,
}


# ---------------------------------------------------------------------------
# Answer-level evaluation
# ---------------------------------------------------------------------------


class TestGoldenAnswerEvaluation:

    @pytest.mark.parametrize(
        "case",
        [c for c in GOLDEN_CASES if c["expected_answer_type"] != "ShipmentNotFoundError"],
        ids=[
            c["id"]
            for c in GOLDEN_CASES
            if c["expected_answer_type"] != "ShipmentNotFoundError"
        ],
    )
    @patch("app.services.assistant.lookup_procurement", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_mixed_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_policy_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_logistics_answer", new_callable=AsyncMock)
    async def test_answer_type(
        self,
        mock_logistics: AsyncMock,
        mock_policy: AsyncMock,
        mock_mixed: AsyncMock,
        mock_lookup: AsyncMock,
        case: dict[str, Any],
    ) -> None:
        _configure_mocks(case, mock_logistics, mock_policy, mock_mixed, mock_lookup)
        db = AsyncMock()
        llm = MagicMock()
        embeddings = MagicMock()

        result = await answer_question(
            user_role=case["role"],
            message=case["question"],
            db=db,
            llm=llm,
            embeddings=embeddings,
        )

        expected_type = _ANSWER_TYPE_MAP[case["expected_answer_type"]]
        assert isinstance(result, expected_type), (
            f"[{case['id']}] Expected {case['expected_answer_type']}, "
            f"got {type(result).__name__}"
        )

    @pytest.mark.parametrize(
        "case",
        [c for c in GOLDEN_CASES if c["expected_answer_type"] == "ShipmentNotFoundError"],
        ids=[
            c["id"]
            for c in GOLDEN_CASES
            if c["expected_answer_type"] == "ShipmentNotFoundError"
        ],
    )
    @patch("app.services.assistant.lookup_procurement", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_mixed_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_policy_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_logistics_answer", new_callable=AsyncMock)
    async def test_shipment_not_found_raises(
        self,
        mock_logistics: AsyncMock,
        mock_policy: AsyncMock,
        mock_mixed: AsyncMock,
        mock_lookup: AsyncMock,
        case: dict[str, Any],
    ) -> None:
        _configure_mocks(case, mock_logistics, mock_policy, mock_mixed, mock_lookup)
        db = AsyncMock()
        llm = MagicMock()
        embeddings = MagicMock()

        with pytest.raises(ShipmentNotFoundError):
            await answer_question(
                user_role=case["role"],
                message=case["question"],
                db=db,
                llm=llm,
                embeddings=embeddings,
            )


# ---------------------------------------------------------------------------
# Evidence-level fact checks
# ---------------------------------------------------------------------------


def _check_facts(result: AssistantAnswer, case: dict[str, Any]) -> list[str]:
    facts = case["expected_facts"]
    failures: list[str] = []

    if facts.get("answer_nonempty"):
        answer_text = getattr(result, "answer", getattr(result, "message", ""))
        if not answer_text:
            failures.append(f"[{case['id']}] answer is empty")

    if facts.get("graph_present"):
        graph = getattr(result, "graph", None)
        if graph is None:
            failures.append(f"[{case['id']}] graph missing but expected")
    elif "graph_present" in facts and not facts["graph_present"]:
        graph = getattr(result, "graph", None)
        if graph is not None:
            failures.append(f"[{case['id']}] graph present but not expected")

    if facts.get("citations_present"):
        citations = getattr(result, "citations", None)
        if not citations:
            failures.append(f"[{case['id']}] citations missing but expected")
    elif "citations_present" in facts and not facts["citations_present"]:
        citations = getattr(result, "citations", None)
        if citations:
            failures.append(f"[{case['id']}] citations present but not expected")

    if facts.get("follow_ups_present"):
        follow_ups = getattr(result, "follow_ups", None)
        if not follow_ups:
            failures.append(f"[{case['id']}] follow_ups missing but expected")
        min_count = facts.get("follow_ups_min_count")
        if min_count is not None and follow_ups and len(follow_ups) < min_count:
            failures.append(
                f"[{case['id']}] follow_ups count {len(follow_ups)} < {min_count}"
            )
    elif "follow_ups_present" in facts and not facts["follow_ups_present"]:
        follow_ups = getattr(result, "follow_ups", None)
        if follow_ups:
            failures.append(f"[{case['id']}] follow_ups present but not expected")

    if facts.get("denial_message_exact"):
        msg = getattr(result, "message", "")
        if msg != _EMPLOYEE_DENIAL:
            failures.append(
                f"[{case['id']}] denial message mismatch: {msg!r} != {_EMPLOYEE_DENIAL!r}"
            )

    return failures


def _check_graph_paths(result: AssistantAnswer, case: dict[str, Any]) -> list[str]:
    spec = case.get("expected_graph_paths")
    if spec is None:
        return []

    graph = getattr(result, "graph", None)
    if graph is None:
        return [f"[{case['id']}] graph is None, cannot check paths"]

    failures: list[str] = []

    node_count = len(graph.nodes) if hasattr(graph, "nodes") else 0
    if node_count < spec["min_nodes"]:
        failures.append(
            f"[{case['id']}] graph has {node_count} nodes, expected >= {spec['min_nodes']}"
        )

    actual_types = {n.type for n in graph.nodes} if hasattr(graph, "nodes") else set()
    for req_type in spec.get("required_node_types", []):
        if req_type not in actual_types:
            failures.append(f"[{case['id']}] missing node type {req_type!r}")

    actual_rels = {e.relationship for e in graph.edges} if hasattr(graph, "edges") else set()
    for req_rel in spec.get("required_relationships", []):
        if req_rel not in actual_rels:
            failures.append(f"[{case['id']}] missing relationship {req_rel!r}")

    return failures


class TestGoldenFactAccuracy:

    @patch("app.services.assistant.lookup_procurement", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_mixed_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_policy_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_logistics_answer", new_callable=AsyncMock)
    async def test_90_percent_fact_accuracy(
        self,
        mock_logistics: AsyncMock,
        mock_policy: AsyncMock,
        mock_mixed: AsyncMock,
        mock_lookup: AsyncMock,
    ) -> None:
        evaluable = [
            c
            for c in GOLDEN_CASES
            if c["expected_answer_type"] != "ShipmentNotFoundError"
        ]

        total_checks = 0
        passed_checks = 0
        all_failures: list[str] = []

        for case in evaluable:
            _configure_mocks(case, mock_logistics, mock_policy, mock_mixed, mock_lookup)
            db = AsyncMock()
            llm = MagicMock()
            embeddings = MagicMock()

            result = await answer_question(
                user_role=case["role"],
                message=case["question"],
                db=db,
                llm=llm,
                embeddings=embeddings,
            )

            fact_failures = _check_facts(result, case)
            path_failures = _check_graph_paths(result, case)

            fact_keys = [k for k in case["expected_facts"] if k != "follow_ups_min_count"]
            num_fact_checks = len(fact_keys)
            graph_spec = case.get("expected_graph_paths")
            num_path_checks = 0
            if graph_spec:
                num_path_checks = (
                    1
                    + len(graph_spec.get("required_node_types", []))
                    + len(graph_spec.get("required_relationships", []))
                )

            case_total = num_fact_checks + num_path_checks
            case_failures = len(fact_failures) + len(path_failures)
            case_passed = case_total - case_failures

            total_checks += case_total
            passed_checks += case_passed
            all_failures.extend(fact_failures)
            all_failures.extend(path_failures)

        accuracy = passed_checks / total_checks if total_checks > 0 else 0.0
        assert accuracy >= 0.90, (
            f"Fact+path accuracy {accuracy:.1%} < 90% threshold. "
            f"Failures ({len(all_failures)}/{total_checks}):\n"
            + "\n".join(all_failures)
        )


# ---------------------------------------------------------------------------
# Authorization and leakage checks (zero tolerance)
# ---------------------------------------------------------------------------


class TestGoldenAuthorization:

    @pytest.mark.parametrize(
        "case",
        [c for c in GOLDEN_CASES if c.get("authorization") and c["authorization"].get("must_deny")],
        ids=[
            c["id"]
            for c in GOLDEN_CASES
            if c.get("authorization") and c["authorization"].get("must_deny")
        ],
    )
    @patch("app.services.assistant.lookup_procurement", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_mixed_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_policy_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_logistics_answer", new_callable=AsyncMock)
    async def test_must_deny(
        self,
        mock_logistics: AsyncMock,
        mock_policy: AsyncMock,
        mock_mixed: AsyncMock,
        mock_lookup: AsyncMock,
        case: dict[str, Any],
    ) -> None:
        _configure_mocks(case, mock_logistics, mock_policy, mock_mixed, mock_lookup)
        db = AsyncMock()
        llm = MagicMock()
        embeddings = MagicMock()

        result = await answer_question(
            user_role=case["role"],
            message=case["question"],
            db=db,
            llm=llm,
            embeddings=embeddings,
        )

        assert isinstance(result, DeniedAnswer), (
            f"[{case['id']}] AUTHORIZATION FAILURE: expected DeniedAnswer, "
            f"got {type(result).__name__}"
        )
        assert result.message == _EMPLOYEE_DENIAL, (
            f"[{case['id']}] AUTHORIZATION FAILURE: denial message mismatch"
        )

    @pytest.mark.parametrize(
        "case",
        [c for c in GOLDEN_CASES if c.get("authorization") and c["authorization"].get("must_deny")],
        ids=[
            c["id"]
            for c in GOLDEN_CASES
            if c.get("authorization") and c["authorization"].get("must_deny")
        ],
    )
    @patch("app.services.assistant.lookup_procurement", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_mixed_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_policy_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_logistics_answer", new_callable=AsyncMock)
    async def test_no_leakage(
        self,
        mock_logistics: AsyncMock,
        mock_policy: AsyncMock,
        mock_mixed: AsyncMock,
        mock_lookup: AsyncMock,
        case: dict[str, Any],
    ) -> None:
        _configure_mocks(case, mock_logistics, mock_policy, mock_mixed, mock_lookup)
        db = AsyncMock()
        llm = MagicMock()
        embeddings = MagicMock()

        result = await answer_question(
            user_role=case["role"],
            message=case["question"],
            db=db,
            llm=llm,
            embeddings=embeddings,
        )

        assert isinstance(result, DeniedAnswer), (
            f"[{case['id']}] expected DeniedAnswer for leakage check"
        )

        leakage_fields = case["authorization"]["leakage_fields"]
        for field in leakage_fields:
            leaked_value = getattr(result, field, None)
            assert leaked_value is None, (
                f"[{case['id']}] LEAKAGE: DeniedAnswer exposes {field!r}={leaked_value!r}"
            )

    @pytest.mark.parametrize(
        "case",
        [
            c
            for c in GOLDEN_CASES
            if c.get("authorization") and not c["authorization"].get("must_deny")
        ],
        ids=[
            c["id"]
            for c in GOLDEN_CASES
            if c.get("authorization") and not c["authorization"].get("must_deny")
        ],
    )
    @patch("app.services.assistant.lookup_procurement", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_mixed_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_policy_answer", new_callable=AsyncMock)
    @patch("app.services.assistant.generate_grounded_logistics_answer", new_callable=AsyncMock)
    async def test_must_allow(
        self,
        mock_logistics: AsyncMock,
        mock_policy: AsyncMock,
        mock_mixed: AsyncMock,
        mock_lookup: AsyncMock,
        case: dict[str, Any],
    ) -> None:
        _configure_mocks(case, mock_logistics, mock_policy, mock_mixed, mock_lookup)
        db = AsyncMock()
        llm = MagicMock()
        embeddings = MagicMock()

        result = await answer_question(
            user_role=case["role"],
            message=case["question"],
            db=db,
            llm=llm,
            embeddings=embeddings,
        )

        assert not isinstance(result, DeniedAnswer), (
            f"[{case['id']}] AUTHORIZATION FAILURE: should be allowed but got DeniedAnswer"
        )
