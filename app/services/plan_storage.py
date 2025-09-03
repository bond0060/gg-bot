import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.models.travel_plan import TravelPlan, PlanSummary, PlanUpdate

logger = logging.getLogger(__name__)


class PlanStorage:
    """In-memory storage for travel plans"""
    
    def __init__(self, max_plans_per_chat: int = 10, max_age_days: int = 30):
        self.plans: Dict[str, TravelPlan] = {}  # plan_id -> TravelPlan
        self.chat_plans: Dict[int, List[str]] = {}  # chat_id -> list of plan_ids
        self.max_plans_per_chat = max_plans_per_chat
        self.max_age_days = max_age_days
        
    def save_plan(self, plan: TravelPlan) -> str:
        """Save a travel plan and return its ID"""
        # Generate unique ID if not provided
        if not plan.id:
            plan.id = str(uuid.uuid4())[:8]  # Short unique ID
            
        # Store the plan
        self.plans[plan.id] = plan
        
        # Add to chat's plan list
        if plan.chat_id not in self.chat_plans:
            self.chat_plans[plan.chat_id] = []
        
        self.chat_plans[plan.chat_id].append(plan.id)
        
        # Cleanup old plans for this chat
        self._cleanup_chat_plans(plan.chat_id)
        
        logger.info(f"Saved travel plan {plan.id} for chat {plan.chat_id}")
        return plan.id
    
    def get_plan(self, plan_id: str) -> Optional[TravelPlan]:
        """Get a travel plan by ID"""
        return self.plans.get(plan_id)
    
    def get_chat_plans(self, chat_id: int) -> List[PlanSummary]:
        """Get all plans for a specific chat"""
        if chat_id not in self.chat_plans:
            return []
        
        plan_summaries = []
        for plan_id in self.chat_plans[chat_id]:
            if plan_id in self.plans:
                plan = self.plans[plan_id]
                summary = PlanSummary(
                    id=plan.id,
                    title=plan.title,
                    destination=plan.destination,
                    duration=plan.duration,
                    travel_type=plan.travel_type,
                    budget_level=plan.budget_level,
                    created_at=plan.created_at,
                    created_by=plan.created_by
                )
                plan_summaries.append(summary)
        
        # Sort by creation date (newest first)
        plan_summaries.sort(key=lambda x: x.created_at, reverse=True)
        return plan_summaries
    
    def update_plan(self, plan_update: PlanUpdate) -> bool:
        """Update an existing travel plan"""
        plan = self.plans.get(plan_update.plan_id)
        if not plan:
            return False
        
        # Update specified fields
        for field, value in plan_update.updates.items():
            if hasattr(plan, field):
                setattr(plan, field, value)
        
        # Increment version
        plan.version += 1
        
        logger.info(f"Updated plan {plan_update.plan_id}: {plan_update.update_reason}")
        return True
    
    def delete_plan(self, plan_id: str, chat_id: int) -> bool:
        """Delete a travel plan"""
        if plan_id not in self.plans:
            return False
        
        # Remove from storage
        del self.plans[plan_id]
        
        # Remove from chat's plan list
        if chat_id in self.chat_plans and plan_id in self.chat_plans[chat_id]:
            self.chat_plans[chat_id].remove(plan_id)
        
        logger.info(f"Deleted plan {plan_id} from chat {chat_id}")
        return True
    
    def search_plans(self, chat_id: int, query: str) -> List[PlanSummary]:
        """Search plans by destination or title"""
        chat_plans = self.get_chat_plans(chat_id)
        query_lower = query.lower()
        
        matching_plans = []
        for plan_summary in chat_plans:
            if (query_lower in plan_summary.destination.lower() or 
                query_lower in plan_summary.title.lower()):
                matching_plans.append(plan_summary)
        
        return matching_plans
    
    def get_latest_plan(self, chat_id: int) -> Optional[TravelPlan]:
        """Get the most recently created plan for a chat"""
        summaries = self.get_chat_plans(chat_id)
        if not summaries:
            return None
        
        latest_summary = summaries[0]  # Already sorted by newest first
        return self.get_plan(latest_summary.id)
    
    def _cleanup_chat_plans(self, chat_id: int) -> None:
        """Clean up old plans for a chat based on limits"""
        if chat_id not in self.chat_plans:
            return
        
        plan_ids = self.chat_plans[chat_id]
        
        # Remove plans older than max_age_days
        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
        valid_plan_ids = []
        
        for plan_id in plan_ids:
            if plan_id in self.plans:
                plan = self.plans[plan_id]
                if plan.created_at >= cutoff_date:
                    valid_plan_ids.append(plan_id)
                else:
                    # Remove old plan
                    del self.plans[plan_id]
                    logger.info(f"Removed expired plan {plan_id}")
        
        # Keep only the most recent max_plans_per_chat
        if len(valid_plan_ids) > self.max_plans_per_chat:
            # Sort by creation date to keep newest
            plan_objects = [(pid, self.plans[pid].created_at) for pid in valid_plan_ids if pid in self.plans]
            plan_objects.sort(key=lambda x: x[1], reverse=True)
            
            # Keep only the newest plans
            valid_plan_ids = [pid for pid, _ in plan_objects[:self.max_plans_per_chat]]
            
            # Remove excess plans
            for pid, _ in plan_objects[self.max_plans_per_chat:]:
                if pid in self.plans:
                    del self.plans[pid]
                    logger.info(f"Removed excess plan {pid}")
        
        self.chat_plans[chat_id] = valid_plan_ids
    
    def clear_chat_plans(self, chat_id: int) -> int:
        """Clear all plans for a chat and return count of deleted plans"""
        if chat_id not in self.chat_plans:
            return 0
        
        plan_ids = self.chat_plans[chat_id].copy()
        count = 0
        
        for plan_id in plan_ids:
            if plan_id in self.plans:
                del self.plans[plan_id]
                count += 1
        
        del self.chat_plans[chat_id]
        logger.info(f"Cleared {count} plans for chat {chat_id}")
        return count
    
    def get_stats(self) -> Dict[str, int]:
        """Get storage statistics"""
        total_plans = len(self.plans)
        active_chats = len(self.chat_plans)
        avg_plans_per_chat = total_plans / active_chats if active_chats > 0 else 0
        
        return {
            "total_plans": total_plans,
            "active_chats": active_chats,
            "avg_plans_per_chat": round(avg_plans_per_chat, 2),
            "max_plans_per_chat": self.max_plans_per_chat,
            "max_age_days": self.max_age_days
        }


# Global plan storage instance
plan_storage = PlanStorage()