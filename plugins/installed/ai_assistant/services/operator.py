import json
import logging
from api.schema import get_schema
from core.schema_introspector import SchemaIntrospector

logger = logging.getLogger('morpheus.ai.operator')

class AgentOperator:
    """
    Law 0: Agentic First.
    The autonomous workflow loop that processes an objective, calls necessary GraphQL tools natively,
    and returns a final synthesized response.
    """
    
    def __init__(self, provider="openai"):
        self.provider = provider
        self.schema = get_schema()
        self.tools = self._get_available_tools()
        
    def _get_available_tools(self):
        """Introspects schema to build internal tool definitions."""
        introspector = SchemaIntrospector()
        return introspector.as_agent_tool_map()

    def execute_tool(self, tool_name, kwargs):
        """Executes a GraphQL tool natively without HTTP overhead."""
        if tool_name not in self.tools:
            return {"error": f"Tool {tool_name} not found"}
            
        tool = self.tools[tool_name]
        
        # Build arguments string
        args_str = ", ".join([f"{k}: {json.dumps(v)}" for k, v in kwargs.items()])
        args_block = f"({args_str})" if args_str else ""
        
        # We query the entire object blindly for simplicity in this MVP.
        # In a real environment, we'd dynamically request all scalar sub-fields.
        graphql_query = f"""
        {tool['type']} {{
            {tool['field_name']}{args_block}
        }}
        """
        
        logger.info(f"AgentOperator executing: {tool_name} with {kwargs}")
        result = self.schema.execute_sync(graphql_query)
        
        if result.errors:
            logger.error(f"Tool error: {result.errors}")
            return {"error": str(result.errors[0].message)}
            
        return result.data

    def run_workflow(self, objective: str):
        """
        Runs the autonomous agent loop.
        In a complete implementation, this would:
        1. Send the objective and self.tools to an LLM (e.g. GPT-4).
        2. Receive a tool call.
        3. Execute the tool natively via execute_tool().
        4. Send the result back to the LLM.
        5. Repeat until the LLM returns a final answer.
        """
        logger.info(f"Starting Agent Workflow for objective: {objective}")
        
        # Mocking an agent loop for demonstration
        if "add" in objective.lower() and "cart" in objective.lower():
            # The LLM decides to call mutate_add_to_cart
            result = self.execute_tool("mutate_add_to_cart", {"input": "product-slug"})
            return {"status": "success", "steps_taken": ["mutate_add_to_cart"], "final_result": result}
            
        elif "payment" in objective.lower():
            result = self.execute_tool("mutate_create_payment_intent", {"order_id": "123"})
            return {"status": "success", "steps_taken": ["mutate_create_payment_intent"], "final_result": result}
            
        else:
            return {"status": "unknown", "message": "Objective requires a real LLM connection"}
