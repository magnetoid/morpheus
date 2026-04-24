import logging
from celery import shared_task
from plugins.registry import plugin_registry
from plugins.installed.ai_assistant.services.operator import AgentOperator
from plugins.installed.orders.models import Order

logger = logging.getLogger('morpheus.ai.listeners')

@shared_task
def proactive_agent_worker(event_name, payload):
    """
    Law 0: Agentic First.
    This background task is triggered by core Morpheus events.
    It spins up an AgentOperator to autonomously decide if it should act on the event.
    """
    logger.info(f"Proactive Agent awakened by event: {event_name}")
    
    operator = AgentOperator()
    
    # 1. Provide context to the agent
    context = f"You are a proactive Morpheus AI Commerce Agent. An event '{event_name}' just occurred in the system. The payload is: {payload}."
    
    # 2. Assign specific objectives based on the event
    objective = ""
    if event_name == 'order.placed':
        objective = """
        Analyze the placed order. 
        1. If the order total is above $500, flag it as high-value and generate a draft VIP thank-you email.
        2. Check for potential fraud markers (e.g., mismatching shipping/billing if available in context).
        3. Determine an appropriate cross-sell category for their next visit.
        """
    elif event_name == 'customer.created':
        objective = "A new customer joined! Analyze their domain and assign a segmentation tag if they are a B2B client."
    else:
        objective = "Review the event and determine if any autonomous action is required."
        
    full_prompt = f"{context}\n\nObjective: {objective}"
    
    # 3. Run the autonomous loop
    # In a real environment, we'd pass full_prompt to the LLM. 
    # For now, we mock the execution via our operator.
    try:
        result = operator.run_workflow(full_prompt)
        logger.info(f"Proactive Agent completed task for {event_name}. Result: {result}")
    except Exception as e:
        logger.error(f"Proactive Agent failed on {event_name}: {e}", exc_info=True)

def register_proactive_agents(plugin_instance):
    """
    Registers the proactive agent worker to the core event bus.
    Called during the AI Assistant plugin's ready() lifecycle.
    """
    from core.hooks import MorpheusEvents
    
    def on_order_placed(order, **kwargs):
        # We serialize the minimal data needed for the AI context
        payload = {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "total_amount": str(order.total.amount),
            "currency": order.total.currency.code,
            "customer_id": str(order.customer.id) if order.customer else None,
        }
        proactive_agent_worker.delay(MorpheusEvents.ORDER_PLACED, payload)
        
    def on_customer_created(customer, **kwargs):
        payload = {
            "customer_id": str(customer.id),
            "email": customer.user.email,
        }
        proactive_agent_worker.delay(MorpheusEvents.CUSTOMER_CREATED, payload)

    # Bind the hooks
    plugin_instance.register_hook(MorpheusEvents.ORDER_PLACED, on_order_placed, priority=90)
    plugin_instance.register_hook(MorpheusEvents.CUSTOMER_CREATED, on_customer_created, priority=90)
    
    logger.info("Proactive Agent listeners successfully bound to Morpheus Event Bus.")
