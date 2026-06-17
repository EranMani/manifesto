import datetime
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.models.shipment_event import ShipmentEvent, ShipmentEventType
from app.models.user import User
from app.models.vendor import Vendor

if TYPE_CHECKING:
    from app.services.llm import ChatMessage, LLMService

# Statuses for which a delay/exception explanation is expected.
EXCEPTION_STATUSES: frozenset[ShipmentStatus] = frozenset(
    {"delayed", "damaged", "partial", "cancelled", "returned", "lost"}
)

# Event types that can support a delay/exception explanation, ordered by
# nothing in particular here — selection picks the latest by (occurred_at, id).
EXCEPTION_EVENT_TYPES: frozenset[ShipmentEventType] = frozenset(
    {"delay_reported", "damaged", "partial_delivery", "cancelled", "returned", "lost"}
)


class ShipmentNotFoundError(Exception):
    """Raised when no shipment matches the normalized tracking code."""


@dataclass(frozen=True)
class ShipmentEvidence:
    id: str
    tracking_code: str
    status: ShipmentStatus
    origin: str
    destination: str
    dispatched_at: datetime.datetime
    expected_arrival_at: datetime.datetime
    actual_arrival_at: datetime.datetime | None
    delay_reason: str | None


@dataclass(frozen=True)
class VendorEvidence:
    id: str
    name: str
    country: str | None


@dataclass(frozen=True)
class BuyerEvidence:
    id: str
    name: str


@dataclass(frozen=True)
class PurchaseOrderEvidence:
    id: str
    order_number: str
    status: PurchaseOrderStatus
    ordered_at: datetime.datetime
    requested_delivery_at: datetime.datetime


@dataclass(frozen=True)
class ProductEvidence:
    id: str
    name: str
    description: str | None
    quantity: int
    unit: str | None


@dataclass(frozen=True)
class ShipmentEventEvidence:
    id: str
    event_type: ShipmentEventType
    occurred_at: datetime.datetime
    location: str
    details: str | None


@dataclass(frozen=True)
class DelayEvidence:
    reason: str
    exception_event: ShipmentEventEvidence | None


@dataclass(frozen=True)
class ProcurementEvidence:
    shipment: ShipmentEvidence
    purchase_order: PurchaseOrderEvidence | None
    buyer: BuyerEvidence | None
    vendor: VendorEvidence
    products: list[ProductEvidence]
    timeline: list[ShipmentEventEvidence]
    delay: DelayEvidence | None


# Stable node types for the logistics evidence graph.
GraphNodeType = Literal[
    "buyer", "purchase_order", "vendor", "shipment", "product", "event"
]

# Allowlisted edge relationships between node types.
GraphRelationship = Literal[
    "placed_order",
    "ordered_from",
    "fulfilled_by",
    "ships_via",
    "contains",
    "has_event",
]


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: GraphNodeType
    label: str


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    relationship: GraphRelationship


@dataclass(frozen=True)
class ProcurementGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    highlighted_path: list[str]
    retrieved_at: datetime.datetime


def _shipment_evidence(shipment: Shipment) -> ShipmentEvidence:
    return ShipmentEvidence(
        id=shipment.id,
        tracking_code=shipment.tracking_code,
        status=shipment.status,
        origin=shipment.origin,
        destination=shipment.destination,
        dispatched_at=shipment.dispatched_at,
        expected_arrival_at=shipment.expected_arrival_at,
        actual_arrival_at=shipment.actual_arrival_at,
        delay_reason=shipment.delay_reason,
    )


async def _load_shipment(db: AsyncSession, tracking_code: str) -> Shipment:
    normalized = tracking_code.strip().upper()
    if not normalized:
        raise ShipmentNotFoundError("tracking code is blank")

    result = await db.execute(
        select(Shipment).where(Shipment.tracking_code == normalized)
    )
    shipment = result.scalar_one_or_none()
    if shipment is None:
        raise ShipmentNotFoundError(f"no shipment found for tracking code {normalized!r}")

    return shipment


def _shipment_event_evidence(event: ShipmentEvent) -> ShipmentEventEvidence:
    return ShipmentEventEvidence(
        id=event.id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        location=event.location,
        details=event.details,
    )


async def _load_timeline(db: AsyncSession, shipment_id: str) -> list[ShipmentEventEvidence]:
    events = (
        await db.execute(
            select(ShipmentEvent)
            .where(ShipmentEvent.shipment_id == shipment_id)
            .order_by(ShipmentEvent.occurred_at, ShipmentEvent.id)
        )
    ).scalars().all()
    return [_shipment_event_evidence(event) for event in events]


def _delay_evidence(
    shipment: Shipment, timeline: list[ShipmentEventEvidence]
) -> DelayEvidence | None:
    if shipment.status not in EXCEPTION_STATUSES:
        return None
    if not shipment.delay_reason:
        return None

    matching = [e for e in timeline if e.event_type in EXCEPTION_EVENT_TYPES]
    exception_event = (
        max(matching, key=lambda e: (e.occurred_at, e.id)) if matching else None
    )

    return DelayEvidence(reason=shipment.delay_reason, exception_event=exception_event)


async def lookup_shipment(db: AsyncSession, tracking_code: str) -> ShipmentEvidence:
    shipment = await _load_shipment(db, tracking_code)
    return _shipment_evidence(shipment)


async def lookup_procurement(db: AsyncSession, tracking_code: str) -> ProcurementEvidence:
    shipment = await _load_shipment(db, tracking_code)

    vendor = (
        await db.execute(select(Vendor).where(Vendor.id == shipment.vendor_id))
    ).scalar_one_or_none()
    if vendor is None:
        raise ShipmentNotFoundError(
            f"vendor {shipment.vendor_id!r} for shipment {shipment.tracking_code!r} not found"
        )

    purchase_order_evidence: PurchaseOrderEvidence | None = None
    buyer_evidence: BuyerEvidence | None = None
    if shipment.purchase_order_id is not None:
        purchase_order = (
            await db.execute(
                select(PurchaseOrder).where(PurchaseOrder.id == shipment.purchase_order_id)
            )
        ).scalar_one_or_none()
        if purchase_order is not None:
            purchase_order_evidence = PurchaseOrderEvidence(
                id=purchase_order.id,
                order_number=purchase_order.order_number,
                status=purchase_order.status,
                ordered_at=purchase_order.ordered_at,
                requested_delivery_at=purchase_order.requested_delivery_at,
            )
            buyer = (
                await db.execute(select(User).where(User.id == purchase_order.buyer_id))
            ).scalar_one_or_none()
            if buyer is not None:
                buyer_evidence = BuyerEvidence(id=buyer.id, name=buyer.name)

    products = (
        await db.execute(
            select(Product)
            .where(Product.shipment_id == shipment.id)
            .order_by(Product.name, Product.id)
        )
    ).scalars().all()

    timeline = await _load_timeline(db, shipment.id)

    return ProcurementEvidence(
        shipment=_shipment_evidence(shipment),
        purchase_order=purchase_order_evidence,
        buyer=buyer_evidence,
        vendor=VendorEvidence(id=vendor.id, name=vendor.name, country=vendor.country),
        products=[
            ProductEvidence(
                id=product.id,
                name=product.name,
                description=product.description,
                quantity=product.quantity,
                unit=product.unit,
            )
            for product in products
        ],
        timeline=timeline,
        delay=_delay_evidence(shipment, timeline),
    )


def _project_procurement_graph(evidence: ProcurementEvidence) -> ProcurementGraph:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    highlighted_path: list[str] = []

    shipment_node_id = f"shipment:{evidence.shipment.id}"
    vendor_node_id = f"vendor:{evidence.vendor.id}"

    buyer_node_id: str | None = None
    order_node_id: str | None = None

    if evidence.buyer is not None:
        buyer_node_id = f"buyer:{evidence.buyer.id}"
        nodes.append(GraphNode(id=buyer_node_id, type="buyer", label=evidence.buyer.name))
        highlighted_path.append(buyer_node_id)

    if evidence.purchase_order is not None:
        order_node_id = f"purchase_order:{evidence.purchase_order.id}"
        nodes.append(
            GraphNode(
                id=order_node_id,
                type="purchase_order",
                label=evidence.purchase_order.order_number,
            )
        )
        if buyer_node_id is not None:
            edges.append(
                GraphEdge(
                    source=buyer_node_id, target=order_node_id, relationship="placed_order"
                )
            )
            highlighted_path.append(order_node_id)

    nodes.append(GraphNode(id=vendor_node_id, type="vendor", label=evidence.vendor.name))
    if order_node_id is not None:
        edges.append(
            GraphEdge(
                source=order_node_id, target=vendor_node_id, relationship="ordered_from"
            )
        )

    nodes.append(
        GraphNode(
            id=shipment_node_id, type="shipment", label=evidence.shipment.tracking_code
        )
    )
    if order_node_id is not None:
        edges.append(
            GraphEdge(
                source=order_node_id, target=shipment_node_id, relationship="fulfilled_by"
            )
        )
    edges.append(
        GraphEdge(source=vendor_node_id, target=shipment_node_id, relationship="ships_via")
    )

    highlighted_path.append(shipment_node_id)

    for product in evidence.products:
        product_node_id = f"product:{product.id}"
        nodes.append(GraphNode(id=product_node_id, type="product", label=product.name))
        edges.append(
            GraphEdge(
                source=shipment_node_id, target=product_node_id, relationship="contains"
            )
        )

    for event in evidence.timeline:
        event_node_id = f"event:{event.id}"
        nodes.append(GraphNode(id=event_node_id, type="event", label=event.event_type))
        edges.append(
            GraphEdge(
                source=shipment_node_id, target=event_node_id, relationship="has_event"
            )
        )

    # Extend the highlighted path to the most relevant terminal node: the
    # exception event explaining a delay, if one exists; otherwise the first
    # product on the shipment, if any.
    if evidence.delay is not None and evidence.delay.exception_event is not None:
        highlighted_path.append(f"event:{evidence.delay.exception_event.id}")
    elif evidence.products:
        highlighted_path.append(f"product:{evidence.products[0].id}")

    return ProcurementGraph(
        nodes=nodes,
        edges=edges,
        highlighted_path=highlighted_path,
        retrieved_at=datetime.datetime.now(datetime.timezone.utc),
    )


async def lookup_procurement_graph(db: AsyncSession, tracking_code: str) -> ProcurementGraph:
    evidence = await lookup_procurement(db, tracking_code)
    return _project_procurement_graph(evidence)


# --- Grounded logistics answer generation -------------------------------------


@dataclass(frozen=True)
class LogisticsAnswer:
    """A grounded logistics response: complete answer text, evidence graph,
    and suggested follow-up questions.

    ``answer`` is either the LLM's generation (grounded only in
    ``ProcurementEvidence``) or, on any ``LLMError``, a deterministic
    fallback summary built directly from the evidence.
    """

    answer: str
    graph: ProcurementGraph
    follow_ups: list[str]


_SYSTEM_PROMPT = (
    "You are a logistics assistant. Answer the user's question using only the "
    "evidence provided below. Do not invent shipment, order, vendor, buyer, "
    "product, or timeline details that are not present in the evidence. If the "
    "evidence does not contain the answer, say so plainly. Never mention SQL, "
    "databases, or internal identifiers that are not part of the evidence."
)

_DEFAULT_FOLLOW_UPS: list[str] = [
    "Would you like the full shipment timeline?",
    "Do you want details on the products in this shipment?",
    "Should I check the related purchase order status?",
]


def _format_timestamp(value: datetime.datetime | None) -> str:
    if value is None:
        return "unknown"
    return value.isoformat()


def _format_evidence_for_prompt(evidence: ProcurementEvidence) -> str:
    """Render ``evidence`` as a plain-text block containing only retrieved facts.

    No field is invented: optional relationships (purchase order, buyer, delay)
    are described as "not on file" when absent rather than omitted silently,
    so the model cannot fill the gap with a guess.
    """
    shipment = evidence.shipment
    lines: list[str] = [
        "Shipment:",
        f"  tracking_code: {shipment.tracking_code}",
        f"  status: {shipment.status}",
        f"  origin: {shipment.origin}",
        f"  destination: {shipment.destination}",
        f"  dispatched_at: {_format_timestamp(shipment.dispatched_at)}",
        f"  expected_arrival_at: {_format_timestamp(shipment.expected_arrival_at)}",
        f"  actual_arrival_at: {_format_timestamp(shipment.actual_arrival_at)}",
    ]

    lines.append("Vendor:")
    lines.append(f"  name: {evidence.vendor.name}")
    lines.append(f"  country: {evidence.vendor.country or 'not on file'}")

    if evidence.purchase_order is not None:
        order = evidence.purchase_order
        lines.append("Purchase order:")
        lines.append(f"  order_number: {order.order_number}")
        lines.append(f"  status: {order.status}")
        lines.append(f"  ordered_at: {_format_timestamp(order.ordered_at)}")
        lines.append(
            f"  requested_delivery_at: {_format_timestamp(order.requested_delivery_at)}"
        )
    else:
        lines.append("Purchase order: not on file")

    if evidence.buyer is not None:
        lines.append("Buyer:")
        lines.append(f"  name: {evidence.buyer.name}")
    else:
        lines.append("Buyer: not on file")

    if evidence.products:
        lines.append("Products:")
        for product in evidence.products:
            unit = product.unit or "unit"
            lines.append(f"  - {product.name}: {product.quantity} {unit}")
    else:
        lines.append("Products: not on file")

    if evidence.timeline:
        lines.append("Timeline:")
        for event in evidence.timeline:
            details = f" ({event.details})" if event.details else ""
            lines.append(
                f"  - {_format_timestamp(event.occurred_at)} {event.event_type}"
                f" at {event.location}{details}"
            )
    else:
        lines.append("Timeline: not on file")

    if evidence.delay is not None:
        lines.append("Delay:")
        lines.append(f"  reason: {evidence.delay.reason}")
        if evidence.delay.exception_event is not None:
            exception_event = evidence.delay.exception_event
            details = f" ({exception_event.details})" if exception_event.details else ""
            lines.append(
                f"  exception_event: {_format_timestamp(exception_event.occurred_at)}"
                f" {exception_event.event_type} at {exception_event.location}{details}"
            )
        else:
            lines.append("  exception_event: not on file")
    else:
        lines.append("Delay: none reported")

    return "\n".join(lines)


def _build_logistics_prompt(question: str, evidence: ProcurementEvidence) -> "list[ChatMessage]":
    from app.services.llm import ChatMessage

    evidence_block = _format_evidence_for_prompt(evidence)
    user_content = (
        f"Evidence:\n{evidence_block}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the evidence above."
    )
    return [
        ChatMessage(role="system", content=_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_content),
    ]


def _deterministic_fallback(evidence: ProcurementEvidence) -> str:
    """Build a deterministic summary of ``evidence`` for use when the LLM is
    unavailable. Reports status, delay reason, vendor, buyer/order, products,
    and timing -- never invents fields absent from the evidence.
    """
    shipment = evidence.shipment
    parts: list[str] = [
        f"Shipment {shipment.tracking_code} is currently '{shipment.status}'.",
        f"It shipped from {shipment.origin} to {shipment.destination}, "
        f"dispatched {_format_timestamp(shipment.dispatched_at)} with an expected "
        f"arrival of {_format_timestamp(shipment.expected_arrival_at)}.",
    ]

    if shipment.actual_arrival_at is not None:
        parts.append(f"It actually arrived {_format_timestamp(shipment.actual_arrival_at)}.")

    if evidence.delay is not None:
        parts.append(f"Delay reason: {evidence.delay.reason}.")

    parts.append(f"Vendor: {evidence.vendor.name}.")

    if evidence.purchase_order is not None:
        order = evidence.purchase_order
        buyer_part = f" placed by {evidence.buyer.name}" if evidence.buyer is not None else ""
        parts.append(
            f"Purchase order {order.order_number} ({order.status}){buyer_part}."
        )

    if evidence.products:
        product_list = ", ".join(
            f"{product.name} ({product.quantity} {product.unit or 'unit'})"
            for product in evidence.products
        )
        parts.append(f"Products: {product_list}.")

    return " ".join(parts)


async def list_shipments_summary(
    db: AsyncSession,
    *,
    status_filter: str | None = None,
    limit: int = 20,
) -> list[ShipmentEvidence]:
    query = select(Shipment).order_by(Shipment.dispatched_at.desc()).limit(limit)
    if status_filter is not None:
        query = query.where(Shipment.status == status_filter)
    result = await db.execute(query)
    return [_shipment_evidence(s) for s in result.scalars().all()]


def _deterministic_browse_fallback(
    shipments: list[ShipmentEvidence], total_count: int
) -> str:
    if not shipments:
        return "No shipments found matching your query."
    lines: list[str] = []
    if total_count > len(shipments):
        lines.append(f"Showing {len(shipments)} of {total_count} shipments.\n")
    for s in shipments:
        arrival = _format_timestamp(s.actual_arrival_at) if s.actual_arrival_at else _format_timestamp(s.expected_arrival_at) + " (expected)"
        lines.append(
            f"- {s.tracking_code}: {s.status} | {s.origin} → {s.destination} | "
            f"dispatched {_format_timestamp(s.dispatched_at)} | arrival {arrival}"
        )
    return "\n".join(lines)


def _format_browse_evidence_for_prompt(
    shipments: list[ShipmentEvidence], total_count: int
) -> str:
    """Render a plain-text evidence block listing each shipment's key fields.

    Includes a "Showing X of Y shipments" header when the result set is
    truncated (``total_count > len(shipments)``).
    """
    lines: list[str] = []
    if total_count > len(shipments):
        lines.append(f"Showing {len(shipments)} of {total_count} shipments.\n")

    for s in shipments:
        lines.append(f"Shipment {s.tracking_code}:")
        lines.append(f"  status: {s.status}")
        lines.append(f"  origin: {s.origin}")
        lines.append(f"  destination: {s.destination}")
        lines.append(f"  dispatched_at: {_format_timestamp(s.dispatched_at)}")
        lines.append(f"  expected_arrival_at: {_format_timestamp(s.expected_arrival_at)}")
        lines.append(f"  delay_reason: {s.delay_reason or 'none'}")

    return "\n".join(lines)


_BROWSE_SYSTEM_PROMPT = (
    "You are a logistics assistant. Answer the user's question using only the "
    "shipment list evidence provided below. Do not invent shipment details that "
    "are not present in the evidence. If the evidence is empty, say no shipments "
    "were found. Never mention SQL, databases, or internal identifiers."
)


def _build_browse_logistics_prompt(
    question: str,
    shipments: list[ShipmentEvidence],
    total_count: int,
) -> "list[ChatMessage]":
    """Build system + user messages for a browse logistics query."""
    from app.services.llm import ChatMessage

    evidence_block = _format_browse_evidence_for_prompt(shipments, total_count)
    user_content = (
        f"Evidence:\n{evidence_block}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the evidence above."
    )
    return [
        ChatMessage(role="system", content=_BROWSE_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_content),
    ]


def _browse_follow_ups(shipments: list[ShipmentEvidence]) -> list[str]:
    """Suggest follow-up questions referencing specific tracking codes."""
    follow_ups: list[str] = []
    for s in shipments[:3]:
        follow_ups.append(f"Tell me more about shipment {s.tracking_code}")
    return follow_ups


async def generate_browse_logistics_answer(
    db: AsyncSession,
    *,
    llm: "LLMService | None" = None,
    status_filter: str | None = None,
    question: str,
    limit: int = 20,
) -> LogisticsAnswer:
    """Generate a grounded multi-shipment answer for a browse query.

    Retrieves up to ``limit`` shipments via ``list_shipments_summary()``,
    builds a browse prompt, and calls ``llm.chat()`` for a natural-language
    answer. On any ``LLMError`` or when ``llm`` is ``None``, falls back to
    ``_deterministic_browse_fallback()``. The graph is always an empty
    ``ProcurementGraph``. Follow-ups suggest specific shipment lookups from
    the returned list.
    """
    from sqlalchemy import func

    count_query = select(func.count()).select_from(Shipment)
    if status_filter is not None:
        count_query = count_query.where(Shipment.status == status_filter)
    total_count = (await db.execute(count_query)).scalar_one()

    shipments = await list_shipments_summary(
        db, status_filter=status_filter, limit=limit,
    )

    answer: str | None = None
    if llm is not None:
        from app.services.llm import LLMError

        try:
            messages = _build_browse_logistics_prompt(question, shipments, total_count)
            chunks = await llm.chat(messages, stream=False)
            answer = "".join([chunk async for chunk in chunks])
        except LLMError:
            answer = None

    if answer is None:
        answer = _deterministic_browse_fallback(shipments, total_count)

    empty_graph = ProcurementGraph(
        nodes=[], edges=[], highlighted_path=[],
        retrieved_at=datetime.datetime.now(datetime.timezone.utc),
    )
    follow_ups = _browse_follow_ups(shipments)
    return LogisticsAnswer(answer=answer, graph=empty_graph, follow_ups=follow_ups)


async def generate_grounded_logistics_answer(
    db: AsyncSession,
    llm: "LLMService",
    tracking_code: str,
    question: str,
) -> LogisticsAnswer:
    """Generate a grounded logistics answer for ``question`` about ``tracking_code``.

    Builds a provider-neutral prompt containing only retrieved
    ``ProcurementEvidence`` and the user's question, then calls
    ``LLMService.chat()`` with ``stream=False`` to obtain a complete answer.
    On any ``LLMError`` (timeout, rate limit, provider unavailable, etc.),
    returns a deterministic summary of the evidence instead. The evidence
    graph is always returned unchanged regardless of generation outcome.
    """
    from app.services.llm import LLMError

    evidence = await lookup_procurement(db, tracking_code)
    graph = _project_procurement_graph(evidence)

    try:
        messages = _build_logistics_prompt(question, evidence)
        chunks = await llm.chat(messages, stream=False)
        answer = "".join([chunk async for chunk in chunks])
    except LLMError:
        answer = _deterministic_fallback(evidence)

    return LogisticsAnswer(answer=answer, graph=graph, follow_ups=list(_DEFAULT_FOLLOW_UPS))


class RAGLogistics:
    async def query(self, text: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError


# --- Assistant intent routing ------------------------------------------------

# A routing decision selects which evidence sources (logistics, policy, or
# both) a downstream retrieval/generation step should consult.
AssistantIntent = Literal["logistics", "policy", "mixed", "logistics_browse"]

# Matches a shipment tracking identifier, e.g. "SHP-1234".
_SHIPMENT_ID_PATTERN = re.compile(r"\bSHP-\d{4,}\b", re.IGNORECASE)

# Matches a purchase order identifier, e.g. "PO-2026-001".
_PURCHASE_ORDER_ID_PATTERN = re.compile(r"\bPO-\d{4}-\d{3,}\b", re.IGNORECASE)

# Vocabulary that indicates a policy-topic question (returns, warranties,
# terms, eligibility, compliance, etc.). Matched as whole words against the
# lowercased question text.
_POLICY_TERMS: frozenset[str] = frozenset(
    {
        "policy",
        "policies",
        "return",
        "returns",
        "refund",
        "refunds",
        "warranty",
        "warranties",
        "terms",
        "eligibility",
        "eligible",
        "compliance",
        "guideline",
        "guidelines",
        "procedure",
        "procedures",
        "handbook",
    }
)

_POLICY_TERM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in _POLICY_TERMS) + r")\b",
    re.IGNORECASE,
)

_BROWSE_TERMS: frozenset[str] = frozenset(
    {
        "list",
        "all",
        "show",
        "find",
        "search",
        "shipments",
        "orders",
        "delayed",
        "pending",
    }
)

_BROWSE_TERM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in _BROWSE_TERMS) + r")\b",
    re.IGNORECASE,
)

_BROWSE_PHRASE_PATTERN = re.compile(r"\bhow\s+many\b", re.IGNORECASE)

_STATUS_FILTER_MAP: dict[str, str] = {
    "delayed": "delayed",
    "pending": "pending",
    "delivered": "delivered",
    "cancelled": "cancelled",
    "damaged": "damaged",
    "lost": "lost",
    "returned": "returned",
    "partial": "partial",
}

_STATUS_FILTER_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _STATUS_FILTER_MAP) + r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class IntentRouting:
    """A deterministic routing decision for an assistant question.

    `tracking_codes` and `purchase_order_numbers` hold normalized identifiers
    extracted from the question text -- never guessed. `confidence` is 1.0
    when an explicit identifier or policy term was matched, and a lower
    value for ambiguous questions routed by default.
    """

    intent: AssistantIntent
    confidence: float
    tracking_codes: list[str]
    purchase_order_numbers: list[str]
    reason: str
    status_filter: str | None = None


def classify_intent(text: str) -> IntentRouting:
    """Classify a question as logistics, policy, or mixed.

    Explicit ``SHP-####`` or ``PO-YYYY-###`` identifiers select logistics.
    Policy-topic terms (return, refund, warranty, policy, etc.) select
    policy. If both are present, the intent is mixed. Ambiguous operational
    questions with no identifier and no policy term default to logistics
    with no guessed identifier and a lower confidence.
    """
    tracking_codes = sorted(
        {match.group(0).upper() for match in _SHIPMENT_ID_PATTERN.finditer(text)}
    )
    purchase_order_numbers = sorted(
        {match.group(0).upper() for match in _PURCHASE_ORDER_ID_PATTERN.finditer(text)}
    )
    has_identifier = bool(tracking_codes or purchase_order_numbers)
    has_policy_term = _POLICY_TERM_PATTERN.search(text) is not None

    if has_identifier and has_policy_term:
        return IntentRouting(
            intent="mixed",
            confidence=1.0,
            tracking_codes=tracking_codes,
            purchase_order_numbers=purchase_order_numbers,
            reason="Question contains both a shipment/order identifier and policy terms.",
        )

    if has_identifier:
        return IntentRouting(
            intent="logistics",
            confidence=1.0,
            tracking_codes=tracking_codes,
            purchase_order_numbers=purchase_order_numbers,
            reason="Question contains an explicit shipment or purchase order identifier.",
        )

    if has_policy_term:
        return IntentRouting(
            intent="policy",
            confidence=1.0,
            tracking_codes=[],
            purchase_order_numbers=[],
            reason="Question contains policy-topic terms.",
        )

    has_browse_term = (
        _BROWSE_TERM_PATTERN.search(text) is not None
        or _BROWSE_PHRASE_PATTERN.search(text) is not None
    )

    if has_browse_term:
        status_match = _STATUS_FILTER_PATTERN.search(text)
        status_filter = (
            _STATUS_FILTER_MAP[status_match.group(0).lower()]
            if status_match
            else None
        )
        return IntentRouting(
            intent="logistics_browse",
            confidence=1.0,
            tracking_codes=[],
            purchase_order_numbers=[],
            reason="Question contains browse vocabulary for listing/filtering shipments.",
            status_filter=status_filter,
        )

    return IntentRouting(
        intent="logistics",
        confidence=0.5,
        tracking_codes=[],
        purchase_order_numbers=[],
        reason="Ambiguous operational question with no identifier; defaulting to logistics.",
    )
