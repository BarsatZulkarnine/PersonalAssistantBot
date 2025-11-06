"""
Memory Classifier - AI-Powered Memory Worth Detection

Classifies conversations into three tiers:
- EPHEMERAL: Don't store (greetings, time, weather, music commands)
- CONVERSATIONAL: Store in SQL only (jokes, generic Q&A)
- FACTUAL: Store in SQL + Vector DB (personal info, preferences, learnings)
"""

import os
import json
from typing import Optional, List
from openai import AsyncOpenAI
from dotenv import load_dotenv


from modules.memory.base import (
    MemoryClassifier, MemoryClassification, MemoryCategory, FactCategory
)
from utils.logger import get_logger

load_dotenv()
logger = get_logger('memory.classifier')

class AIMemoryClassifier(MemoryClassifier):
    """
    AI-powered memory classifier using OpenAI.
    
    Determines if a conversation should be:
    1. Ignored (ephemeral)
    2. Logged (conversational)
    3. Embedded (factual)
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.3):
        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        logger.info(f"Memory classifier initialized (model={model})")
    
    async def classify(
        self,
        user_input: str,
        assistant_response: str,
        intent_type: Optional[str] = None
    ) -> MemoryClassification:
        """
        Classify a conversation's memory worth.
        
        Args:
            user_input: What the user said
            assistant_response: What the assistant replied
            intent_type: Optional intent classification (AI, Web, Action)
            
        Returns:
            MemoryClassification with category and importance
        """
        try:
            # Build prompt
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(user_input, assistant_response, intent_type)
            
            # Call OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            
            classification = self._parse_classification(result)
            
            logger.info(
                f"Classified as {classification.category.value} "
                f"(importance: {classification.importance_score:.2f})"
            )
            logger.debug(f"Reasoning: {classification.reasoning}")
            
            return classification
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            # Fallback: treat as conversational
            return MemoryClassification(
                category=MemoryCategory.CONVERSATIONAL,
                importance_score=0.3,
                reasoning=f"Error during classification: {e}"
            )
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for classification"""
        return """You are a memory classification system. Your job is to determine if a conversation should be stored and how.

Classify conversations into ONE of these categories:

1. **EPHEMERAL** - Don't store at all
   - Greetings, goodbyes ("hello", "bye", "how are you")
   - Time/date queries ("what time is it", "what day is it")
   - Weather queries ("what's the weather")
   - Music commands ("play music", "pause", "skip")
   - Generic system commands with no learning value
   - Simple acknowledgments ("ok", "thanks", "sure")

2. **CONVERSATIONAL** - Store in SQL only (for history/context)
   - Jokes and stories
   - General knowledge questions
   - Explanations that don't reveal user preferences
   - Chitchat without personal information
   - Generic Q&A

3. **FACTUAL** - Store in SQL + Vector DB (important information)
   - Personal information (name, birthday, location, family)
   - Preferences (likes, dislikes, habits)
   - Opinions and beliefs
   - Important context (plans, decisions, goals)
   - User corrections ("actually, I prefer...", "I live in...")
   - Anything starting with "remember that..." or "don't forget..."

For FACTUAL conversations, also extract specific facts and categorize them:
- PERSONAL: Name, birthday, location, job, family
- PREFERENCE: Likes, dislikes, favorites
- KNOWLEDGE: Learned information, skills
- CONTEXT: Plans, decisions, ongoing situations
- OPINION: Beliefs, viewpoints, thoughts

Return JSON format:
{
    "category": "EPHEMERAL|CONVERSATIONAL|FACTUAL",
    "importance_score": 0.0-1.0,
    "fact_category": "PERSONAL|PREFERENCE|KNOWLEDGE|CONTEXT|OPINION" (only if FACTUAL),
    "extracted_facts": ["fact1", "fact2", ...] (only if FACTUAL),
    "reasoning": "Brief explanation"
}

Importance scoring:
- EPHEMERAL: 0.0
- CONVERSATIONAL: 0.1-0.4
- FACTUAL: 0.5-1.0
  - 0.5-0.6: Minor preferences
  - 0.7-0.8: Important preferences and context
  - 0.9-1.0: Critical personal information"""
    
    def _build_user_prompt(
        self,
        user_input: str,
        assistant_response: str,
        intent_type: Optional[str]
    ) -> str:
        """Build the user prompt"""
        prompt = f"""Classify this conversation:

User: {user_input}
Assistant: {assistant_response}"""
        
        if intent_type:
            prompt += f"\nIntent Type: {intent_type}"
        
        prompt += "\n\nProvide classification in JSON format."
        
        return prompt
    
    def _parse_classification(self, result: dict) -> MemoryClassification:
        """Parse the JSON result into MemoryClassification"""
        # Parse category
        category_str = result.get("category", "CONVERSATIONAL").upper()
        try:
            category = MemoryCategory[category_str]
        except KeyError:
            logger.warning(f"Unknown category '{category_str}', defaulting to CONVERSATIONAL")
            category = MemoryCategory.CONVERSATIONAL
        
        # Parse importance
        importance = float(result.get("importance_score", 0.3))
        importance = max(0.0, min(1.0, importance))  # Clamp to 0-1
        
        # Parse fact category (only for FACTUAL)
        fact_category = None
        if category == MemoryCategory.FACTUAL:
            fact_cat_str = result.get("fact_category")
            if fact_cat_str:
                try:
                    fact_category = FactCategory[fact_cat_str.upper()]
                except KeyError:
                    logger.warning(f"Unknown fact category '{fact_cat_str}'")
                    fact_category = FactCategory.CONTEXT  # Default
        
        # Parse extracted facts
        extracted_facts = result.get("extracted_facts", [])
        if not isinstance(extracted_facts, list):
            extracted_facts = []
        
        # Get reasoning
        reasoning = result.get("reasoning", "No reasoning provided")
        
        return MemoryClassification(
            category=category,
            importance_score=importance,
            fact_category=fact_category,
            extracted_facts=extracted_facts,
            reasoning=reasoning
        )
    
    async def classify_batch(
        self,
        conversations: List[tuple]
    ) -> List[MemoryClassification]:
        """
        Classify multiple conversations at once (for efficiency).
        
        Args:
            conversations: List of (user_input, assistant_response, intent_type) tuples
            
        Returns:
            List of MemoryClassification objects
        """
        # TODO: Implement batch classification for cost optimization
        # For now, classify one by one
        results = []
        for user_input, assistant_response, intent_type in conversations:
            classification = await self.classify(user_input, assistant_response, intent_type)
            results.append(classification)
        
        return results


# Convenience function

_classifier_instance = None

def get_classifier() -> AIMemoryClassifier:
    """Get or create global classifier instance"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = AIMemoryClassifier()
    return _classifier_instance