from core.services.llm import llm_service


class ChatService:
    """Chat wrapper that delegates to the shared LLMService so it inherits
    dynamic model resolution, provider fallback, retries, and circuit breaking.
    No model id is hardcoded — the current model is resolved at runtime."""

    async def get_chat_response(self, message: str):
        try:
            text = await llm_service.complete(prompt=message, max_tokens=1024)
            if text:
                return text
            return "Sorry, I'm having trouble connecting to the AI. Please check the console for more details."
        except Exception as e:
            print(f"Error getting chat response: {e}")
            return "Sorry, I'm having trouble connecting to the AI. Please check the console for more details."


chat_service = ChatService()
