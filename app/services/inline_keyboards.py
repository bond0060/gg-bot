import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from enum import Enum

logger = logging.getLogger(__name__)


class CallbackAction(str, Enum):
    """Callback actions for inline keyboards"""
    ANSWER_QUESTION = "ans"
    GENERATE_PLAN = "plan"
    MORE_INFO = "more"
    DESTINATION = "dest"
    DURATION = "dur"
    BUDGET = "budg"
    GROUP_SIZE = "grp"
    INTERESTS = "int"
    DATES = "date"
    FLIGHT_DETAILS = "flight"
    AIRLINE_PREF = "airline"
    AIRPORT_PREF = "airport"
    TRAVEL_TIME = "time"
    FLIGHT_CHOICE = "flight_choice"


class InlineKeyboardService:
    """Service for creating and managing inline keyboards"""
    
    def __init__(self):
        self.callback_prefix = "travelbot"
        
    def create_follow_up_keyboard(
        self, 
        questions_data: List[Dict[str, Any]],
        chat_id: int,
        context: Dict[str, Any] = None
    ) -> Optional[InlineKeyboardMarkup]:
        """Create inline keyboard for follow-up questions"""
        
        if not questions_data:
            return None
        
        keyboard = []
        
        # Add question-specific buttons
        for i, question_data in enumerate(questions_data):
            question_type = question_data.get("type", "general")
            buttons = self._create_question_buttons(question_data, i, chat_id)
            if buttons:
                keyboard.extend(buttons)
        
        # Add general action buttons
        action_buttons = self._create_action_buttons(chat_id, context)
        if action_buttons:
            keyboard.extend(action_buttons)
        
        return InlineKeyboardMarkup(keyboard) if keyboard else None
    
    def _create_question_buttons(
        self, 
        question_data: Dict[str, Any], 
        question_index: int,
        chat_id: int
    ) -> List[List[InlineKeyboardButton]]:
        """Create buttons for a specific question"""
        
        question_type = question_data.get("type", "general")
        question_text = question_data.get("question", "")
        
        buttons = []
        
        if question_type == "destination":
            buttons.append([
                InlineKeyboardButton("🏖️ Beach/Tropical", 
                    callback_data=self._create_callback(CallbackAction.DESTINATION, "beach", chat_id)),
                InlineKeyboardButton("🏔️ Mountains", 
                    callback_data=self._create_callback(CallbackAction.DESTINATION, "mountains", chat_id))
            ])
            buttons.append([
                InlineKeyboardButton("🏛️ City/Culture", 
                    callback_data=self._create_callback(CallbackAction.DESTINATION, "city", chat_id)),
                InlineKeyboardButton("🌿 Nature/Adventure", 
                    callback_data=self._create_callback(CallbackAction.DESTINATION, "nature", chat_id))
            ])
            
        elif question_type == "duration":
            buttons.append([
                InlineKeyboardButton("🎯 Weekend (2-3 days)", 
                    callback_data=self._create_callback(CallbackAction.DURATION, "weekend", chat_id)),
                InlineKeyboardButton("📅 Week (4-7 days)", 
                    callback_data=self._create_callback(CallbackAction.DURATION, "week", chat_id))
            ])
            buttons.append([
                InlineKeyboardButton("📆 2 weeks", 
                    callback_data=self._create_callback(CallbackAction.DURATION, "two_weeks", chat_id)),
                InlineKeyboardButton("🗓️ Month+", 
                    callback_data=self._create_callback(CallbackAction.DURATION, "month", chat_id))
            ])
            
        elif question_type == "budget":
            buttons.append([
                InlineKeyboardButton("💸 Budget ($)", 
                    callback_data=self._create_callback(CallbackAction.BUDGET, "budget", chat_id)),
                InlineKeyboardButton("💳 Moderate ($$)", 
                    callback_data=self._create_callback(CallbackAction.BUDGET, "moderate", chat_id))
            ])
            buttons.append([
                InlineKeyboardButton("💎 Luxury ($$$)", 
                    callback_data=self._create_callback(CallbackAction.BUDGET, "luxury", chat_id)),
                InlineKeyboardButton("🏦 No limit", 
                    callback_data=self._create_callback(CallbackAction.BUDGET, "unlimited", chat_id))
            ])
            
        elif question_type == "group_size":
            buttons.append([
                InlineKeyboardButton("🧳 Solo travel", 
                    callback_data=self._create_callback(CallbackAction.GROUP_SIZE, "solo", chat_id)),
                InlineKeyboardButton("👫 Couple", 
                    callback_data=self._create_callback(CallbackAction.GROUP_SIZE, "couple", chat_id))
            ])
            buttons.append([
                InlineKeyboardButton("👨‍👩‍👧‍👦 Family", 
                    callback_data=self._create_callback(CallbackAction.GROUP_SIZE, "family", chat_id)),
                InlineKeyboardButton("👥 Group of friends", 
                    callback_data=self._create_callback(CallbackAction.GROUP_SIZE, "group", chat_id))
            ])
            
        elif question_type == "interests":
            buttons.append([
                InlineKeyboardButton("🍜 Food & cuisine", 
                    callback_data=self._create_callback(CallbackAction.INTERESTS, "food", chat_id)),
                InlineKeyboardButton("🏛️ Culture & history", 
                    callback_data=self._create_callback(CallbackAction.INTERESTS, "culture", chat_id))
            ])
            buttons.append([
                InlineKeyboardButton("🎢 Adventure & sports", 
                    callback_data=self._create_callback(CallbackAction.INTERESTS, "adventure", chat_id)),
                InlineKeyboardButton("🛍️ Shopping & nightlife", 
                    callback_data=self._create_callback(CallbackAction.INTERESTS, "shopping", chat_id))
            ])
            
        elif question_type == "dates":
            buttons.append([
                InlineKeyboardButton("🌸 Spring", 
                    callback_data=self._create_callback(CallbackAction.DATES, "spring", chat_id)),
                InlineKeyboardButton("☀️ Summer", 
                    callback_data=self._create_callback(CallbackAction.DATES, "summer", chat_id))
            ])
            buttons.append([
                InlineKeyboardButton("🍂 Fall/Autumn", 
                    callback_data=self._create_callback(CallbackAction.DATES, "fall", chat_id)),
                InlineKeyboardButton("❄️ Winter", 
                    callback_data=self._create_callback(CallbackAction.DATES, "winter", chat_id))
            ])
            
        elif question_type == "flight_details":
            buttons.append([
                InlineKeyboardButton("✈️ Show specific flights", 
                    callback_data=self._create_callback(CallbackAction.FLIGHT_DETAILS, "specific", chat_id)),
                InlineKeyboardButton("💰 Show price ranges", 
                    callback_data=self._create_callback(CallbackAction.FLIGHT_DETAILS, "prices", chat_id))
            ])
            buttons.append([
                InlineKeyboardButton("🕐 Best departure times", 
                    callback_data=self._create_callback(CallbackAction.FLIGHT_DETAILS, "times", chat_id)),
                InlineKeyboardButton("🏢 Airport recommendations", 
                    callback_data=self._create_callback(CallbackAction.FLIGHT_DETAILS, "airports", chat_id))
            ])
            
        elif question_type == "airline_pref":
            buttons.append([
                InlineKeyboardButton("🇨🇳 Chinese airlines", 
                    callback_data=self._create_callback(CallbackAction.AIRLINE_PREF, "chinese", chat_id)),
                InlineKeyboardButton("🇯🇵 Japanese airlines", 
                    callback_data=self._create_callback(CallbackAction.AIRLINE_PREF, "japanese", chat_id))
            ])
            buttons.append([
                InlineKeyboardButton("🌍 International airlines", 
                    callback_data=self._create_callback(CallbackAction.AIRLINE_PREF, "international", chat_id)),
                InlineKeyboardButton("💎 Premium airlines", 
                    callback_data=self._create_callback(CallbackAction.AIRLINE_PREF, "premium", chat_id))
            ])
            
        elif question_type == "airport_pref":
            buttons.append([
                InlineKeyboardButton("✈️ Haneda (HND) - Closer to city", 
                    callback_data=self._create_callback(CallbackAction.AIRPORT_PREF, "haneda", chat_id)),
                InlineKeyboardButton("🛫 Narita (NRT) - More flights", 
                    callback_data=self._create_callback(CallbackAction.AIRPORT_PREF, "narita", chat_id))
            ])
        
        elif question_type == "travel_time":
            buttons.append([
                InlineKeyboardButton("🌅 Morning flights", 
                    callback_data=self._create_callback(CallbackAction.TRAVEL_TIME, "morning", chat_id)),
                InlineKeyboardButton("🌞 Afternoon flights", 
                    callback_data=self._create_callback(CallbackAction.TRAVEL_TIME, "afternoon", chat_id))
            ])
            buttons.append([
                InlineKeyboardButton("🌆 Evening flights", 
                    callback_data=self._create_callback(CallbackAction.TRAVEL_TIME, "evening", chat_id)),
                InlineKeyboardButton("🚫 No red-eye flights", 
                    callback_data=self._create_callback(CallbackAction.TRAVEL_TIME, "no_red_eye", chat_id))
            ])
        
        elif question_type == "flight_options":
            # Create buttons for flight options (方案A, 方案B, 方案C, 都不满意)
            options = question_data.get("options", ["方案A", "方案B", "方案C", "都不满意"])
            
            # Add blue square prefix for better visibility (Telegram buttons have no bg color)
            def decorate(label: str) -> str:
                return f"🔷 {label}"
            
            # Create buttons in pairs
            for i in range(0, len(options), 2):
                row = []
                row.append(InlineKeyboardButton(
                    decorate(options[i]), 
                    callback_data=self._create_callback(CallbackAction.FLIGHT_CHOICE, options[i], chat_id)
                ))
                
                if i + 1 < len(options):
                    row.append(InlineKeyboardButton(
                        decorate(options[i + 1]), 
                        callback_data=self._create_callback(CallbackAction.FLIGHT_CHOICE, options[i + 1], chat_id)
                    ))
                
                buttons.append(row)
        
        elif question_type == "general":
            # Handle general questions with default options
            options = question_data.get("options", ["Yes", "No", "Maybe"])
            
            # Add emoji prefix for better visibility
            def decorate(label: str) -> str:
                if "yes" in label.lower() or "是" in label or "好的" in label:
                    return f"✅ {label}"
                elif "no" in label.lower() or "不" in label or "否" in label:
                    return f"❌ {label}"
                elif "maybe" in label.lower() or "可能" in label or "也许" in label:
                    return f"🤔 {label}"
                else:
                    return f"💬 {label}"
            
            # Create buttons in pairs
            for i in range(0, len(options), 2):
                row = []
                row.append(InlineKeyboardButton(
                    decorate(options[i]), 
                    callback_data=self._create_callback(CallbackAction.ANSWER_QUESTION, options[i], chat_id)
                ))
                
                if i + 1 < len(options):
                    row.append(InlineKeyboardButton(
                        decorate(options[i + 1]), 
                        callback_data=self._create_callback(CallbackAction.ANSWER_QUESTION, options[i + 1], chat_id)
                    ))
                buttons.append(row)
        
        return buttons
    
    def _create_action_buttons(self, chat_id: int, context: Dict[str, Any] = None) -> List[List[InlineKeyboardButton]]:
        """Create general action buttons"""
        
        action_buttons = []
        
        # Main actions
        action_buttons.append([
            InlineKeyboardButton("✨ Generate travel plan", 
                callback_data=self._create_callback(CallbackAction.GENERATE_PLAN, "now", chat_id)),
            InlineKeyboardButton("💬 Tell me more", 
                callback_data=self._create_callback(CallbackAction.MORE_INFO, "general", chat_id))
        ])
        
        return action_buttons
    
    def _create_callback(self, action: CallbackAction, value: str, chat_id: int) -> str:
        """Create callback data string"""
        callback_data = {
            "a": action.value,  # action
            "v": value,         # value
            "c": chat_id        # chat_id
        }
        
        # Telegram callback data limit is 64 bytes
        callback_str = json.dumps(callback_data, separators=(',', ':'))
        
        if len(callback_str) > 64:
            # Fallback to shorter format
            callback_str = f"{action.value}:{value}:{chat_id}"
            if len(callback_str) > 64:
                callback_str = f"{action.value}:{value}"[:64]
        
        return callback_str
    
    def parse_callback_data(self, callback_data: str) -> Dict[str, str]:
        """Parse callback data back to dict"""
        try:
            # Try JSON format first
            if callback_data.startswith('{'):
                data = json.loads(callback_data)
                return {
                    "action": data.get("a", ""),
                    "value": data.get("v", ""),
                    "chat_id": str(data.get("c", ""))
                }
            else:
                # Fallback to colon-separated format
                parts = callback_data.split(':')
                return {
                    "action": parts[0] if len(parts) > 0 else "",
                    "value": parts[1] if len(parts) > 1 else "",
                    "chat_id": parts[2] if len(parts) > 2 else ""
                }
        except Exception as e:
            logger.error(f"Error parsing callback data: {e}")
            return {"action": "", "value": "", "chat_id": ""}
    
    def create_quick_action_keyboard(self, chat_id: int) -> InlineKeyboardMarkup:
        """Create quick action keyboard for common travel questions"""
        
        keyboard = [
            [
                InlineKeyboardButton("🗺️ Plan my trip", 
                    callback_data=self._create_callback(CallbackAction.GENERATE_PLAN, "quick", chat_id)),
                InlineKeyboardButton("💡 Give me ideas", 
                    callback_data=self._create_callback(CallbackAction.MORE_INFO, "ideas", chat_id))
            ],
            [
                InlineKeyboardButton("🏖️ Beach destinations", 
                    callback_data=self._create_callback(CallbackAction.DESTINATION, "beach", chat_id)),
                InlineKeyboardButton("🏛️ City breaks", 
                    callback_data=self._create_callback(CallbackAction.DESTINATION, "city", chat_id))
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_user_answer(self, action: str, value: str) -> str:
        """Format user's button selection as natural text"""
        
        # Map callback values to natural language
        value_map = {
            # Destinations
            "beach": "🏖️ Beach/tropical destinations",
            "mountains": "🏔️ Mountain destinations", 
            "city": "🏛️ City/cultural destinations",
            "nature": "🌿 Nature/adventure destinations",
            
            # Duration
            "weekend": "🎯 Weekend trip (2-3 days)",
            "week": "📅 One week trip",
            "two_weeks": "📆 Two week vacation",
            "month": "🗓️ Long-term travel (month+)",
            
            # Budget
            "budget": "💸 Budget travel",
            "moderate": "💳 Moderate budget",
            "luxury": "💎 Luxury travel",
            "unlimited": "🏦 No budget limits",
            
            # Group size
            "solo": "🧳 Solo travel",
            "couple": "👫 Couple's trip",
            "family": "👨‍👩‍👧‍👦 Family vacation", 
            "group": "👥 Group of friends",
            
            # Interests
            "food": "🍜 Food & cuisine",
            "culture": "🏛️ Culture & history",
            "adventure": "🎢 Adventure & sports",
            "shopping": "🛍️ Shopping & nightlife",
            
            # Dates
            "spring": "🌸 Spring travel",
            "summer": "☀️ Summer vacation",
            "fall": "🍂 Fall/autumn trip",
            "winter": "❄️ Winter getaway"
        }
        
        return value_map.get(value, f"Selected: {value}")


# Global inline keyboard service
inline_keyboard_service = InlineKeyboardService()