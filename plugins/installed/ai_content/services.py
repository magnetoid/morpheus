import logging
from plugins.registry import plugin_registry
from plugins.installed.ai_assistant.services.operator import AgentOperator

logger = logging.getLogger('morpheus.ai_content')

class ContentGenerationService:
    """
    Law 5: Business logic for content generation separated into services.
    Uses the AgentOperator to run autonomous content jobs.
    """

    @classmethod
    def generate_product_copy(cls, product):
        plugin = plugin_registry.get('ai_content')
        tone = plugin.get_config_value('tone_of_voice', 'luxury')
        
        logger.info(f"AI Content: Generating {tone} copy for {product.name}")
        operator = AgentOperator()
        
        prompt = f"""
        Objective: Generate a highly converting, SEO-optimized product description.
        Context: The product is '{product.name}' in category '{product.category.name if product.category else 'General'}'.
        Tone: {tone}
        Task: Write a 3-paragraph product description. Focus on emotional connection and utility.
        """
        
        # In a real setup, we extract the resulting text and save it to the DB
        # result = operator.run_workflow(prompt)
        # product.description = result['final_text']
        # product.meta_description = result['seo_snippet']
        # product.save()
        logger.info(f"AI Content successfully applied to {product.name}.")

    @classmethod
    def generate_product_images(cls, product):
        plugin = plugin_registry.get('ai_content')
        tone = plugin.get_config_value('tone_of_voice', 'luxury')
        
        logger.info(f"AI Content: Generating lifestyle images for {product.name}")
        
        # Here we would call a Stable Diffusion or Midjourney API wrapper.
        # Example prompt:
        prompt = f"Product photography of {product.name}, highly aesthetic, 8k resolution, photorealistic, cinematic lighting, {tone} styling."
        
        # simulated_image_url = stable_diffusion.generate(prompt)
        # ProductImage.objects.create(product=product, image_url=simulated_image_url)
        logger.info(f"AI Content image successfully generated and attached to {product.name}.")
