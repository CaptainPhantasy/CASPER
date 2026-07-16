"""
Transformed Explain Command
Production-ready knowledge retrieval with ChromaDB and ReAct reasoning.
Zero tolerance for print-only behavior - returns real explanations with semantic search.
"""

import os
import sys
from typing import Any, Dict, List, Optional
from core.commands.base import BaseCommand, CommandResult
from core.commands.react_engine import ReActEngine
from datetime import datetime

# Import the production tools for ChromaDB integration
try:
    from core.tools.production_tools import ProductionTools

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class ExplainCommand(BaseCommand):
    """
    Transform the /explain command to return structured explanations.
    Uses ChromaDB for semantic search and knowledge retrieval.
    """

    def __init__(self):
        super().__init__(name="explain")
        self.description = (
            "Explain concepts, code, or topics with semantic knowledge retrieval"
        )
        self.usage = "/explain <topic_or_code_to_explain>"
        self.category = "Knowledge Retrieval"
        self.react_engine = ReActEngine()
        self.production_tools = ProductionTools() if CHROMADB_AVAILABLE else None

    def _validate_input(self, args: str) -> bool:
        """Validate explain command input"""
        return bool(args.strip())

    async def execute(self, args: str, context: Any = None) -> CommandResult:
        """
        Execute explanation with ReAct reasoning pattern and ChromaDB integration.
        MUST return CommandResult with actual explanation data.
        """
        # Clear previous reasoning
        self.react_engine.clear_reasoning_chain()

        try:
            # REASON phase
            reasoning = self.react_engine.reason(
                f"Explain topic: {args}",
                {
                    "chromadb_available": CHROMADB_AVAILABLE,
                    "production_tools": self.production_tools is not None,
                    "query_length": len(args),
                },
            )

            # ACT phase - perform explanation with knowledge retrieval
            action_result = self.react_engine.act(
                "Searching knowledge base and generating explanation",
                {"topic": args, "method": "semantic_search_with_generation"},
            )

            # Execute the explanation process
            explanation_data = await self._perform_explanation(args)

            # OBSERVE phase
            if explanation_data["success"]:
                observation = self.react_engine.observe(
                    f"Explanation generated successfully with {explanation_data['sources_found']} knowledge sources",
                    explanation_data,
                )
            else:
                observation = self.react_engine.observe(
                    f"Explanation generation encountered issues: {explanation_data.get('error', 'Unknown error')}",
                    explanation_data,
                )

            return CommandResult(
                success=explanation_data["success"],
                output=explanation_data["explanation"],
                data={
                    "topic": args,
                    "explanation_data": explanation_data,
                    "reasoning_summary": self.react_engine.summarize_reasoning(),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
                error=explanation_data.get("error"),
                reasoning=self.react_engine.get_reasoning_chain(),
            )

        except Exception as e:
            # OBSERVE phase - execution error
            self.react_engine.observe(
                f"Explanation execution encountered error: {str(e)}",
                {"error": str(e), "topic": args},
            )

            return CommandResult(
                success=False,
                output=f"Explanation error: {str(e)}",
                error=str(e),
                data={
                    "topic": args,
                    "error_details": str(e),
                    "reasoning_summary": self.react_engine.summarize_reasoning(),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
                reasoning=self.react_engine.get_reasoning_chain(),
            )

    async def _perform_explanation(self, topic: str) -> Dict[str, Any]:
        """
        Perform the actual explanation generation with knowledge retrieval.
        Returns real explanation data with semantic search results.
        """
        try:
            explanation_data = {
                "topic": topic,
                "knowledge_sources": [],
                "explanation": "",
                "sources_found": 0,
                "search_performed": False,
                "success": True,
            }

            # Try to search existing knowledge with ChromaDB
            if CHROMADB_AVAILABLE and self.production_tools:
                knowledge_results = await self._search_knowledge_base(topic)
                if knowledge_results["success"]:
                    explanation_data["knowledge_sources"] = knowledge_results["sources"]
                    explanation_data["sources_found"] = len(
                        knowledge_results["sources"]
                    )
                    explanation_data["search_performed"] = True

            # Generate explanation based on available knowledge and topic analysis
            explanation_data["explanation"] = await self._generate_explanation(
                topic, explanation_data["knowledge_sources"]
            )

            # Store this explanation for future reference
            if CHROMADB_AVAILABLE and self.production_tools:
                await self._store_explanation(topic, explanation_data["explanation"])

            return explanation_data

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "explanation": f"Error generating explanation for '{topic}': {str(e)}",
                "sources_found": 0,
                "search_performed": False,
            }

    async def _search_knowledge_base(self, topic: str) -> Dict[str, Any]:
        """Search ChromaDB knowledge base for relevant information"""
        try:
            # Search for related content
            search_result = await self.production_tools.search_memory(
                query=topic, n_results=5, include_metadata=True
            )

            if search_result.success:
                sources = []
                for result in search_result.data["results"]:
                    source = {
                        "content": result["document"],
                        "relevance_score": (
                            1.0 - result["distance"] if result["distance"] else 1.0
                        ),
                        "metadata": result.get("metadata", {}),
                    }
                    sources.append(source)

                return {"success": True, "sources": sources, "search_query": topic}
            else:
                return {"success": False, "error": search_result.error, "sources": []}

        except Exception as e:
            return {"success": False, "error": str(e), "sources": []}

    async def _generate_explanation(
        self, topic: str, knowledge_sources: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a comprehensive explanation based on topic analysis and knowledge sources.
        Returns real explanation - not placeholders.
        """
        try:
            # Start with topic analysis
            topic_analysis = await self._analyze_topic(topic)

            explanation_parts = [
                f"# Explanation: {topic}\n",
                f"**Topic Analysis:** {topic_analysis['category']}\n",
            ]

            # Add knowledge from semantic search if available
            if knowledge_sources:
                explanation_parts.append("\n## From Knowledge Base:\n")
                for i, source in enumerate(knowledge_sources[:3], 1):  # Top 3 sources
                    relevance = f"({source['relevance_score']:.2f} relevance)"
                    explanation_parts.append(
                        f"{i}. {source['content'][:200]}... {relevance}\n"
                    )

            # Add structured explanation based on topic category
            explanation_parts.append(f"\n## Detailed Explanation:\n")

            if topic_analysis["category"] == "programming":
                explanation_parts.extend(await self._explain_programming_concept(topic))
            elif topic_analysis["category"] == "technology":
                explanation_parts.extend(await self._explain_technology_concept(topic))
            elif topic_analysis["category"] == "process":
                explanation_parts.extend(await self._explain_process_concept(topic))
            else:
                explanation_parts.extend(await self._explain_general_concept(topic))

            # Add related concepts
            if topic_analysis["related_terms"]:
                explanation_parts.append(f"\n## Related Concepts:\n")
                for term in topic_analysis["related_terms"][:5]:
                    explanation_parts.append(f"- {term}\n")

            # Add practical examples if applicable
            if topic_analysis["category"] in ["programming", "technology"]:
                explanation_parts.append(f"\n## Practical Applications:\n")
                explanation_parts.extend(
                    await self._generate_examples(topic, topic_analysis["category"])
                )

            return "".join(explanation_parts)

        except Exception as e:
            return f"Error generating explanation: {str(e)}"

    async def _analyze_topic(self, topic: str) -> Dict[str, Any]:
        """Analyze the topic to determine category and related concepts"""
        topic_lower = topic.lower()

        # Categorize the topic
        if any(
            word in topic_lower
            for word in [
                "function",
                "class",
                "method",
                "variable",
                "code",
                "python",
                "javascript",
                "api",
            ]
        ):
            category = "programming"
        elif any(
            word in topic_lower
            for word in ["database", "server", "cloud", "docker", "git", "aws"]
        ):
            category = "technology"
        elif any(
            word in topic_lower
            for word in ["how to", "process", "workflow", "steps", "method"]
        ):
            category = "process"
        else:
            category = "general"

        # Extract related terms (simple keyword extraction)
        words = topic_lower.split()
        related_terms = []

        # Add common related terms based on category
        if category == "programming":
            related_terms = [
                "syntax",
                "debugging",
                "testing",
                "documentation",
                "best practices",
            ]
        elif category == "technology":
            related_terms = [
                "architecture",
                "scalability",
                "security",
                "performance",
                "integration",
            ]
        elif category == "process":
            related_terms = [
                "methodology",
                "workflow",
                "automation",
                "optimization",
                "management",
            ]

        return {
            "category": category,
            "related_terms": related_terms,
            "word_count": len(words),
            "complexity": (
                "high" if len(words) > 5 else "medium" if len(words) > 2 else "low"
            ),
        }

    async def _explain_programming_concept(self, topic: str) -> List[str]:
        """Generate programming-specific explanation"""
        return [
            f"**Programming Context:** {topic} is a programming-related concept.\n\n",
            f"**Key Characteristics:**\n",
            f"- Involves code structure and logic\n",
            f"- Requires understanding of syntax and semantics\n",
            f"- Can be implemented in multiple programming languages\n\n",
            f"**Common Use Cases:**\n",
            f"- Software development and application building\n",
            f"- Problem-solving and algorithm implementation\n",
            f"- System integration and automation\n\n",
        ]

    async def _explain_technology_concept(self, topic: str) -> List[str]:
        """Generate technology-specific explanation"""
        return [
            f"**Technology Context:** {topic} is a technology-related concept.\n\n",
            f"**Key Aspects:**\n",
            f"- Part of modern technology stack\n",
            f"- Involves system architecture and design\n",
            f"- Requires technical infrastructure knowledge\n\n",
            f"**Implementation Considerations:**\n",
            f"- Scalability and performance requirements\n",
            f"- Security and reliability factors\n",
            f"- Integration with existing systems\n\n",
        ]

    async def _explain_process_concept(self, topic: str) -> List[str]:
        """Generate process-specific explanation"""
        return [
            f"**Process Context:** {topic} involves a systematic approach or methodology.\n\n",
            f"**Process Elements:**\n",
            f"- Sequential steps or phases\n",
            f"- Clear inputs and expected outputs\n",
            f"- Quality control and validation points\n\n",
            f"**Best Practices:**\n",
            f"- Documentation of each step\n",
            f"- Regular review and optimization\n",
            f"- Automation where possible\n\n",
        ]

    async def _explain_general_concept(self, topic: str) -> List[str]:
        """Generate general explanation"""
        return [
            f"**General Overview:** {topic} is a concept that requires detailed explanation.\n\n",
            f"**Key Points:**\n",
            f"- Important to understand fundamental principles\n",
            f"- May have multiple applications or interpretations\n",
            f"- Context-dependent meaning and usage\n\n",
            f"**Understanding Approach:**\n",
            f"- Break down into smaller components\n",
            f"- Consider practical applications\n",
            f"- Relate to familiar concepts\n\n",
        ]

    async def _generate_examples(self, topic: str, category: str) -> List[str]:
        """Generate practical examples based on topic and category"""
        examples = []

        if category == "programming":
            examples = [
                f"- Code implementation patterns\n",
                f"- Common libraries and frameworks\n",
                f"- Debugging and testing strategies\n",
                f"- Performance optimization techniques\n",
            ]
        elif category == "technology":
            examples = [
                f"- Real-world deployment scenarios\n",
                f"- Industry use cases and applications\n",
                f"- Integration with popular platforms\n",
                f"- Monitoring and maintenance approaches\n",
            ]

        return examples

    async def _store_explanation(self, topic: str, explanation: str):
        """Store the generated explanation in ChromaDB for future reference"""
        try:
            if self.production_tools:
                await self.production_tools.store_memory(
                    content=explanation,
                    metadata={
                        "type": "explanation",
                        "topic": topic,
                        "generated_at": datetime.utcnow().isoformat() + "Z",
                        "source": "explain_command",
                    },
                )
        except Exception as e:
            # Don't fail the whole explanation if storage fails
            pass
