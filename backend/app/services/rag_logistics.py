import datetime
import re
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.models.shipment_event import ShipmentEvent, ShipmentEventType
from app.models.user import User
from app.models.vendor import Vendor

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

    exception_event: ShipmentEventEvidence | None = None
    for event in timeline:
        if event.event_type in EXCEPTION_EVENT_TYPES:
            exception_event = event

    return DelayEvidence(reason=shipment.delay_reason, exception_event=exception_event)


async def lookup_shipment(db: AsyncSession, tracking_code: str) -> ShipmentEvidence:
    shipment = await _load_shipment(db, tracking_code)
    return _shipment_evidence(shipment)


async def lookup_procurement(db: AsyncSession, tracking_code: str) -> ProcurementEvidence:
    shipment = await _load_shipment(db, tracking_code)

    vendor = (
        await db.execute(select(Vendor).where(Vendor.id == shipment.vendor_id))
    ).scalar_one()

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


class RAGLogistics:
    async def query(self, text: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError


# --- Assistant intent routing ------------------------------------------------

# A routing decision selects which evidence sources (logistics, policy, or
# both) a downstream retrieval/generation step should consult.
AssistantIntent = Literal["logistics", "policy", "mixed"]

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

    return IntentRouting(
        intent="logistics",
        confidence=0.5,
        tracking_codes=[],
        purchase_order_numbers=[],
        reason="Ambiguous operational question with no identifier; defaulting to logistics.",
    )
