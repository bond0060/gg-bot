import logging
import json
from typing import List, Dict, Any, Optional
from enum import Enum
from openai import AsyncOpenAI
from app.services.conversation_memory import conversation_memory
from app.config.settings import settings

logger = logging.getLogger(__name__)


class QuestionType(str, Enum):
    DESTINATION = "destination"
    DURATION = "duration"
    BUDGET = "budget"
    GROUP_SIZE = "group_size"
    TRAVEL_TYPE = "travel_type"
    INTERESTS = "interests"
    DATES = "dates"
    ACCOMMODATION = "accommodation"
    ACTIVITIES = "activities"


class FollowUpQuestionService:
    """Service to generate contextual follow-up questions for faster planning"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.question_templates = self._init_question_templates()  # Keep as fallback
        
    def _init_question_templates(self) -> Dict[QuestionType, List[str]]:
        """Initialize question templates for different scenarios"""
        return {
            QuestionType.DESTINATION: [
                "Where would you like to travel? 🌍",
                "What destination do you have in mind? ✈️",
                "Which city or country interests you? 🗺️"
            ],
            QuestionType.DURATION: [
                "How long is your trip? (e.g., 3 days, 1 week) ⏰",
                "What's your trip duration? 📅",
                "How many days are you planning to travel? 🗓️"
            ],
            QuestionType.BUDGET: [
                "What's your budget range? (budget/moderate/luxury) 💰",
                "Are you looking for budget, moderate, or luxury travel? 💳",
                "What's your budget level for this trip? 🏦"
            ],
            QuestionType.GROUP_SIZE: [
                "How many people are traveling? 👥",
                "Is this for solo travel, couple, family, or group? 🧳",
                "Who's joining you on this trip? 👫"
            ],
            QuestionType.TRAVEL_TYPE: [
                "What type of trip is this? (leisure/business/adventure/relaxation) 🎯",
                "Are you looking for adventure, relaxation, culture, or business? 🎪",
                "What's the main purpose of your trip? 🌟"
            ],
            QuestionType.INTERESTS: [
                "What activities interest you? (food/culture/nature/adventure/shopping) 🎨",
                "What would you like to experience? (museums/beaches/nightlife/local cuisine) 🍜",
                "Any specific interests or must-see attractions? 🏛️"
            ],
            QuestionType.DATES: [
                "When are you planning to travel? 📆",
                "Do you have specific travel dates in mind? 🗓️",
                "What time of year works best for you? 🌸"
            ],
            QuestionType.ACCOMMODATION: [
                "What type of accommodation do you prefer? (hotel/hostel/apartment/resort) 🏨",
                "Any accommodation preferences? 🛏️",
                "Where would you like to stay? 🏠"
            ],
            QuestionType.ACTIVITIES: [
                "What kind of activities excite you most? 🎭",
                "Are you more into active adventures or cultural experiences? 🚴‍♀️",
                "What would make this trip perfect for you? ⭐"
            ]
        }
    
    def should_ask_follow_up(self, message: str, context: Dict[str, Any]) -> bool:
        """Determine if we should ask follow-up questions"""
        message_lower = message.lower()
        chat_id = context.get("chat_id")
        
        # Don't ask if user just generated a plan
        if any(keyword in message_lower for keyword in ["plan", "itinerary", "schedule"]):
            return False
            
        # Don't ask if message is too short (likely not a travel query)
        if len(message.split()) < 3:
            return False
            
        # Don't ask if user is sharing specific details (photos, links, long descriptions)
        if len(message) > 200:
            return False
            
        # Check if this looks like a travel-related query
        travel_keywords = [
            "travel", "trip", "vacation", "holiday", "visit", "go to", "planning",
            "destination", "flight", "hotel", "budget", "days", "week", "month"
        ]
        
        has_travel_context = any(keyword in message_lower for keyword in travel_keywords)
        
        # Check conversation history for travel context
        if chat_id:
            travel_context = conversation_memory.get_travel_context_summary(chat_id)
            if travel_context.get("destinations_mentioned") or travel_context.get("photos_shared", 0) > 0:
                has_travel_context = True
        
        return has_travel_context
    
    def get_missing_info(self, context: Dict[str, Any]) -> List[QuestionType]:
        """Identify what travel information is missing from conversation"""
        chat_id = context.get("chat_id")
        missing_info = []
        
        if not chat_id:
            return [QuestionType.DESTINATION, QuestionType.DURATION, QuestionType.BUDGET]
        
        # Get conversation context
        travel_context = conversation_memory.get_travel_context_summary(chat_id)
        conversation_history = conversation_memory.get_recent_context(chat_id, max_messages=10)
        
        # Check what's missing based on conversation
        history_lower = conversation_history.lower()
        
        # Check for destination
        if (not travel_context.get("destinations_mentioned") and 
            not any(word in history_lower for word in ["to", "in", "visit", "going"])):
            missing_info.append(QuestionType.DESTINATION)
        
        # Check for duration
        duration_keywords = ["day", "week", "month", "weekend", "night", "long"]
        if not any(word in history_lower for word in duration_keywords):
            missing_info.append(QuestionType.DURATION)
        
        # Check for budget
        budget_keywords = ["budget", "cheap", "expensive", "luxury", "moderate", "$", "cost", "money"]
        if not any(word in history_lower for word in budget_keywords):
            missing_info.append(QuestionType.BUDGET)
        
        # Check for group size
        if not travel_context.get("group_size"):
            group_keywords = ["solo", "couple", "family", "friend", "group", "people", "us", "we"]
            if not any(word in history_lower for word in group_keywords):
                missing_info.append(QuestionType.GROUP_SIZE)
        
        # Check for interests/activities  
        interest_keywords = ["food", "culture", "beach", "museum", "adventure", "nature", "shopping", "nightlife"]
        if not any(word in history_lower for word in interest_keywords):
            missing_info.append(QuestionType.INTERESTS)
        
        return missing_info[:3]  # Limit to 3 questions to avoid overwhelming
    
    def generate_follow_up_questions(
        self, 
        message: str, 
        context: Dict[str, Any], 
        max_questions: int = 2
    ) -> List[str]:
        """Generate contextual follow-up questions"""
        
        if not self.should_ask_follow_up(message, context):
            return []
        
        missing_info = self.get_missing_info(context)
        
        if not missing_info:
            return []
        
        # Select most important questions
        priority_order = [
            QuestionType.DESTINATION,
            QuestionType.DURATION,
            QuestionType.BUDGET,
            QuestionType.GROUP_SIZE,
            QuestionType.INTERESTS
        ]
        
        # Sort missing info by priority
        prioritized_missing = []
        for priority_type in priority_order:
            if priority_type in missing_info:
                prioritized_missing.append(priority_type)
        
        # Add any remaining missing info
        for info_type in missing_info:
            if info_type not in prioritized_missing:
                prioritized_missing.append(info_type)
        
        # Generate questions
        questions = []
        for i, info_type in enumerate(prioritized_missing[:max_questions]):
            templates = self.question_templates.get(info_type, [])
            if templates:
                # Use different templates to avoid repetition
                question = templates[i % len(templates)]
                questions.append(question)
        
        return questions
    
    def format_follow_up_response(
        self, 
        main_response: str, 
        follow_up_questions: List[str]
    ) -> str:
        """Format the response with follow-up questions"""
        
        if not follow_up_questions:
            return main_response
        
        response = main_response + "\n\n"
        
        if len(follow_up_questions) == 1:
            response += f"💡 Quick question: {follow_up_questions[0]}"
        else:
            response += "💡 *Quick questions to help me plan better:*\n"
            for i, question in enumerate(follow_up_questions, 1):
                response += f"{i}. {question}\n"
        
        return response
    
    def get_contextual_questions_for_photo(self, caption: str, context: Dict[str, Any]) -> List[str]:
        """Generate follow-up questions specific to photo sharing"""
        questions = []
        
        missing_info = self.get_missing_info(context)
        
        # Photo-specific questions
        if QuestionType.DESTINATION in missing_info:
            questions.append("Is this where you're planning to visit? 📍")
        elif QuestionType.INTERESTS in missing_info:
            questions.append("What attracted you to this place? 🤔")
        
        # Add one more general question
        if QuestionType.DURATION in missing_info:
            questions.append("How long would you like to spend there? ⏱️")
        elif QuestionType.BUDGET in missing_info:
            questions.append("What's your budget range for this trip? 💰")
            
        return questions[:2]
    
    def get_contextual_questions_for_link(self, urls: List[str], context: Dict[str, Any]) -> List[str]:
        """Generate follow-up questions specific to link sharing"""
        questions = []
        
        missing_info = self.get_missing_info(context)
        
        # Link-specific questions
        if QuestionType.DURATION in missing_info:
            questions.append("How long are you planning to stay? 📅")
        
        if QuestionType.BUDGET in missing_info:
            questions.append("What's your budget level? (budget/moderate/luxury) 💳")
            
        return questions[:2]

    async def generate_llm_follow_up_questions(
        self,
        user_message: str,
        bot_response: str,
        context: Dict[str, Any],
        max_questions: int = 2
    ) -> List[str]:
        """Generate contextual follow-up questions using LLM"""
        try:
            chat_id = context.get("chat_id")
            user_name = context.get("user_name", "User")
            
            # Get conversation context
            conversation_history = ""
            travel_context_summary = ""
            
            if chat_id:
                conversation_history = conversation_memory.get_recent_context(chat_id, max_messages=8)
                travel_context = conversation_memory.get_travel_context_summary(chat_id)
                travel_context_summary = self._format_travel_context_for_llm(travel_context)
            
            # Build system prompt for follow-up question generation
            system_prompt = self._build_follow_up_system_prompt()
            
            # Build user prompt with context
            user_prompt = self._build_follow_up_user_prompt(
                user_message, bot_response, conversation_history, 
                travel_context_summary, user_name, max_questions
            )
            
            logger.info("Generating LLM follow-up questions")
            
            # Call OpenAI with JSON mode for structured output
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            result = json.loads(response.choices[0].message.content)
            
            # Check if we should ask questions
            should_ask = result.get("should_ask", False)
            if not should_ask:
                return []
            
            questions_data = result.get("questions", [])
            
            # Convert to simple list for backward compatibility (for now)
            questions = []
            for q_data in questions_data:
                if isinstance(q_data, dict):
                    questions.append(q_data.get("question", ""))
                else:
                    questions.append(str(q_data))
            
            logger.info(f"Generated {len(questions)} follow-up questions")
            return questions[:max_questions]
            
        except Exception as e:
            logger.error(f"Error generating LLM follow-up questions: {e}")
            # Fallback to template-based questions
            return self.generate_follow_up_questions(user_message, context, max_questions)

    def _build_follow_up_system_prompt(self) -> str:
        """Build system prompt for follow-up question generation"""
        return f"""You are {settings.bot_name}, an expert travel planning assistant. Your job is to generate smart, contextual follow-up questions to help users plan their trips faster.

IMPORTANT: You must respond with valid JSON only. No additional text outside the JSON.

Analyze the conversation and generate 0-2 highly relevant follow-up questions that will help gather the most important missing travel information.

Rules for good follow-up questions:
1. Only ask if the information is genuinely missing and important
2. Make questions natural and conversational, not robotic
3. Use emojis to make questions friendly
4. Be specific to what the user just said
5. Prioritize: destination → duration → budget → group size → interests
6. Don't ask if the information is already clear from context
7. Don't ask if user just provided a detailed plan or comprehensive info

Special rules for flight queries:
- If user asks about flights, use flight_details, airline_pref, airport_pref, or travel_time types
- flight_details: for specific flight info, prices, times, airport recommendations
- airline_pref: for airline preferences (Chinese, Japanese, international, premium)
- airport_pref: for airport choice (Haneda vs Narita, etc.)
- travel_time: for departure time preferences (morning, afternoon, evening, no red-eye)

CRITICAL: If the bot response contains flight options (方案A, 方案B, 方案C), generate flight option buttons instead of general questions.
Flight option format:
{
  "question": "请选择您喜欢的航班方案",
  "type": "flight_options",
  "options": ["方案A", "方案B", "方案C", "都不满意"]
}

Response format:
{{
  "should_ask": true/false,
  "reasoning": "Why these questions are helpful",
  "questions": [
    {{
      "question": "What type of destination interests you most?",
      "type": "destination", 
      "context": "User mentioned wanting to travel but no destination specified"
    }},
    {{
      "question": "How long are you planning to travel?",
      "type": "duration",
      "context": "Duration not mentioned in conversation"
    }}
  ]
}}

Question types: destination, duration, budget, group_size, interests, dates, flight_details, airline_pref, airport_pref, travel_time, general

If no questions are needed, return:
{{
  "should_ask": false,
  "reasoning": "User provided sufficient information", 
  "questions": []
}}"""

    def _build_follow_up_user_prompt(
        self,
        user_message: str,
        bot_response: str,
        conversation_history: str,
        travel_context_summary: str,
        user_name: str,
        max_questions: int
    ) -> str:
        """Build user prompt for follow-up question generation"""
        
        prompt = f"""Analyze this travel conversation and generate follow-up questions.

User: {user_name}
Max questions: {max_questions}

Latest Exchange:
User said: "{user_message}"
Bot responded: "{bot_response}"

"""
        
        if conversation_history and conversation_history != "No previous conversation history.":
            prompt += f"Recent Conversation Context:\n{conversation_history}\n\n"
        
        if travel_context_summary:
            prompt += f"Travel Context Already Known:\n{travel_context_summary}\n\n"
        
        prompt += """Generate smart follow-up questions that:
1. Help gather the most important missing travel information
2. Are natural and contextual to what the user just said
3. Avoid asking what's already known from conversation
4. Feel like genuine curiosity, not a robotic checklist

Return JSON with your analysis and questions."""
        
        return prompt

    def _format_travel_context_for_llm(self, travel_context: Dict[str, Any]) -> str:
        """Format travel context for LLM prompt"""
        if not travel_context:
            return "No travel context yet"
        
        context_parts = []
        
        if travel_context.get("destinations_mentioned"):
            destinations = ", ".join(travel_context["destinations_mentioned"])
            context_parts.append(f"Destinations mentioned: {destinations}")
        
        if travel_context.get("group_size"):
            context_parts.append(f"Travel type: {travel_context['group_size']}")
        
        if travel_context.get("photos_shared", 0) > 0:
            context_parts.append(f"Photos shared: {travel_context['photos_shared']}")
        
        if travel_context.get("links_shared", 0) > 0:
            context_parts.append(f"Links shared: {travel_context['links_shared']}")
        
        if travel_context.get("budget_mentions"):
            context_parts.append("Budget preferences discussed")
        
        return "\n".join(context_parts) if context_parts else "No specific travel context"

    # Update the main generation method to use LLM
    async def generate_smart_follow_up_questions(
        self,
        user_message: str,
        bot_response: str,
        context: Dict[str, Any],
        max_questions: int = 2
    ) -> List[str]:
        """Generate intelligent follow-up questions using LLM (main method)"""
        
        # Quick check if we should even try to ask questions
        if not self.should_ask_follow_up(user_message, context):
            return []
        
        # Use LLM to generate contextual questions
        return await self.generate_llm_follow_up_questions(
            user_message, bot_response, context, max_questions
        )

    async def generate_structured_follow_up_questions(
        self,
        user_message: str,
        bot_response: str,
        context: Dict[str, Any],
        max_questions: int = 2
    ) -> List[Dict[str, Any]]:
        """Generate structured follow-up questions for inline keyboards"""
        
        try:
            # Check if this is a flight response with options
            if self._has_flight_options(bot_response):
                return self._generate_flight_option_buttons()
            
            chat_id = context.get("chat_id")
            user_name = context.get("user_name", "User")
            
            # Get conversation context
            conversation_history = ""
            travel_context_summary = ""
            
            if chat_id:
                conversation_history = conversation_memory.get_recent_context(chat_id, max_messages=8)
                travel_context = conversation_memory.get_travel_context_summary(chat_id)
                travel_context_summary = self._format_travel_context_for_llm(travel_context)
            
            # Build system prompt for follow-up question generation
            system_prompt = self._build_follow_up_system_prompt()
            
            # Build user prompt with context
            user_prompt = self._build_follow_up_user_prompt(
                user_message, bot_response, conversation_history, 
                travel_context_summary, user_name, max_questions
            )
            
            logger.info("Generating structured LLM follow-up questions")
            
            # Call OpenAI with JSON mode for structured output
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            result = json.loads(response.choices[0].message.content)
            
            # Check if we should ask questions
            should_ask = result.get("should_ask", False)
            if not should_ask:
                return []
            
            questions_data = result.get("questions", [])
            
            logger.info(f"Generated {len(questions_data)} structured follow-up questions")
            return questions_data[:max_questions]
            
        except Exception as e:
            logger.error(f"Error generating structured follow-up questions: {e}")
            # Return empty list on error
            return []
    
    def _has_flight_options(self, bot_response: str) -> bool:
        """Check if bot response contains flight options (方案A, 方案B, 方案C)"""
        flight_keywords = ["方案A", "方案B", "方案C"]
        return any(keyword in bot_response for keyword in flight_keywords)
    
    def _generate_flight_option_buttons(self) -> List[Dict[str, Any]]:
        """Generate flight option buttons"""
        return [{
            "question": "请选择您喜欢的航班方案",
            "type": "flight_options",
            "options": ["方案A", "方案B", "方案C", "都不满意"]
        }]


# Global follow-up question service
follow_up_service = FollowUpQuestionService()