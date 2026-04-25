# Morpheus Python SDK (alpha)

Agent-first SDK for the Morpheus commerce platform.

## Install

```bash
pip install -e services/sdk_python
```

## Quick start

```python
from morph_sdk import MorphAgentClient

agent = MorphAgentClient(
    base_url="https://store.example.com",
    agent_token="<token-from-AgentRegistration.token>",
    signing_secret="<AgentRegistration.signing_secret>",
)

products = agent.search_products("blender under 80 USD")

intent = agent.propose_intent(
    kind="checkout",
    summary="Buy the Vitamix Pro for me",
    payload={"product_id": products[0]["id"], "quantity": 1},
    estimated_amount=79.99,
    correlation_id="my-agent-run-id-1",
)

# The customer authorizes via the merchant's UI; the platform completes the intent.
intents = agent.list_my_intents(state="completed")
for i in intents:
    receipt = agent.receipt_for(i)
    if receipt and receipt.verify():
        print("verified:", receipt.intent_id, receipt.state)
```

## What the SDK does for you

- Sends every request with the agent bearer token to `/graphql/agent/`.
- Wraps `propose_agent_intent`, `my_agent_intents`, `semantic_search` GraphQL.
- Maps platform errors to typed exceptions (`PermissionDeniedError`, `AgentBudgetError`).
- Verifies signed receipts locally — you don't have to trust the wire.

## Roadmap

- Async client (`MorphAgentAsyncClient`)
- Built-in `cart.add` / `cart.checkout` flows
- MCP server adapter
- Webhook signature verification helpers (already in `morph_sdk.receipts`)
