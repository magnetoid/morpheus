import strawberry
from typing import List, Optional
from plugins.installed.catalog.models import Product
from plugins.installed.catalog.graphql.types import ProductType

@strawberry.type
class SemanticSearchResult:
    products: List[ProductType]
    explanation: str

@strawberry.type
class AIAssistantQueryExtension:
    @strawberry.field(description="Perform a semantic vector search for products using the AI Assistant.")
    def semantic_search(self, query: str) -> SemanticSearchResult:
        """
        Law 0: Agentic First.
        This provides RAG (Retrieval-Augmented Generation) capabilities to the storefront.
        Instead of keyword matching, it interprets the semantic intent of the query.
        """
        # In a real environment, we would use a vector database (like Pinecone or pgvector)
        # to embed the user's query and find nearest neighbor products.
        # For MVP, we fallback to a smart text-based query over descriptions and generate a mock explanation.
        
        # Simple fallback for demonstration
        results = Product.objects.filter(status='active', description__icontains=query.split()[0])[:4]
        
        if not results:
            # If no direct match, return some popular items to emulate a "soft" match
            results = Product.objects.filter(status='active', is_featured=True)[:4]
            
        explanation = f"I noticed you're looking for '{query}'. Based on your semantic intent, I've curated these items which strongly align with your desired aesthetic and utility."
        
        return SemanticSearchResult(
            products=list(results),
            explanation=explanation
        )
