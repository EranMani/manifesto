"""Tests for backend/app/services/rag_logistics.py — shipment identifier lookup.

These tests run against a real PostgreSQL database (the docker-compose ``db``
service, resolved via DATABASE_URL inside the backend container). Each test
runs inside its own transaction that is rolled back on teardown.
"""

from __future__ import annotations

import datetime
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.shipment import Shipment
from app.models.shipment_event import ShipmentEvent
from app.models.user import User
from app.models.vendor import Vendor
from app.services.llm import ChatMessage, LLMError, LLMTimeoutError
from app.services.rag_logistics import (
    IntentRouting,
    LogisticsAnswer,
    ProcurementEvidence,
    ProcurementGraph,
    ShipmentEvidence,
    ShipmentNotFoundError,
    classify_intent,
    generate_grounded_logistics_answer,
    lookup_procurement,
    lookup_procurement_graph,
    lookup_shipment,
)

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto"
)

_NOW = datetime.datetime.now(datetime.timezone.utc)
_LATER = _NOW + datetime.timedelta(days=5)


@pytest_asyncio.fixture
async def session():
    """Yield an AsyncSession bound to a transaction that is rolled back after the test."""
    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session_factory = async_sessionmaker(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
            async with session_factory() as sess:
                yield sess
            await trans.rollback()
    finally:
        await engine.dispose()


async def _make_shipment(session: AsyncSession, **overrides) -> Shipment:
    vendor = Vendor(name="Test Vendor " + uuid.uuid4().hex[:8])
    session.add(vendor)
    await session.flush()

    defaults = dict(
        tracking_code="TRK-" + uuid.uuid4().hex[:12].upper(),
        vendor_id=vendor.id,
        origin="Shenzhen, CN",
        destination="Los Angeles, US",
        dispatched_at=_NOW,
        expected_arrival_at=_LATER,
    )
    defaults.update(overrides)
    shipment = Shipment(**defaults)
    session.add(shipment)
    await session.flush()
    return shipment


@pytest.mark.asyncio
async def test_identifier_lookup_resolves_known_shipment(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="delayed",
        delay_reason="Customs hold",
        actual_arrival_at=None,
    )

    evidence = await lookup_shipment(session, f"  {shipment.tracking_code.lower()}  ")

    assert isinstance(evidence, ShipmentEvidence)
    assert evidence.id == shipment.id
    assert evidence.tracking_code == shipment.tracking_code
    assert evidence.status == "delayed"
    assert evidence.origin == "Shenzhen, CN"
    assert evidence.destination == "Los Angeles, US"
    assert evidence.dispatched_at == shipment.dispatched_at
    assert evidence.expected_arrival_at == shipment.expected_arrival_at
    assert evidence.actual_arrival_at is None
    assert evidence.delay_reason == "Customs hold"


@pytest.mark.asyncio
async def test_identifier_lookup_unknown_identifier_raises(session: AsyncSession):
    with pytest.raises(ShipmentNotFoundError):
        await lookup_shipment(session, "TRK-DOES-NOT-EXIST")


@pytest.mark.asyncio
async def test_identifier_lookup_blank_identifier_raises(session: AsyncSession):
    with pytest.raises(ShipmentNotFoundError):
        await lookup_shipment(session, "   ")


@pytest.mark.asyncio
async def test_identifier_lookup_executes_no_write_statement(session: AsyncSession):
    shipment = await _make_shipment(session)
    session.expunge_all()

    await lookup_shipment(session, shipment.tracking_code)

    assert not session.new
    assert not session.dirty
    assert not session.deleted


async def _make_buyer(session: AsyncSession) -> User:
    buyer = User(
        name="Test Buyer",
        email=f"buyer-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        role="employee",
    )
    session.add(buyer)
    await session.flush()
    return buyer


async def _make_purchase_order(session: AsyncSession, vendor_id: str, buyer_id: str, **overrides) -> PurchaseOrder:
    defaults = dict(
        order_number="PO-" + uuid.uuid4().hex[:12],
        vendor_id=vendor_id,
        buyer_id=buyer_id,
        ordered_at=_NOW,
        requested_delivery_at=_LATER,
    )
    defaults.update(overrides)
    order = PurchaseOrder(**defaults)
    session.add(order)
    await session.flush()
    return order


async def _make_product(session: AsyncSession, shipment_id: str, **overrides) -> Product:
    defaults = dict(
        shipment_id=shipment_id,
        name="Widget",
        quantity=1,
    )
    defaults.update(overrides)
    product = Product(**defaults)
    session.add(product)
    await session.flush()
    return product


async def _make_event(session: AsyncSession, shipment_id: str, **overrides) -> ShipmentEvent:
    defaults = dict(
        shipment_id=shipment_id,
        event_type="dispatched",
        occurred_at=_NOW,
        location="Shenzhen, CN",
    )
    defaults.update(overrides)
    event = ShipmentEvent(**defaults)
    session.add(event)
    await session.flush()
    return event


@pytest.mark.asyncio
async def test_timeline_orders_events_by_occurred_at_then_id(session: AsyncSession):
    shipment = await _make_shipment(session)

    middle = await _make_event(
        session, shipment.id, event_type="departed", occurred_at=_NOW + datetime.timedelta(hours=1)
    )
    earliest = await _make_event(
        session, shipment.id, event_type="ordered", occurred_at=_NOW
    )
    latest = await _make_event(
        session, shipment.id, event_type="arrived_hub", occurred_at=_NOW + datetime.timedelta(hours=2)
    )

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert isinstance(evidence, ProcurementEvidence)
    assert [event.id for event in evidence.timeline] == [earliest.id, middle.id, latest.id]
    assert [event.event_type for event in evidence.timeline] == [
        "ordered",
        "departed",
        "arrived_hub",
    ]


@pytest.mark.asyncio
async def test_timeline_orders_simultaneous_events_by_id(session: AsyncSession):
    shipment = await _make_shipment(session)

    first = await _make_event(session, shipment.id, event_type="ordered", occurred_at=_NOW)
    second = await _make_event(session, shipment.id, event_type="dispatched", occurred_at=_NOW)

    evidence = await lookup_procurement(session, shipment.tracking_code)

    expected_order = sorted([first.id, second.id])
    assert [event.id for event in evidence.timeline] == expected_order


@pytest.mark.asyncio
async def test_timeline_delay_evidence_maps_to_latest_exception_event(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="delayed",
        delay_reason="Customs hold",
        actual_arrival_at=None,
    )

    await _make_event(
        session,
        shipment.id,
        event_type="delay_reported",
        occurred_at=_NOW + datetime.timedelta(hours=1),
        details="First delay notice",
    )
    latest_exception = await _make_event(
        session,
        shipment.id,
        event_type="delay_reported",
        occurred_at=_NOW + datetime.timedelta(hours=2),
        details="Customs hold confirmed",
    )
    await _make_event(
        session,
        shipment.id,
        event_type="customs_hold",
        occurred_at=_NOW + datetime.timedelta(hours=3),
    )

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.delay is not None
    assert evidence.delay.reason == "Customs hold"
    assert evidence.delay.exception_event is not None
    assert evidence.delay.exception_event.id == latest_exception.id
    assert evidence.delay.exception_event.details == "Customs hold confirmed"


@pytest.mark.asyncio
async def test_timeline_delay_evidence_absent_for_on_track_shipment(session: AsyncSession):
    shipment = await _make_shipment(session, status="in_transit")

    await _make_event(session, shipment.id, event_type="dispatched", occurred_at=_NOW)

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.delay is None


@pytest.mark.asyncio
async def test_timeline_delay_evidence_without_reason_is_not_invented(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="lost",
        delay_reason=None,
        actual_arrival_at=None,
    )

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.delay is None


@pytest.mark.asyncio
async def test_timeline_delay_evidence_without_supporting_event_has_no_exception_event(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="damaged",
        delay_reason="Container damaged in transit",
        actual_arrival_at=None,
    )

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.delay is not None
    assert evidence.delay.reason == "Container damaged in transit"
    assert evidence.delay.exception_event is None


@pytest.mark.asyncio
async def test_procurement_relationships_returns_buyer_order_vendor_and_products(session: AsyncSession):
    shipment = await _make_shipment(session)
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()

    product_b = await _make_product(session, shipment.id, name="Widget B", quantity=2, unit="box")
    product_a = await _make_product(session, shipment.id, name="Widget A", quantity=1, unit="crate")

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert isinstance(evidence, ProcurementEvidence)
    assert evidence.shipment.id == shipment.id
    assert evidence.purchase_order is not None
    assert evidence.purchase_order.id == order.id
    assert evidence.purchase_order.order_number == order.order_number
    assert evidence.buyer is not None
    assert evidence.buyer.id == buyer.id
    assert evidence.buyer.name == buyer.name
    assert evidence.vendor.id == shipment.vendor_id
    assert [p.id for p in evidence.products] == [product_a.id, product_b.id]


@pytest.mark.asyncio
async def test_procurement_relationships_missing_order_is_explicit(session: AsyncSession):
    shipment = await _make_shipment(session)

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.purchase_order is None
    assert evidence.buyer is None
    assert evidence.vendor.id == shipment.vendor_id
    assert evidence.products == []


@pytest.mark.asyncio
async def test_procurement_relationships_excludes_sensitive_user_fields(session: AsyncSession):
    shipment = await _make_shipment(session)
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()

    evidence = await lookup_procurement(session, shipment.tracking_code)

    buyer_fields = vars(evidence.buyer)
    assert "email" not in buyer_fields
    assert "password_hash" not in buyer_fields
    vendor_fields = vars(evidence.vendor)
    assert "email" not in vendor_fields
    assert "contact" not in vendor_fields


@pytest.mark.asyncio
async def test_graph_full_procurement_chain_has_expected_nodes_and_edges(session: AsyncSession):
    shipment = await _make_shipment(session)
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()

    product = await _make_product(session, shipment.id, name="Widget")
    event = await _make_event(session, shipment.id, event_type="dispatched", occurred_at=_NOW)

    graph = await lookup_procurement_graph(session, shipment.tracking_code)

    assert isinstance(graph, ProcurementGraph)
    node_ids = {node.id for node in graph.nodes}
    assert f"buyer:{buyer.id}" in node_ids
    assert f"purchase_order:{order.id}" in node_ids
    assert f"vendor:{shipment.vendor_id}" in node_ids
    assert f"shipment:{shipment.id}" in node_ids
    assert f"product:{product.id}" in node_ids
    assert f"event:{event.id}" in node_ids

    edge_tuples = {(edge.source, edge.target, edge.relationship) for edge in graph.edges}
    assert (f"buyer:{buyer.id}", f"purchase_order:{order.id}", "placed_order") in edge_tuples
    assert (f"purchase_order:{order.id}", f"vendor:{shipment.vendor_id}", "ordered_from") in edge_tuples
    assert (f"purchase_order:{order.id}", f"shipment:{shipment.id}", "fulfilled_by") in edge_tuples
    assert (f"vendor:{shipment.vendor_id}", f"shipment:{shipment.id}", "ships_via") in edge_tuples
    assert (f"shipment:{shipment.id}", f"product:{product.id}", "contains") in edge_tuples
    assert (f"shipment:{shipment.id}", f"event:{event.id}", "has_event") in edge_tuples


@pytest.mark.asyncio
async def test_graph_node_ids_are_stable_and_typed(session: AsyncSession):
    shipment = await _make_shipment(session)
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()
    await _make_product(session, shipment.id)

    graph = await lookup_procurement_graph(session, shipment.tracking_code)

    for node in graph.nodes:
        prefix, _, database_id = node.id.partition(":")
        assert prefix == node.type
        assert database_id
    assert {node.type for node in graph.nodes} >= {
        "buyer",
        "purchase_order",
        "vendor",
        "shipment",
        "product",
    }


@pytest.mark.asyncio
async def test_graph_no_orphan_edges(session: AsyncSession):
    shipment = await _make_shipment(session)
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()
    await _make_product(session, shipment.id)
    await _make_event(session, shipment.id)

    graph = await lookup_procurement_graph(session, shipment.tracking_code)

    node_ids = {node.id for node in graph.nodes}
    for edge in graph.edges:
        assert edge.source in node_ids
        assert edge.target in node_ids
    for highlighted_id in graph.highlighted_path:
        assert highlighted_id in node_ids


@pytest.mark.asyncio
async def test_graph_highlighted_path_ordered_buyer_to_event(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="delayed",
        delay_reason="Customs hold",
        actual_arrival_at=None,
    )
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()

    exception_event = await _make_event(
        session,
        shipment.id,
        event_type="delay_reported",
        occurred_at=_NOW + datetime.timedelta(hours=1),
        details="Customs hold confirmed",
    )

    graph = await lookup_procurement_graph(session, shipment.tracking_code)

    assert graph.highlighted_path == [
        f"buyer:{buyer.id}",
        f"purchase_order:{order.id}",
        f"shipment:{shipment.id}",
        f"event:{exception_event.id}",
    ]


@pytest.mark.asyncio
async def test_graph_highlighted_path_excludes_unrelated_products_and_events(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="delayed",
        delay_reason="Customs hold",
        actual_arrival_at=None,
    )
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()

    product_a = await _make_product(session, shipment.id, name="Widget A")
    product_b = await _make_product(session, shipment.id, name="Widget B")
    dispatch_event = await _make_event(
        session, shipment.id, event_type="dispatched", occurred_at=_NOW
    )
    exception_event = await _make_event(
        session,
        shipment.id,
        event_type="delay_reported",
        occurred_at=_NOW + datetime.timedelta(hours=1),
        details="Customs hold confirmed",
    )

    graph = await lookup_procurement_graph(session, shipment.tracking_code)

    assert graph.highlighted_path[-1] == f"event:{exception_event.id}"
    assert f"product:{product_a.id}" not in graph.highlighted_path
    assert f"product:{product_b.id}" not in graph.highlighted_path
    assert f"event:{dispatch_event.id}" not in graph.highlighted_path


@pytest.mark.asyncio
async def test_graph_retrieved_at_is_recent_utc(session: AsyncSession):
    shipment = await _make_shipment(session)

    before = datetime.datetime.now(datetime.timezone.utc)
    graph = await lookup_procurement_graph(session, shipment.tracking_code)
    after = datetime.datetime.now(datetime.timezone.utc)

    assert graph.retrieved_at.tzinfo is not None
    assert before <= graph.retrieved_at <= after


def test_intent_routing_explicit_shipment_id_selects_logistics():
    routing = classify_intent("What is the status of SHP-1234?")

    assert isinstance(routing, IntentRouting)
    assert routing.intent == "logistics"
    assert routing.confidence == 1.0
    assert routing.tracking_codes == ["SHP-1234"]
    assert routing.purchase_order_numbers == []


def test_intent_routing_explicit_purchase_order_id_selects_logistics():
    routing = classify_intent("Where is order PO-2026-001 right now?")

    assert routing.intent == "logistics"
    assert routing.confidence == 1.0
    assert routing.purchase_order_numbers == ["PO-2026-001"]
    assert routing.tracking_codes == []


def test_intent_routing_normalizes_lowercase_identifiers():
    routing = classify_intent("any update on shp-5678 or po-2026-099?")

    assert routing.tracking_codes == ["SHP-5678"]
    assert routing.purchase_order_numbers == ["PO-2026-099"]


def test_intent_routing_policy_terms_select_policy():
    routing = classify_intent("What is our return policy for damaged goods?")

    assert routing.intent == "policy"
    assert routing.confidence == 1.0
    assert routing.tracking_codes == []
    assert routing.purchase_order_numbers == []


def test_intent_routing_identifier_and_policy_terms_select_mixed():
    routing = classify_intent("Can I get a refund for shipment SHP-1234?")

    assert routing.intent == "mixed"
    assert routing.confidence == 1.0
    assert routing.tracking_codes == ["SHP-1234"]


def test_intent_routing_ambiguous_question_defaults_to_logistics_no_identifier():
    routing = classify_intent("Where is my shipment?")

    assert routing.intent == "logistics"
    assert routing.confidence < 1.0
    assert routing.tracking_codes == []
    assert routing.purchase_order_numbers == []


def test_intent_routing_does_not_invent_identifiers_from_unrelated_numbers():
    routing = classify_intent("I ordered 1234 units last week, any news?")

    assert routing.tracking_codes == []
    assert routing.purchase_order_numbers == []


def test_intent_routing_deduplicates_repeated_identifiers():
    routing = classify_intent("SHP-1234 and shp-1234 both refer to the same shipment.")

    assert routing.tracking_codes == ["SHP-1234"]


def test_intent_routing_browse_find_all_shipments():
    routing = classify_intent("Find all shipments")

    assert routing.intent == "logistics_browse"
    assert routing.confidence == 1.0
    assert routing.tracking_codes == []
    assert routing.purchase_order_numbers == []
    assert routing.status_filter is None


def test_intent_routing_browse_show_delayed_shipments():
    routing = classify_intent("Show delayed shipments")

    assert routing.intent == "logistics_browse"
    assert routing.confidence == 1.0
    assert routing.status_filter == "delayed"


def test_intent_routing_browse_how_many_pending():
    routing = classify_intent("How many shipments are pending?")

    assert routing.intent == "logistics_browse"
    assert routing.confidence == 1.0
    assert routing.status_filter == "pending"


def test_intent_routing_browse_extracts_delivered_status():
    routing = classify_intent("List all delivered orders")

    assert routing.intent == "logistics_browse"
    assert routing.status_filter == "delivered"


def test_intent_routing_browse_with_identifier_stays_logistics():
    routing = classify_intent("Show all shipments like SHP-1234")

    assert routing.intent == "logistics"
    assert routing.confidence == 1.0
    assert routing.tracking_codes == ["SHP-1234"]


def test_intent_routing_browse_with_policy_term_stays_policy():
    routing = classify_intent("Show all return policies for delayed shipments")

    assert routing.intent == "policy"
    assert routing.confidence == 1.0


def test_intent_routing_ambiguous_no_browse_no_identifier_stays_logistics():
    routing = classify_intent("Where is my shipment?")

    assert routing.intent == "logistics"
    assert routing.confidence == 0.5
    assert routing.tracking_codes == []


def test_intent_routing_existing_routes_have_null_status_filter():
    routing = classify_intent("What is the status of SHP-1234?")

    assert routing.intent == "logistics"
    assert routing.status_filter is None


class _FakeLLMService:
    """Records the prompt passed to ``chat()`` and yields a fixed answer."""

    def __init__(self, answer: str = "Generated answer.") -> None:
        self.answer = answer
        self.last_messages: list[ChatMessage] | None = None

    async def chat(self, messages, *, stream: bool = True):
        self.last_messages = list(messages)

        async def _generator():
            yield self.answer

        return _generator()


class _FailingLLMService:
    """Raises ``LLMError`` (or a subclass) whenever ``chat()`` is called."""

    def __init__(self, error: LLMError | None = None) -> None:
        self.error = error or LLMTimeoutError("simulated timeout")

    async def chat(self, messages, *, stream: bool = True):
        raise self.error


@pytest.mark.asyncio
async def test_grounded_answer_prompt_contains_only_evidence(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="delayed",
        delay_reason="Customs hold",
        actual_arrival_at=None,
    )
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()
    await _make_product(session, shipment.id, name="Widget A")

    llm = _FakeLLMService(answer="Your shipment is delayed due to a customs hold.")

    result = await generate_grounded_logistics_answer(
        session, llm, shipment.tracking_code, "What is the status of my shipment?"
    )

    assert isinstance(result, LogisticsAnswer)
    assert result.answer == "Your shipment is delayed due to a customs hold."

    assert llm.last_messages is not None
    prompt_text = "\n".join(message.content for message in llm.last_messages)

    # Evidence values appear in the prompt.
    assert shipment.tracking_code in prompt_text
    assert "delayed" in prompt_text
    assert "Customs hold" in prompt_text
    assert order.order_number in prompt_text
    assert buyer.name in prompt_text
    assert "Widget A" in prompt_text

    # No SQL or internal query language leaks into the prompt.
    assert "SELECT" not in prompt_text
    assert "FROM " not in prompt_text


@pytest.mark.asyncio
async def test_grounded_answer_success_keeps_graph_unchanged(session: AsyncSession):
    shipment = await _make_shipment(session)
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()
    product = await _make_product(session, shipment.id, name="Widget")

    expected_graph = await lookup_procurement_graph(session, shipment.tracking_code)

    llm = _FakeLLMService(answer="Everything is on track.")

    result = await generate_grounded_logistics_answer(
        session, llm, shipment.tracking_code, "Is my shipment on track?"
    )

    assert result.answer == "Everything is on track."
    assert {node.id for node in result.graph.nodes} == {node.id for node in expected_graph.nodes}
    assert {(e.source, e.target, e.relationship) for e in result.graph.edges} == {
        (e.source, e.target, e.relationship) for e in expected_graph.edges
    }
    assert result.graph.highlighted_path == expected_graph.highlighted_path
    assert f"product:{product.id}" in {node.id for node in result.graph.nodes}


@pytest.mark.asyncio
async def test_grounded_answer_provider_failure_returns_deterministic_fallback(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="delayed",
        delay_reason="Customs hold",
        actual_arrival_at=None,
    )
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()
    await _make_product(session, shipment.id, name="Widget A", quantity=3, unit="box")

    llm = _FailingLLMService()

    result = await generate_grounded_logistics_answer(
        session, llm, shipment.tracking_code, "What is the status of my shipment?"
    )

    assert isinstance(result, LogisticsAnswer)
    assert shipment.tracking_code in result.answer
    assert "delayed" in result.answer
    assert "Customs hold" in result.answer
    assert "Widget A" in result.answer
    assert order.order_number in result.answer
    assert buyer.name in result.answer

    # Graph evidence is still returned even on provider failure.
    assert isinstance(result.graph, ProcurementGraph)
    assert any(node.id == f"shipment:{shipment.id}" for node in result.graph.nodes)


@pytest.mark.asyncio
async def test_grounded_answer_unknown_shipment_raises_not_found(session: AsyncSession):
    llm = _FakeLLMService()

    with pytest.raises(ShipmentNotFoundError):
        await generate_grounded_logistics_answer(
            session, llm, "TRK-DOES-NOT-EXIST", "Where is my shipment?"
        )


@pytest.mark.asyncio
async def test_lookup_procurement_raises_when_vendor_missing():
    """Vendor lookup raises ShipmentNotFoundError (not NoResultFound) for a missing vendor row.

    FK constraints make this unreachable in a well-constrained DB, so tested via mocks.
    """
    from unittest.mock import AsyncMock, MagicMock, patch
    import app.services.rag_logistics as svc

    mock_shipment = MagicMock()
    mock_shipment.tracking_code = "TRK-ORPHAN"
    mock_shipment.vendor_id = "dead-vendor-id"
    mock_shipment.purchase_order_id = None
    mock_shipment.id = "s-orphan"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch.object(svc, "_load_shipment", new_callable=AsyncMock, return_value=mock_shipment):
        with pytest.raises(svc.ShipmentNotFoundError, match="dead-vendor-id"):
            await svc.lookup_procurement(mock_session, "TRK-ORPHAN")


@pytest.mark.asyncio
async def test_delay_evidence_selects_latest_event_by_id_on_occurred_at_tie(session: AsyncSession):
    """When two exception events share occurred_at, max() by id is the explicit tie-breaker."""
    shipment = await _make_shipment(
        session,
        status="delayed",
        delay_reason="Multiple alerts",
        actual_arrival_at=None,
    )
    shared_time = _NOW + datetime.timedelta(hours=1)
    first = await _make_event(
        session,
        shipment.id,
        event_type="delay_reported",
        occurred_at=shared_time,
        details="Alert A",
    )
    second = await _make_event(
        session,
        shipment.id,
        event_type="delay_reported",
        occurred_at=shared_time,
        details="Alert B",
    )

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.delay is not None
    expected_id = max(first.id, second.id)
    assert evidence.delay.exception_event is not None
    assert evidence.delay.exception_event.id == expected_id
