from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActionBadge:
    label: str
    prompt: str


_EMPLOYEE_BADGES: list[ActionBadge] = [
    ActionBadge("Read full policy", "Show me the full text of the relevant policy"),
    ActionBadge("Ask a follow-up", "I have a follow-up question about this policy"),
    ActionBadge("Talk to my manager", "How do I escalate this to my manager?"),
]

_CUSTOMS_HOLD_BADGES: list[ActionBadge] = [
    ActionBadge("Contact vendor about docs", "Contact the vendor about the customs clearance paperwork for this shipment"),
    ActionBadge("Extend delivery estimate", "Extend the delivery estimate for this shipment due to the customs hold"),
    ActionBadge("Watch for release", "Notify me when customs is cleared for this shipment"),
]

_STATUS_BADGES: dict[str, list[ActionBadge]] = {
    "pending": [
        ActionBadge("Ask vendor for dispatch date", "Ask the vendor when this shipment will be dispatched"),
        ActionBadge("Change expected arrival", "Update the expected arrival date for this shipment"),
        ActionBadge("Cancel order", "Cancel the order for this shipment"),
    ],
    "in_transit": [
        ActionBadge("Track next update", "Notify me when the next tracking event arrives for this shipment"),
        ActionBadge("Notify client", "Notify the client that this shipment is on its way"),
        ActionBadge("Flag concern", "Flag a concern about this shipment"),
    ],
    "delayed": [
        ActionBadge("Ask vendor for explanation", "Ask the vendor for an explanation of the delay on this shipment"),
        ActionBadge("Extend delivery estimate", "Extend the delivery estimate for this shipment"),
        ActionBadge("Escalate to manager", "Escalate this delayed shipment to a manager"),
    ],
    "damaged": [
        ActionBadge("File claim with vendor", "File a damage claim with the vendor for this shipment"),
        ActionBadge("Request replacement", "Request a replacement order for this damaged shipment"),
        ActionBadge("Document damage", "Document the damage for this shipment"),
    ],
    "partial": [
        ActionBadge("Confirm what arrived", "Reconcile the received items against the expected items for this shipment"),
        ActionBadge("Request remaining items", "Ask the vendor to ship the remaining items for this shipment"),
        ActionBadge("Adjust purchase order", "Adjust the purchase order quantities for this partial delivery"),
    ],
    "cancelled": [
        ActionBadge("Request refund", "Request a refund for this cancelled shipment"),
        ActionBadge("Reorder from same vendor", "Reorder from the same vendor for this cancelled shipment"),
        ActionBadge("Find alternate vendor", "Find an alternate vendor to replace this cancelled order"),
    ],
    "returned": [
        ActionBadge("Confirm vendor received return", "Confirm the vendor received the returned shipment"),
        ActionBadge("Request credit/refund", "Request a credit or refund for this returned shipment"),
        ActionBadge("Reorder", "Reorder the goods from this returned shipment"),
    ],
    "lost": [
        ActionBadge("File claim", "File an insurance or liability claim for this lost shipment"),
        ActionBadge("Reorder urgently", "Place an urgent reorder for this lost shipment"),
        ActionBadge("Notify client", "Notify the client about this lost shipment"),
    ],
}


def select_badges(
    status: str,
    latest_event_type: str | None,
    role: str,
) -> list[ActionBadge]:
    if role == "employee":
        return _EMPLOYEE_BADGES[:3]

    if latest_event_type == "customs_hold":
        return _CUSTOMS_HOLD_BADGES[:3]

    if status == "delivered":
        return []

    badges = _STATUS_BADGES.get(status, [])
    return badges[:3]
