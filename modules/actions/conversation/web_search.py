"""
Real Web Search Action using Brave Search API

UPDATED: Now supports memory context injection for personalized search responses.
"""

import os
import requests
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv
from modules.actions.base import Action, ActionResult, ActionCategory, SecurityLevel
from utils.logger import get_logger

load_dotenv()
logger = get_logger('actions.web_search_real')

class WebSearchAction(Action):
    """Real web search with Brave Search API + Memory Context"""
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.CONVERSATION
        self.security_level = SecurityLevel.SAFE
        self.description = "Search the web for current information with memory context"
        
        # Brave API
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        
        # OpenAI for summarization
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        if self.brave_api_key:
            logger.info("[OK] Web search initialized with Brave API + Memory support")
            print("[OK] Web search: Using Brave Search API + Memory")
        else:
            logger.warning("[WARN] BRAVE_API_KEY not found, using AI fallback")
            print("[WARN] Web search: No API key, using AI fallback")
    
    def get_intents(self) -> List[str]:
        return [
            "search for",
            "search up",
            "look up",
            "find",
            "what is",
            "who is",
            "when did",
            "where is",
            "how to",
            "what's the score",
            "today's",
            "current",
            "latest",
            "weather"
        ]
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        logger.info(f"Web search: {prompt}")
        print(f"[WEB] Searching: {prompt}")
        
        # NEW: Extract memory context if provided
        memory_context = ""
        if params and 'memory_context' in params:
            memory_context = params['memory_context']
            logger.info(f"Using memory context ({len(memory_context)} chars)")
            print(f"[WEB] Injecting memory context")
        
        # Try real search if API key available
        if self.brave_api_key:
            return await self._brave_search(prompt, memory_context)
        else:
            return await self._ai_fallback(prompt, memory_context)
    
    async def _brave_search(self, query: str, memory_context: str = "") -> ActionResult:
        """Search using Brave API with memory context"""
        try:
            print(f"[WEB] Using Brave Search API...")
            
            # Call Brave API
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.brave_api_key
                },
                params={
                    "q": query,
                    "count": 5,
                    "search_lang": "en"
                },
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Brave API error: {response.status_code}")
                print(f"[FAIL] Brave API error: {response.status_code}")
                return await self._ai_fallback(query, memory_context)
            
            data = response.json()
            results = data.get("web", {}).get("results", [])
            
            if not results:
                print("[WARN] No search results found")
                return await self._ai_fallback(query, memory_context)
            
            print(f"[OK] Found {len(results)} results")
            
            # Summarize with AI (with memory context)
            return await self._summarize_results(query, results, memory_context)
            
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            print(f"[FAIL] Search error: {e}")
            return await self._ai_fallback(query, memory_context)
    
    async def _summarize_results(
        self, 
        query: str, 
        results: list, 
        memory_context: str = ""
    ) -> ActionResult:
        """Use AI to summarize search results WITH MEMORY CONTEXT"""
        try:
            # Build context from search results
            search_context = ""
            for i, result in enumerate(results[:3], 1):
                title = result.get("title", "")
                description = result.get("description", "")
                search_context += f"{i}. {title}\n{description}\n\n"
            
            # Build system prompt
            system_prompt = (
                "You are a helpful assistant that summarizes web search results. "
                "Provide a concise, accurate answer based on the search results below. "
                "Keep it conversational and under 3 sentences. "
                "If the results don't contain the answer, say so briefly."
            )
            
            # NEW: Inject memory context if available
            if memory_context:
                system_prompt += f"""

{memory_context}

Use the above information about the user to personalize your response. 
Reference past conversations naturally when relevant."""
            
            # Ask AI to summarize
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Question: {query}\n\nSearch results:\n{search_context}\n\nAnswer:"
                    }
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            answer = response.choices[0].message.content.strip()
            
            print(f"[OK] Generated answer ({len(answer)} chars)")
            
            return ActionResult(
                success=True,
                message=answer,
                data={
                    "query": query,
                    "source": "brave_search",
                    "num_results": len(results),
                    "used_memory": bool(memory_context)
                }
            )
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return await self._ai_fallback(query, memory_context)
    
    async def _ai_fallback(self, query: str, memory_context: str = "") -> ActionResult:
        """Fallback to AI-only when no API available WITH MEMORY CONTEXT"""
        try:
            print(f"[FALLBACK] Using AI without real search...")
            
            # Build system prompt
            system_prompt = (
                "You are a helpful assistant. Answer questions based on your knowledge. "
                "For questions about current events, weather, or real-time data: "
                "- Acknowledge you don't have real-time access "
                "- Provide general/historical context if relevant "
                "- Suggest where they can find current information "
                "Keep responses concise (2-3 sentences)."
            )
            
            # NEW: Inject memory context
            if memory_context:
                system_prompt += f"""

{memory_context}

Use the above information about the user to personalize your response."""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            answer = response.choices[0].message.content.strip()
            
            print(f"[OK] AI fallback answer")
            
            return ActionResult(
                success=True,
                message=answer,
                data={
                    "query": query,
                    "source": "ai_fallback",
                    "used_memory": bool(memory_context)
                }
            )
            
        except Exception as e:
            logger.error(f"AI fallback error: {e}")
            print(f"[FAIL] AI fallback error: {e}")
            
            return ActionResult(
                success=False,
                message="Sorry, web search is currently unavailable."
            )