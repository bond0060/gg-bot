import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Represents a single message in conversation history"""
    role: str  # 'user' or 'assistant'
    content: str
    message_type: str  # 'text', 'photo', 'link', 'document'
    timestamp: datetime
    user_name: str
    chat_id: int
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class ConversationMemory:
    """Manages conversation history for different chats"""
    
    def __init__(self, max_messages_per_chat: int = 20, max_age_hours: int = 24):
        self.conversations: Dict[int, List[ConversationMessage]] = {}
        self.max_messages_per_chat = max_messages_per_chat
        self.max_age_hours = max_age_hours
        
    def add_user_message(
        self,
        chat_id: int,
        content: str,
        message_type: str,
        user_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a user message to conversation history"""
        message = ConversationMessage(
            role="user",
            content=content,
            message_type=message_type,
            timestamp=datetime.now(),
            user_name=user_name,
            chat_id=chat_id,
            metadata=metadata or {}
        )
        
        self._add_message(chat_id, message)
        logger.debug(f"Added user message to chat {chat_id}: {content[:50]}...")

    def add_assistant_message(
        self,
        chat_id: int,
        content: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an assistant response to conversation history"""
        message = ConversationMessage(
            role="assistant",
            content=content,
            message_type=message_type,
            timestamp=datetime.now(),
            user_name="TravelBot",
            chat_id=chat_id,
            metadata=metadata or {}
        )
        
        self._add_message(chat_id, message)
        logger.debug(f"Added assistant message to chat {chat_id}: {content[:50]}...")

    def _add_message(self, chat_id: int, message: ConversationMessage) -> None:
        """Add message to conversation and manage history limits"""
        if chat_id not in self.conversations:
            self.conversations[chat_id] = []
        
        self.conversations[chat_id].append(message)
        
        # Clean up old messages
        self._cleanup_conversation(chat_id)

    def _cleanup_conversation(self, chat_id: int) -> None:
        """Remove old messages based on limits"""
        if chat_id not in self.conversations:
            return
            
        messages = self.conversations[chat_id]
        
        # Remove messages older than max_age_hours
        cutoff_time = datetime.now() - timedelta(hours=self.max_age_hours)
        messages = [msg for msg in messages if msg.timestamp >= cutoff_time]
        
        # Keep only the most recent max_messages_per_chat messages
        if len(messages) > self.max_messages_per_chat:
            messages = messages[-self.max_messages_per_chat:]
        
        self.conversations[chat_id] = messages

    def get_conversation_history(
        self,
        chat_id: int,
        max_messages: Optional[int] = None
    ) -> List[ConversationMessage]:
        """Get conversation history for a chat"""
        if chat_id not in self.conversations:
            return []
        
        messages = self.conversations[chat_id]
        
        if max_messages:
            messages = messages[-max_messages:]
        
        return messages

    def get_recent_context(
        self,
        chat_id: int,
        max_messages: int = 10
    ) -> str:
        """Get recent conversation context as formatted string"""
        messages = self.get_conversation_history(chat_id, max_messages)
        
        if not messages:
            return "No previous conversation history."
        
        context_lines = []
        context_lines.append("Recent conversation history:")
        
        for msg in messages:
            timestamp_str = msg.timestamp.strftime("%H:%M")
            
            if msg.role == "user":
                if msg.message_type == "photo":
                    content_preview = f"[Shared a photo] {msg.content}" if msg.content else "[Shared a photo]"
                elif msg.message_type == "link":
                    content_preview = f"[Shared links] {msg.content[:100]}..."
                elif msg.message_type == "document":
                    content_preview = f"[Shared document] {msg.content[:100]}..."
                else:
                    content_preview = msg.content[:150] + ("..." if len(msg.content) > 150 else "")
                
                context_lines.append(f"{timestamp_str} {msg.user_name}: {content_preview}")
            else:
                content_preview = msg.content[:150] + ("..." if len(msg.content) > 150 else "")
                context_lines.append(f"{timestamp_str} TravelBot: {content_preview}")
        
        return "\n".join(context_lines)

    def get_travel_context_summary(self, chat_id: int) -> Dict[str, Any]:
        """Extract travel-related context from conversation history"""
        messages = self.get_conversation_history(chat_id)
        
        context = {
            "destinations_mentioned": set(),
            "travel_dates": [],
            "budget_mentions": [],
            "group_size": None,
            "preferences": [],
            "photos_shared": 0,
            "links_shared": 0,
        }
        
        for msg in messages:
            if msg.role == "user":
                content_lower = msg.content.lower()
                
                # Count media shared
                if msg.message_type == "photo":
                    context["photos_shared"] += 1
                elif msg.message_type == "link":
                    context["links_shared"] += 1
                
                # Extract travel-related keywords (basic implementation)
                # This could be enhanced with NLP libraries
                if any(word in content_lower for word in ['visit', 'go to', 'trip to', 'travel to']):
                    # Basic destination extraction - could be improved
                    words = msg.content.split()
                    for i, word in enumerate(words):
                        if word.lower() in ['to', 'visit', 'go']:
                            if i + 1 < len(words):
                                potential_destination = words[i + 1].strip('.,!?')
                                if len(potential_destination) > 2:
                                    context["destinations_mentioned"].add(potential_destination)
                
                # Extract budget mentions
                if any(word in content_lower for word in ['$', 'dollar', 'budget', 'cost', 'price']):
                    context["budget_mentions"].append(msg.content)
                
                # Extract group size mentions
                if any(word in content_lower for word in ['we', 'us', 'group', 'family', 'friends']):
                    context["group_size"] = "group"
                elif any(word in content_lower for word in ['i ', 'me ', 'my ', 'solo']):
                    if context["group_size"] != "group":  # Don't overwrite group info
                        context["group_size"] = "solo"
        
        # Convert set to list for JSON serialization
        context["destinations_mentioned"] = list(context["destinations_mentioned"])
        
        return context

    def clear_conversation(self, chat_id: int) -> None:
        """Clear conversation history for a chat"""
        if chat_id in self.conversations:
            del self.conversations[chat_id]
            logger.info(f"Cleared conversation history for chat {chat_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        total_messages = sum(len(messages) for messages in self.conversations.values())
        
        return {
            "active_chats": len(self.conversations),
            "total_messages": total_messages,
            "avg_messages_per_chat": total_messages / len(self.conversations) if self.conversations else 0,
            "max_messages_per_chat": self.max_messages_per_chat,
            "max_age_hours": self.max_age_hours
        }


# Global conversation memory instance
conversation_memory = ConversationMemory()