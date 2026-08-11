from langchain_core.tools import tool

@tool
def message_fulfillment_team(message: str) -> str:
    """Send a message to the fulfillment team regarding an order."""
    return f"Sent to fulfillment team: {message}"

@tool
def message_payments_team(message: str) -> str:
    """Send a message to the payments team regarding an order."""
    return f"Sent to payments team: {message}"

@tool
def message_logistics_team(message: str) -> str:
    """Send a message to the logistics team regarding an order."""
    return f"Sent to logistics team: {message}"

@tool
def message_customer(message: str) -> str:
    """Send a direct message to the customer regarding their order."""
    return f"Sent to customer: {message}"

@tool
def create_internal_note(note: str) -> str:
    """Create an internal note for record keeping on the order."""
    return f"Internal note created: {note}"

AVAILABLE_TOOLS = {
    "message_fulfillment_team": message_fulfillment_team,
    "message_payments_team": message_payments_team,
    "message_logistics_team": message_logistics_team,
    "message_customer": message_customer,
    "create_internal_note": create_internal_note,
}
