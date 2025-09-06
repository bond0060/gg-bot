import logging
import re
from typing import Optional, List
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from app.services.llm_service import LLMService
from app.services.conversation_memory import conversation_memory
from app.services.plan_storage import plan_storage
from app.services.follow_up_questions import follow_up_service
from app.services.inline_keyboards import inline_keyboard_service
from app.services.hotel_ui_service import HotelUIService
from app.services.hotel_state_machine import hotel_state_machine
from app.services.hotel_ui_v2 import hotel_ui_v2

logger = logging.getLogger(__name__)


class MessageHandlers:
    def __init__(self):
        self.llm_service = LLMService()
        self.hotel_ui_service = HotelUIService()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with LLM-generated welcome"""
        user_name = update.effective_user.first_name or "User"
        chat_type = update.effective_chat.type
        
        try:
            welcome_message = await self.llm_service.generate_welcome_message(user_name, chat_type)
            await update.message.reply_text(welcome_message)
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            fallback_message = (
                f"🌍 Welcome {user_name}! I'm your AI travel planning assistant. "
                "Let's plan an amazing trip together! ✈️"
            )
            await update.message.reply_text(fallback_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "🤖 *TravelBot Commands & Features:*\n\n"
            "*🗺️ Travel Planning:*\n"
            "/plan <details> - Generate structured travel plan\n"
            "/plans - List all your saved plans\n"
            "/viewplan <ID> - View detailed plan\n"
            "/deleteplan <ID> - Delete a plan\n\n"
            "*💬 Conversation:*\n"
            "/start - Welcome message\n"
            "/help - Show this help message\n"
            "/history - View recent conversation\n"
            "/clear - Clear conversation history\n\n"
            "*🎯 I can help with:*\n"
            "📝 Text messages - Share your travel ideas\n"
            "🔗 Links - Send me travel websites or articles\n"
            "📸 Photos - AI-powered image analysis (menus, destinations)\n"
            "👥 Group chats - Collaborative planning\n"
            "📋 Structured plans - Detailed JSON-based itineraries\n\n"
            "*Example:* `/plan 5 days in Tokyo, budget travel, love food and culture`\n\n"
            "I use AI with conversation memory and structured planning!"
        )
        await update.message.reply_text(help_message, parse_mode="Markdown")

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent conversation history"""
        chat_id = update.effective_chat.id
        user_name = update.effective_user.first_name or "User"
        
        # Get recent context
        recent_context = conversation_memory.get_recent_context(chat_id, max_messages=10)
        
        if recent_context == "No previous conversation history.":
            await update.message.reply_text(
                f"No conversation history found, {user_name}. Start chatting to build our travel planning context!"
            )
        else:
            # Get travel context summary
            travel_context = conversation_memory.get_travel_context_summary(chat_id)
            
            response = f"📋 *Recent Conversation History*\n\n{recent_context}\n\n"
            
            # Add travel context summary if available
            if travel_context["destinations_mentioned"] or travel_context["photos_shared"] > 0:
                response += "🎯 *Travel Context Summary:*\n"
                if travel_context["destinations_mentioned"]:
                    destinations = ", ".join(travel_context["destinations_mentioned"])
                    response += f"• Destinations: {destinations}\n"
                if travel_context["group_size"]:
                    response += f"• Travel type: {travel_context['group_size']}\n"
                if travel_context["photos_shared"] > 0:
                    response += f"• Photos shared: {travel_context['photos_shared']}\n"
                if travel_context["links_shared"] > 0:
                    response += f"• Links shared: {travel_context['links_shared']}\n"
            
            await update.message.reply_text(response, parse_mode="Markdown")

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear conversation history"""
        chat_id = update.effective_chat.id
        user_name = update.effective_user.first_name or "User"
        
        conversation_memory.clear_conversation(chat_id)
        
        await update.message.reply_text(
            f"✅ Conversation history cleared, {user_name}! "
            "We can start fresh with your travel planning. What would you like to explore?"
        )

    async def plan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate a structured travel plan"""
        chat_id = update.effective_chat.id
        user_name = update.effective_user.first_name or "User"
        
        # Get user requirements from command arguments
        user_requirements = " ".join(context.args) if context.args else ""
        
        if not user_requirements:
            await update.message.reply_text(
                f"🗺️ To generate a travel plan, please provide some details!\n\n"
                f"Examples:\n"
                f"• `/plan 5 days in Tokyo, budget travel, love food and culture`\n"
                f"• `/plan weekend trip to Paris for couple, moderate budget`\n"
                f"• `/plan family vacation to Thailand, 1 week, beaches and temples`\n\n"
                f"Or just tell me about your travel ideas and I'll create a plan based on our conversation!"
            )
            return
        
        try:
            # Send "generating" message
            generating_msg = await update.message.reply_text(
                f"🎯 Creating your travel plan, {user_name}... This will take a moment! ✈️"
            )
            
            # Build context for plan generation
            plan_context = {
                "chat_id": chat_id,
                "chat_type": update.effective_chat.type,
                "user_name": user_name
            }
            
            # Generate structured travel plan
            travel_plan = await self.llm_service.generate_structured_travel_plan(
                plan_context, user_requirements
            )
            
            # Delete generating message
            await generating_msg.delete()
            
            # Format and send plan summary
            plan_summary = self._format_plan_summary(travel_plan)
            await update.message.reply_text(plan_summary, parse_mode="Markdown")
            
            # Store plan reference in conversation memory
            conversation_memory.add_assistant_message(
                chat_id=chat_id,
                content=f"Generated travel plan: {travel_plan.title} (ID: {travel_plan.id})",
                message_type="plan_generation",
                metadata={"plan_id": travel_plan.id}
            )
            
        except Exception as e:
            logger.error(f"Error generating travel plan: {e}")
            await update.message.reply_text(
                f"Sorry {user_name}, I encountered an issue generating your travel plan. "
                "Please try again or provide more specific details about your trip!"
            )

    async def plans_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all saved travel plans for this chat"""
        chat_id = update.effective_chat.id
        user_name = update.effective_user.first_name or "User"
        
        # Get all plans for this chat
        plans = plan_storage.get_chat_plans(chat_id)
        
        if not plans:
            await update.message.reply_text(
                f"📋 No travel plans found, {user_name}!\n\n"
                f"Create your first plan with `/plan <your travel ideas>`\n"
                f"Example: `/plan 3 days in Rome, budget travel`"
            )
            return
        
        # Format plans list
        response = f"📋 *Your Travel Plans* ({len(plans)} total)\n\n"
        
        for i, plan in enumerate(plans, 1):
            created_date = plan.created_at.strftime("%b %d")
            response += (
                f"{i}. *{plan.title}*\n"
                f"   📍 {plan.destination} • ⏱️ {plan.duration}\n"
                f"   💰 {plan.budget_level.value} • 👥 {plan.travel_type.value}\n"
                f"   📅 Created {created_date} • 🆔 `{plan.id}`\n\n"
            )
        
        response += f"Use `/viewplan <ID>` to see full details of any plan!"
        
        await update.message.reply_text(response, parse_mode="Markdown")

    async def viewplan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View detailed travel plan by ID"""
        chat_id = update.effective_chat.id
        user_name = update.effective_user.first_name or "User"
        
        if not context.args:
            await update.message.reply_text(
                f"Please specify a plan ID!\n\n"
                f"Usage: `/viewplan <plan_id>`\n"
                f"Use `/plans` to see all your plan IDs."
            )
            return
        
        plan_id = context.args[0]
        travel_plan = plan_storage.get_plan(plan_id)
        
        if not travel_plan or travel_plan.chat_id != chat_id:
            await update.message.reply_text(
                f"Plan `{plan_id}` not found or doesn't belong to this chat.\n"
                f"Use `/plans` to see your available plans."
            )
            return
        
        # Format detailed plan
        detailed_plan = self._format_detailed_plan(travel_plan)
        
        # Split long messages if needed
        if len(detailed_plan) > 4000:
            parts = self._split_long_message(detailed_plan)
            for part in parts:
                await update.message.reply_text(part, parse_mode="Markdown")
        else:
            await update.message.reply_text(detailed_plan, parse_mode="Markdown")

    async def deleteplan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a travel plan"""
        chat_id = update.effective_chat.id
        user_name = update.effective_user.first_name or "User"
        
        if not context.args:
            await update.message.reply_text(
                f"Please specify a plan ID to delete!\n\n"
                f"Usage: `/deleteplan <plan_id>`\n"
                f"Use `/plans` to see all your plan IDs."
            )
            return
        
        plan_id = context.args[0]
        travel_plan = plan_storage.get_plan(plan_id)
        
        if not travel_plan or travel_plan.chat_id != chat_id:
            await update.message.reply_text(
                f"Plan `{plan_id}` not found or doesn't belong to this chat."
            )
            return
        
        # Delete the plan
        success = plan_storage.delete_plan(plan_id, chat_id)
        
        if success:
            await update.message.reply_text(
                f"✅ Deleted travel plan: *{travel_plan.title}*\n"
                f"Plan ID: `{plan_id}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Failed to delete plan `{plan_id}`. Please try again."
            )

    def _format_plan_summary(self, plan) -> str:
        """Format travel plan summary for display"""
        summary = f"🎯 *{plan.title}*\n\n"
        summary += f"📍 *Destination:* {plan.destination}\n"
        summary += f"⏱️ *Duration:* {plan.duration}\n"
        summary += f"👥 *Travel Type:* {plan.travel_type.value.title()}\n"
        summary += f"💰 *Budget Level:* {plan.budget_level.value.title()}\n"
        summary += f"🆔 *Plan ID:* `{plan.id}`\n\n"
        
        summary += f"*Overview:*\n{plan.overview}\n\n"
        
        summary += f"*Budget Estimate:* {plan.total_budget_estimate}\n\n"
        
        # Add first day preview
        if plan.itinerary:
            first_day = plan.itinerary[0]
            # Handle both dict and Pydantic model formats
            if hasattr(first_day, 'theme'):
                theme = first_day.theme or 'Activities'
                activities = first_day.activities or []
            else:
                theme = first_day.get('theme', 'Activities')
                activities = first_day.get('activities', [])
            
            summary += f"*Day 1 Preview - {theme}:*\n"
            
            for i, activity in enumerate(activities[:2], 1):  # Show first 2 activities
                if hasattr(activity, 'name'):
                    activity_name = activity.name or 'Activity'
                    activity_duration = activity.duration or 'TBD'
                else:
                    activity_name = activity.get('name', 'Activity')
                    activity_duration = activity.get('duration', 'TBD')
                    
                summary += f"{i}. {activity_name} ({activity_duration})\n"
                
            if len(activities) > 2:
                summary += f"... and {len(activities) - 2} more activities\n"
            summary += "\n"
        
        summary += f"📋 Use `/viewplan {plan.id}` for complete details\n"
        summary += f"📚 Use `/plans` to see all your plans"
        
        return summary

    def _format_detailed_plan(self, plan) -> str:
        """Format detailed travel plan for display"""
        details = f"🗺️ *{plan.title}*\n"
        details += f"_Plan ID: {plan.id} | Created by {plan.created_by}_\n\n"
        
        details += f"📍 *Destination:* {plan.destination}\n"
        details += f"⏱️ *Duration:* {plan.duration}\n"
        details += f"👥 *Type:* {plan.travel_type.value.title()} ({plan.group_size} people)\n"
        details += f"💰 *Budget:* {plan.budget_level.value.title()} - {plan.total_budget_estimate}\n\n"
        
        details += f"*📖 Overview:*\n{plan.overview}\n\n"
        
        # Accommodations
        if plan.accommodations:
            details += "*🏨 Accommodations:*\n"
            for acc in plan.accommodations[:2]:  # Show first 2
                if hasattr(acc, 'name'):
                    acc_name = acc.name or 'Hotel'
                    acc_type = acc.type or 'hotel'
                    acc_location = acc.location or 'TBD'
                    acc_price = acc.price_range or 'TBD'
                else:
                    acc_name = acc.get('name', 'Hotel')
                    acc_type = acc.get('type', 'hotel')
                    acc_location = acc.get('location', 'TBD')
                    acc_price = acc.get('price_range', 'TBD')
                    
                details += f"• *{acc_name}* ({acc_type})\n"
                details += f"  📍 {acc_location} | 💰 {acc_price}\n"
            details += "\n"
        
        # Itinerary preview
        if plan.itinerary:
            details += "*📅 Itinerary Highlights:*\n"
            for day in plan.itinerary[:3]:  # Show first 3 days
                if hasattr(day, 'day'):
                    day_num = day.day or '?'
                    day_theme = day.theme or 'Activities'
                    activities = day.activities or []
                    daily_cost = day.estimated_cost or 'TBD'
                else:
                    day_num = day.get('day', '?')
                    day_theme = day.get('theme', 'Activities')
                    activities = day.get('activities', [])
                    daily_cost = day.get('estimated_cost', 'TBD')
                
                details += f"*Day {day_num}:* {day_theme}\n"
                
                for activity in activities[:2]:  # Show first 2 activities per day
                    if hasattr(activity, 'name'):
                        activity_name = activity.name or 'Activity'
                        activity_cost = activity.cost or 'TBD'
                    else:
                        activity_name = activity.get('name', 'Activity')
                        activity_cost = activity.get('cost', 'TBD')
                        
                    details += f"• {activity_name} ({activity_cost})\n"
                    
                details += f"💰 Daily estimate: {daily_cost}\n\n"
        
        # Packing and tips
        if plan.packing_list:
            details += "*🎒 Packing Essentials:*\n"
            for item in plan.packing_list[:5]:  # Show first 5 items
                details += f"• {item}\n"
            details += "\n"
        
        if plan.local_tips:
            details += "*💡 Local Tips:*\n"
            for tip in plan.local_tips[:3]:  # Show first 3 tips
                details += f"• {tip}\n"
        
        return details

    def _split_long_message(self, message: str, max_length: int = 4000) -> List[str]:
        """Split long message into multiple parts"""
        if len(message) <= max_length:
            return [message]
        
        parts = []
        current_part = ""
        
        for line in message.split('\n'):
            if len(current_part) + len(line) + 1 > max_length:
                if current_part:
                    parts.append(current_part.strip())
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()  # Answer the callback query
        
        try:
            # Parse callback data
            callback_data = inline_keyboard_service.parse_callback_data(query.data)
            action = callback_data.get("action", "")
            value = callback_data.get("value", "")
            
            user_name = update.effective_user.first_name or "User"
            chat_id = update.effective_chat.id
            
            # Format user's choice as natural text
            user_choice = inline_keyboard_service.format_user_answer(action, value)
            
            # Store user's selection in conversation memory
            conversation_memory.add_user_message(
                chat_id=chat_id,
                content=user_choice,
                message_type="button_selection",
                user_name=user_name,
                metadata={"action": action, "value": value}
            )
            
            # Handle different callback actions
            if action == "plan":
                # User wants to generate a plan
                await self._handle_generate_plan_callback(query, context, user_name, chat_id)
                
            elif action == "more":
                # User wants more information
                await self._handle_more_info_callback(query, context, user_name, chat_id)
                
            elif action in ["dest", "dur", "budg", "grp", "int", "date", "flight", "airline", "airport", "time"]:
                # User answered a specific question
                await self._handle_question_answer_callback(
                    query, context, action, value, user_choice, user_name, chat_id
                )
                
            elif action == "flight_choice":
                # User selected a flight option
                await self._handle_flight_choice_callback(
                    query, context, value, user_choice, user_name, chat_id
                )
            
            elif action == "quick_flight":
                # User clicked quick flight search button
                await self._handle_quick_flight_callback(
                    query, context, user_name, chat_id
                )
            
            elif action == "book_hotel":
                # User clicked book hotel button
                await self._handle_book_hotel_callback(
                    query, context, user_name, chat_id
                )
            
            elif action == "weather":
                # User clicked weather button
                await self._handle_weather_callback(
                    query, context, user_name, chat_id
                )
            
            elif action == "share_loc":
                # User clicked share location button
                await self._handle_share_location_callback(
                    query, context, user_name, chat_id
                )
            
            elif action == "hotel_ui":
                # User clicked hotel UI button
                await self._handle_hotel_ui_callback(
                    query, context, user_name, chat_id
                )
            
            elif action in ["set_city", "set_budget", "set_location", "set_tags", "set_checkin", 
                           "set_checkout", "set_party", "set_extras", "generate_recommendation",
                           "toggle_tag", "set_adults", "set_children", "set_rooms", "toggle_facility",
                           "set_view", "set_open_after", "set_brand", "confirm_children_yes",
                           "confirm_children_no", "add_child_age", "custom_city", "custom_budget",
                           "custom_location", "confirm_tags", "confirm_party", "confirm_extras",
                           "confirm_facilities", "confirm_view", "confirm_brand", "confirm_open_after",
                           "back_main", "back_extras", "change_hotels", "compare_hotels"]:
                # User clicked new hotel UI button
                await self._handle_new_hotel_ui_callback(
                    query, context, user_name, chat_id
                )
            
            # Try to remove the inline keyboard (optional) - but not for hotel_ui
            if action != "hotel_ui":
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except BadRequest:
                    pass  # Message too old or already modified
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.edit_message_text("Sorry, something went wrong processing your selection.")

    async def _handle_generate_plan_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """Handle generate plan button press"""
        
        # Update the message to show we're working
        await query.edit_message_text("🎯 *Generating your travel plan...* ✈️", parse_mode="Markdown")
        
        try:
            # Build context for plan generation
            plan_context = {
                "chat_id": chat_id,
                "chat_type": query.message.chat.type,
                "user_name": user_name
            }
            
            # Generate travel plan based on conversation history
            travel_plan = await self.llm_service.generate_structured_travel_plan(
                plan_context, "Generate plan based on our conversation"
            )
            
            # Format and send plan summary
            plan_summary = self._format_plan_summary(travel_plan)
            await query.edit_message_text(plan_summary, parse_mode="Markdown")
            
            # Store plan reference in conversation memory
            conversation_memory.add_assistant_message(
                chat_id=chat_id,
                content=f"Generated travel plan: {travel_plan.title} (ID: {travel_plan.id})",
                message_type="plan_generation",
                metadata={"plan_id": travel_plan.id}
            )
            
        except Exception as e:
            logger.error(f"Error generating plan from callback: {e}")
            await query.edit_message_text(
                f"Sorry {user_name}, I encountered an issue generating your travel plan. "
                "Please try the `/plan` command with more details!"
            )

    async def _handle_more_info_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """Handle more info button press"""
        
        try:
            # Build context for response generation
            llm_context = {
                "chat_id": chat_id,
                "chat_type": query.message.chat.type,
                "user_name": user_name
            }
            
            # Generate helpful travel information based on conversation
            response = await self.llm_service.generate_travel_response_without_followup(
                "Tell me more helpful travel information", llm_context, "text"
            )
            
            await query.edit_message_text(response, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error generating more info: {e}")
            await query.edit_message_text(
                f"Here are some general travel tips, {user_name}! Feel free to ask me about destinations, "
                "budgets, activities, or anything else travel-related. I'm here to help! 🌍✈️"
            )

    async def _handle_question_answer_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        action: str, 
        value: str, 
        user_choice: str,
        user_name: str, 
        chat_id: int
    ):
        """Handle specific question answer button press"""
        
        try:
            # Build context for response generation
            llm_context = {
                "chat_id": chat_id,
                "chat_type": query.message.chat.type,
                "user_name": user_name
            }
            
            # Generate response acknowledging the user's choice
            acknowledgment_prompt = f"User selected: {user_choice}. Acknowledge this and provide helpful follow-up."
            
            response = await self.llm_service.generate_travel_response_without_followup(
                acknowledgment_prompt, llm_context, "text"
            )
            
            await query.edit_message_text(
                f"Great choice! {response}", 
                parse_mode="Markdown"
            )
            
            # Generate new follow-up questions based on this answer
            questions_data = await follow_up_service.generate_structured_follow_up_questions(
                user_choice, response, llm_context, max_questions=2
            )
            
            # Send new inline keyboard if we have more questions
            if questions_data:
                keyboard = inline_keyboard_service.create_follow_up_keyboard(
                    questions_data, chat_id, llm_context
                )
                
                if keyboard:
                    follow_up_text = "💡 *What else would help me plan your trip?*"
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=follow_up_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                    
        except Exception as e:
            logger.error(f"Error handling question answer: {e}")
            await query.edit_message_text(
                f"Thanks for your choice, {user_name}! Feel free to tell me more about your travel plans."
            )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages with LLM-generated responses"""
        message_text = update.message.text
        chat_type = update.effective_chat.type
        chat_id = update.effective_chat.id
        user_name = update.effective_user.first_name or "User"
        
        # Check if bot is mentioned in the message
        bot_mentioned = self._is_bot_mentioned(update, context)
        
        # Only respond if bot is mentioned (except in private chats)
        if chat_type != "private" and not bot_mentioned:
            logger.info(f"Bot not mentioned in {chat_type} chat, ignoring message")
            return
        
        # Check if message contains URLs
        urls = re.findall(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            message_text
        )
        
        logger.info(f"Received text from {user_name} in {chat_type}: {message_text[:50]}...")
        
        # Determine message type
        message_type = "link" if urls else "text"
        
        # Store user message in conversation memory
        conversation_memory.add_user_message(
            chat_id=chat_id,
            content=message_text,
            message_type=message_type,
            user_name=user_name,
            metadata={"urls": urls} if urls else None
        )
        
        # Build context for LLM
        llm_context = {
            "chat_type": chat_type,
            "chat_id": chat_id,
            "user_name": user_name,
            "urls": urls
        }
        
        # Initialize hotel_slots in context if not exists
        if "hotel_slots" not in llm_context:
            llm_context["hotel_slots"] = {}
        
        # Check if user is in hotel UI input mode
        if "awaiting" in context.user_data:
            awaiting = context.user_data["awaiting"]
            if awaiting in ["city", "budget"]:
                # Handle hotel UI text input
                await self._handle_hotel_ui_text_input(
                    update, context, message_text, awaiting, user_name, chat_id
                )
                return
        
        # Check if this is a hotel-related query and show new hotel UI
        if self._is_hotel_related_message(message_text):
            logger.info(f"Hotel-related message detected: {message_text[:50]}...")
            await self._show_new_hotel_ui_interface(update, context, user_name, chat_id)
            logger.info("New hotel UI interface shown, returning early")
            return
        
        try:
            # Generate response WITHOUT follow-up questions (we'll add them separately)
            response = await self.llm_service.generate_travel_response_without_followup(
                message_text, llm_context, message_type
            )
            
            # Generate structured follow-up questions for inline keyboards
            questions_data = await follow_up_service.generate_structured_follow_up_questions(
                message_text, response, llm_context, max_questions=3
            )
            
            # Create and send inline keyboard if we have questions
            if questions_data:
                keyboard = inline_keyboard_service.create_follow_up_keyboard(
                    questions_data, chat_id, llm_context
                )
                
                if keyboard:
                    # If we have a main response, send it first, then the keyboard
                    if response and response.strip():
                        await update.message.reply_text(response, parse_mode="Markdown")
                        follow_up_text = "💡 *你更倾向哪个方案？*"
                        await update.message.reply_text(
                            follow_up_text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                    else:
                        # If no main response, send keyboard with a default message
                        follow_up_text = "💡 *你更倾向哪个方案？*"
                        await update.message.reply_text(
                            follow_up_text,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
            else:
                # No follow-up questions, check if we should add custom buttons
                if response and response.strip():
                    # Check if response contains hotel recommendations - use influencer hotel response for Instagram buttons
                    # This ensures ANY response with hotel recommendations gets Instagram buttons, regardless of user's question
                    hotel_response_keywords = ["酒店", "hotel", "住宿", "宾馆", "旅馆", "resort", "boutique", "accommodation", "lodging", "inn", "suite", "lodge"]
                    
                    # Check if response contains hotel recommendations
                    is_hotel_response = any(keyword in response.lower() for keyword in hotel_response_keywords)
                    
                    if is_hotel_response:
                        await self._send_influencer_hotel_response(update, response, message_text, chat_id)
                    
                    # Check if this is a general travel query that could benefit from custom buttons
                    elif any(keyword in message_text.lower() for keyword in ["旅行", "旅游", "计划", "推荐", "帮助", "travel", "trip", "plan"]):
                        # Add custom buttons for general travel assistance
                        custom_keyboard = inline_keyboard_service.create_custom_buttons(
                            chat_id, ["quick_flight", "book_hotel", "weather"]
                        )
                        
                        if custom_keyboard:
                            await update.message.reply_text(response, parse_mode="Markdown")
                            await update.message.reply_text(
                                "💡 *我还可以帮您：*",
                                reply_markup=custom_keyboard,
                                parse_mode="Markdown"
                            )
                        else:
                            await update.message.reply_text(response, parse_mode="Markdown")
                    else:
                        await update.message.reply_text(response, parse_mode="Markdown")
                else:
                    # No response generated, send a default message with custom buttons
                    custom_keyboard = inline_keyboard_service.create_custom_buttons(
                        chat_id, ["quick_flight", "book_hotel", "weather"]
                    )
                    
                    if custom_keyboard:
                        await update.message.reply_text(
                            "🤔 我不太确定您想要什么帮助。让我为您提供一些选项：",
                            reply_markup=custom_keyboard
                        )
                    else:
                        await update.message.reply_text(
                            "🤔 我不太确定您想要什么帮助。请告诉我您需要什么，我会尽力协助您！"
                        )
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            fallback_response = (
                f"Thanks for sharing, {user_name}! I'm excited to help you plan an amazing trip. "
                "Could you tell me more about what you have in mind?"
            )
            await update.message.reply_text(fallback_response)

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages with AI vision analysis"""
        user_name = update.effective_user.first_name or "User"
        chat_type = update.effective_chat.type
        chat_id = update.effective_chat.id
        
        # Get photo info
        photo = update.message.photo[-1]  # Get the highest resolution photo
        caption = update.message.caption or ""
        
        logger.info(f"Received photo from {user_name} in {chat_type}")
        
        # Store user message in conversation memory
        conversation_memory.add_user_message(
            chat_id=chat_id,
            content=caption,
            message_type="photo",
            user_name=user_name,
            metadata={"photo_file_id": photo.file_id}
        )
        
        # Build context for LLM
        llm_context = {
            "chat_type": chat_type,
            "chat_id": chat_id,
            "user_name": user_name,
            "caption": caption
        }
        
        try:
            # Send "analyzing" message first
            analyzing_msg = await update.message.reply_text(
                f"📸 Analyzing your photo, {user_name}... This might take a moment!"
            )
            
            # Analyze photo with OpenAI Vision
            response = await self.llm_service.analyze_photo(
                context.bot, photo, caption, llm_context
            )
            
            # Store assistant response
            conversation_memory.add_assistant_message(
                chat_id=chat_id,
                content=response,
                message_type="photo_analysis"
            )
            
            # Delete the "analyzing" message and send the result
            await analyzing_msg.delete()
            await update.message.reply_text(response, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error handling photo message: {e}")
            fallback_response = (
                f"Beautiful photo, {user_name}! 📸 This looks like an amazing destination. "
                "What kind of activities are you interested in there?"
            )
            await update.message.reply_text(fallback_response)

    async def handle_image_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image files sent as documents with AI vision analysis"""
        user_name = update.effective_user.first_name or "User"
        chat_type = update.effective_chat.type
        chat_id = update.effective_chat.id
        document = update.message.document
        
        logger.info(f"Received image document from {user_name} in {chat_type}: {document.file_name}")
        
        # Check if it's an image file
        if not document.mime_type or not document.mime_type.startswith('image/'):
            await update.message.reply_text(
                f"Thanks for the file, {user_name}! However, I can only analyze image files. "
                "Please send photos or image documents for visual analysis."
            )
            return
        
        # Store user message in conversation memory
        conversation_memory.add_user_message(
            chat_id=chat_id,
            content=f"Document: {document.file_name}",
            message_type="document",
            user_name=user_name,
            metadata={
                "file_id": document.file_id,
                "filename": document.file_name,
                "mime_type": document.mime_type
            }
        )
        
        # Build context for LLM  
        llm_context = {
            "chat_type": chat_type,
            "chat_id": chat_id,
            "user_name": user_name,
            "filename": document.file_name
        }
        
        try:
            # Send "analyzing" message first
            analyzing_msg = await update.message.reply_text(
                f"🖼️ Analyzing your image document, {user_name}... This might take a moment!"
            )
            
            # Create a pseudo photo object for document analysis
            # We'll download the document directly
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()
            
            # Use the same photo analysis but with document download
            response = await self.llm_service.analyze_document_image(
                file_bytes, document.file_name, llm_context
            )
            
            # Store assistant response
            conversation_memory.add_assistant_message(
                chat_id=chat_id,
                content=response,
                message_type="document_analysis"
            )
            
            # Delete the "analyzing" message and send the result
            await analyzing_msg.delete()
            await update.message.reply_text(response, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error handling image document: {e}")
            fallback_response = (
                f"Thanks for the image, {user_name}! 🖼️ "
                "This will help me understand your travel preferences better!"
            )
            await update.message.reply_text(fallback_response)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        # Try to send a user-friendly error message
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "Sorry, I encountered an issue processing your request. "
                    "Please try again or contact support if the problem persists."
                )
            except Exception as e:
                logger.error(f"Failed to send error message: {e}")

    async def _handle_flight_choice_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        value: str, 
        user_choice: str,
        user_name: str, 
        chat_id: int
    ):
        """Handle flight option selection callback"""
        
        try:
            # Build context for response generation
            llm_context = {
                "chat_id": chat_id,
                "chat_type": query.message.chat.type,
                "user_name": user_name
            }
            
            # Send notification in group chats
            if query.message.chat.type in ["group", "supergroup"]:
                notification_text = f"👤 用户 {user_name} 选择了 {value}"
                await query.message.reply_text(notification_text)
            
            if value == "都不满意":
                # User is not satisfied with any option
                response = await self.llm_service.generate_travel_response_without_followup(
                    "用户选择了'都不满意'，请提供其他航班选择或建议", llm_context, "text"
                )
                
                await query.edit_message_text(
                    f"我理解您对当前方案不满意，{user_name}！{response}", 
                    parse_mode="Markdown"
                )
            else:
                # User selected a specific flight option
                response = await self.llm_service.generate_travel_response_without_followup(
                    f"用户选择了{value}，请提供该方案的详细信息、预订建议和后续步骤", llm_context, "text"
                )
                
                await query.edit_message_text(
                    f"很好的选择！您选择了{value}。{response}", 
                    parse_mode="Markdown"
                )
            
            # Generate new follow-up questions based on this choice
            questions_data = await follow_up_service.generate_structured_follow_up_questions(
                user_choice, f"User selected {value}", llm_context, max_questions=2
            )
            
            # Send new inline keyboard if we have more questions
            if questions_data:
                keyboard = inline_keyboard_service.create_follow_up_keyboard(
                    questions_data, chat_id, llm_context
                )
                
                if keyboard:
                    follow_up_text = "💡 *还有什么可以帮助您完善旅行计划？*"
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=follow_up_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                    
        except Exception as e:
            logger.error(f"Error handling flight choice: {e}")
            await query.edit_message_text(
                f"谢谢您的选择，{user_name}！如果您需要更多帮助，请随时告诉我。"
            )

    async def _handle_quick_flight_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """Handle quick flight search button"""
        try:
            await query.edit_message_text(
                f"✈️ 好的，{user_name}！我来帮您快速查询航班。\n\n"
                "请告诉我：\n"
                "1. 出发城市和目的地\n"
                "2. 出发日期\n"
                "3. 是否往返（如果是，请提供返程日期）\n\n"
                "例如：'上海到纽约，10月1号出发，10月5号返回'"
            )
        except Exception as e:
            logger.error(f"Error handling quick flight callback: {e}")

    async def _handle_book_hotel_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """Handle book hotel button"""
        try:
            await query.edit_message_text(
                f"🏨 好的，{user_name}！我来帮您预订酒店。\n\n"
                "请告诉我：\n"
                "1. 目的地城市\n"
                "2. 入住和退房日期\n"
                "3. 房间数量和客人数量\n"
                "4. 预算范围（可选）\n\n"
                "例如：'纽约，10月1号到10月5号，2个房间，4个客人'"
            )
        except Exception as e:
            logger.error(f"Error handling book hotel callback: {e}")

    async def _handle_weather_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """Handle weather button"""
        try:
            await query.edit_message_text(
                f"🌤️ 好的，{user_name}！我来帮您查看天气信息。\n\n"
                "请告诉我：\n"
                "1. 您想查询哪个城市的天气？\n"
                "2. 需要查看哪几天的天气？（可选）\n\n"
                "例如：'纽约的天气' 或 '东京10月1号到10月5号的天气'"
            )
        except Exception as e:
            logger.error(f"Error handling weather callback: {e}")

    async def _handle_share_location_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """Handle share location button"""
        try:
            await query.edit_message_text(
                f"📍 好的，{user_name}！\n\n"
                "请分享您的位置，这样我可以：\n"
                "• 为您推荐附近的景点和餐厅\n"
                "• 提供当地的交通信息\n"
                "• 查看您当前位置的天气\n"
                "• 规划从您当前位置出发的路线\n\n"
                "请点击Telegram的'分享位置'按钮发送您的位置。"
            )
        except Exception as e:
            logger.error(f"Error handling share location callback: {e}")

    async def _handle_hotel_ui_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """Handle hotel UI callback queries"""
        try:
            callback_data = query.data
            
            # Initialize hotel slots if not exists
            if "hotel_slots" not in context.user_data:
                context.user_data["hotel_slots"] = {
                    "city": None,
                    "check_in": None,
                    "nights": None,
                    "check_out": None,
                    "budget_range_local": None,
                    "party": {"adults": 2, "children": 0, "rooms": 1},
                }
            
            slots = context.user_data["hotel_slots"]
            
            if callback_data == "hotel_ui:back_main":
                # Return to main menu
                await query.edit_message_text(
                    self.hotel_ui_service.get_initial_message(slots),
                    reply_markup=self.hotel_ui_service.get_main_menu_keyboard()
                )
                return
            
            elif callback_data == "hotel_ui:ask_city":
                # Ask for city input
                await query.edit_message_text(
                    self.hotel_ui_service.get_city_input_message()
                )
                context.user_data["awaiting"] = "city"
                return
            
            elif callback_data == "hotel_ui:ask_checkin":
                # Show date selection
                await query.edit_message_text(
                    "📅 **请选择入住日期**\n\n选择未来14天内的日期：",
                    reply_markup=self.hotel_ui_service.get_quick_dates_keyboard()
                )
                return
            
            elif callback_data == "hotel_ui:ask_nights":
                # Show nights selection
                await query.edit_message_text(
                    "🛏 **请选择住宿晚数**\n\n选择您计划住几晚：",
                    reply_markup=self.hotel_ui_service.get_nights_keyboard()
                )
                return
            
            elif callback_data == "hotel_ui:ask_budget":
                # Show budget selection
                await query.edit_message_text(
                    "💰 **请选择每晚预算**\n\n选择您的预算范围：",
                    reply_markup=self.hotel_ui_service.get_budget_keyboard()
                )
                return
            
            elif callback_data == "hotel_ui:ask_party":
                # Show party selection
                await query.edit_message_text(
                    self.hotel_ui_service.get_summary_text(slots) + 
                    "\n\n👪 **调整同行人数和房间数**\n\n使用下方按钮调整：",
                    reply_markup=self.hotel_ui_service.get_party_keyboard()
                )
                return
            
            elif callback_data == "hotel_ui:custom_budget":
                # Ask for custom budget
                await query.edit_message_text(
                    self.hotel_ui_service.get_budget_input_message()
                )
                context.user_data["awaiting"] = "budget"
                return
            
            elif callback_data == "hotel_ui:done":
                # Complete hotel search
                await query.edit_message_text(
                    self.hotel_ui_service.get_completion_message(slots)
                )
                
                # Generate hotel recommendations using the collected slots
                await self._generate_hotel_recommendations_from_slots(
                    query, context, slots, user_name, chat_id
                )
                return
            
            # Handle slot updates (only if not handled by specific cases above)
            try:
                if self.hotel_ui_service.update_slots_from_callback(slots, callback_data):
                    # Update successful, show updated summary
                    await query.edit_message_text(
                        self.hotel_ui_service.get_summary_text(slots),
                        reply_markup=self.hotel_ui_service.get_main_menu_keyboard()
                    )
                    return
                else:
                    # Update failed, show error message
                    await query.edit_message_text(
                        "❌ 设置失败，请重试。",
                        reply_markup=self.hotel_ui_service.get_main_menu_keyboard()
                    )
                    return
            except Exception as e:
                logger.error(f"Error updating slots from callback: {e}")
                await query.edit_message_text(
                    "❌ 处理您的选择时出现错误，请重试。",
                    reply_markup=self.hotel_ui_service.get_main_menu_keyboard()
                )
                return
            
        except Exception as e:
            logger.error(f"Error handling hotel UI callback: {e}")
            await query.edit_message_text("抱歉，处理您的选择时出现了错误。")

    async def _generate_hotel_recommendations_from_slots(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        slots: dict, 
        user_name: str, 
        chat_id: int
    ):
        """Generate hotel recommendations from collected slots"""
        try:
            logger.info(f"Generating hotel recommendations from slots: {slots}")
            
            # Convert slots to hotel agent format - include all required fields
            from app.services.hotel_agent import hotel_agent
            default_slots = hotel_agent._initialize_slots()
            
            hotel_slots = {
                "city": slots.get("city"),
                "check_in": slots.get("check_in"),
                "check_out": slots.get("check_out"),
                "party": slots.get("party", {"adults": 2, "children": 0, "rooms": 1}),
                "budget_range_local": slots.get("budget_range_local"),
                "city_type": "A",  # Default to A tier
                "star_level": default_slots["star_level"],
                "preferred_area": default_slots["preferred_area"],
                "preferred_brands": default_slots["preferred_brands"],
                "special_needs": default_slots["special_needs"],
                "view": default_slots["view"],
                "breakfast_needed": default_slots["breakfast_needed"],
                "style": default_slots["style"]
            }
            
            logger.info(f"Converted hotel_slots: {hotel_slots}")
            
            # Use hotel agent to generate recommendations
            hotel_agent.slots = hotel_slots
            logger.info(f"Set hotel_agent.slots: {hotel_agent.slots}")
            
            # Generate hotel recommendations
            # The method uses hotel_agent.slots internally, so we just need to pass any context
            logger.info("Calling _generate_hotel_recommendations...")
            recommendations = await self.llm_service._generate_hotel_recommendations({})
            logger.info(f"Generated recommendations: {recommendations[:100] if recommendations else 'None'}...")
            
            if recommendations:
                # Send recommendations with Instagram buttons
                # Create a mock update object for the callback query
                from telegram import Update
                mock_update = Update(update_id=0, callback_query=query)
                await self._send_influencer_hotel_response(
                    mock_update, recommendations, slots.get("city", ""), chat_id
                )
            else:
                await query.edit_message_text(
                    "抱歉，没有找到合适的酒店推荐。请尝试调整您的搜索条件。"
                )
                
        except Exception as e:
            logger.error(f"Error generating hotel recommendations: {e}")
            await query.edit_message_text(
                "抱歉，生成酒店推荐时出现了错误。请稍后重试。"
            )

    async def _handle_hotel_ui_text_input(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        message_text: str, 
        awaiting: str, 
        user_name: str, 
        chat_id: int
    ):
        """Handle hotel UI text input (city, budget)"""
        try:
            # Initialize hotel slots if not exists
            if "hotel_slots" not in context.user_data:
                context.user_data["hotel_slots"] = {
                    "city": None,
                    "check_in": None,
                    "nights": None,
                    "check_out": None,
                    "budget_range_local": None,
                    "party": {"adults": 2, "children": 0, "rooms": 1},
                }
            
            slots = context.user_data["hotel_slots"]
            
            # Update slots based on input
            if self.hotel_ui_service.update_slots_from_text(slots, message_text, awaiting):
                # Clear awaiting state
                context.user_data["awaiting"] = None
                
                # Send confirmation and show updated menu
                await update.message.reply_text(
                    f"✅ 已设置{'目的地' if awaiting == 'city' else '预算'}！\n\n" +
                    self.hotel_ui_service.get_summary_text(slots),
                    reply_markup=self.hotel_ui_service.get_main_menu_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ 输入格式不正确，请重新输入：\n\n" +
                    (self.hotel_ui_service.get_city_input_message() if awaiting == "city" 
                     else self.hotel_ui_service.get_budget_input_message())
                )
                
        except Exception as e:
            logger.error(f"Error handling hotel UI text input: {e}")
            await update.message.reply_text("抱歉，处理您的输入时出现了错误。")

    def _is_hotel_related_message(self, message: str) -> bool:
        """Check if message is hotel-related"""
        hotel_keywords = [
            "酒店", "hotel", "住宿", "宾馆", "旅馆", "resort", "boutique", 
            "accommodation", "lodging", "inn", "suite", "lodge", "预订酒店",
            "推荐酒店", "酒店推荐", "订酒店", "找酒店", "酒店选择"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in hotel_keywords)

    async def _show_hotel_ui_interface(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """Show hotel UI interface"""
        try:
            # Initialize hotel slots if not exists
            if "hotel_slots" not in context.user_data:
                context.user_data["hotel_slots"] = {
                    "city": None,
                    "check_in": None,
                    "nights": None,
                    "check_out": None,
                    "budget_range_local": None,
                    "party": {"adults": 2, "children": 0, "rooms": 1},
                }
            
            slots = context.user_data["hotel_slots"]
            
            # Try to extract city from message
            city = self._extract_city_from_message(update.message.text)
            if city:
                slots["city"] = city
            
            await update.message.reply_text(
                self.hotel_ui_service.get_initial_message(slots),
                reply_markup=self.hotel_ui_service.get_main_menu_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error showing hotel UI interface: {e}")
            await update.message.reply_text("抱歉，显示酒店推荐界面时出现了错误。")
    
    async def _show_new_hotel_ui_interface(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """显示新的酒店UI界面"""
        try:
            # 为每个用户创建独立的状态机实例
            if "hotel_state_machine" not in context.user_data:
                from app.services.hotel_state_machine import HotelStateMachine
                context.user_data["hotel_state_machine"] = HotelStateMachine()
            
            state_machine = context.user_data["hotel_state_machine"]
            
            # 使用新的状态机处理消息
            state, message, keyboard_data = state_machine.process_message(
                update.message.text, None
            )
            
            # 获取键盘
            keyboard = hotel_ui_v2.get_keyboard(keyboard_data["type"])
            
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing new hotel UI interface: {e}")
            await update.message.reply_text("抱歉，显示酒店推荐界面时出现了错误。")
    
    async def _handle_new_hotel_ui_callback(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        user_name: str, 
        chat_id: int
    ):
        """处理新的酒店UI回调"""
        try:
            callback_data = query.data
            logger.info(f"Handling new hotel UI callback: {callback_data}")
            
            # 为每个用户创建独立的状态机实例
            if "hotel_state_machine" not in context.user_data:
                from app.services.hotel_state_machine import HotelStateMachine
                context.user_data["hotel_state_machine"] = HotelStateMachine()
            
            state_machine = context.user_data["hotel_state_machine"]
            
            # 使用新的状态机处理回调
            logger.info(f"Processing callback: {callback_data}")
            state, message, keyboard_data = state_machine.process_message(
                None, callback_data
            )
            
            logger.info(f"State machine returned: state={state}")
            logger.info(f"Message length: {len(message)}, content: {message}")
            logger.info(f"Keyboard data: {keyboard_data}")
            
            # 获取键盘
            keyboard = hotel_ui_v2.get_keyboard(keyboard_data["type"])
            logger.info(f"Generated keyboard type: {keyboard_data['type']}")
            logger.info(f"Keyboard object: {keyboard}")
            logger.info(f"Keyboard inline_keyboard: {keyboard.inline_keyboard if keyboard else 'None'}")
            
            # 检查键盘是否为空
            if keyboard is None:
                logger.error(f"Keyboard is None for type: {keyboard_data['type']}")
                keyboard = hotel_ui_v2.get_keyboard("main_menu")  # 使用主菜单作为备用
                logger.info(f"Using fallback keyboard: {keyboard}")
            
            # 尝试编辑消息，如果失败则发送新消息
            logger.info("Attempting to edit message...")
            try:
                await query.edit_message_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                logger.info("✅ Successfully edited message with keyboard")
            except Exception as edit_error:
                logger.warning(f"❌ Edit message failed: {edit_error}")
                logger.warning(f"Error type: {type(edit_error)}")
                logger.warning(f"Error details: {str(edit_error)}")
                # 编辑失败，发送新消息
                logger.info("Attempting to send new message...")
                try:
                    await query.message.reply_text(
                        message,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                    logger.info("✅ Successfully sent new message with keyboard")
                except Exception as reply_error:
                    logger.error(f"❌ Reply message also failed: {reply_error}")
                    logger.error(f"Reply error type: {type(reply_error)}")
                    # 最后的备用方案：发送简单消息
                    try:
                        await query.message.reply_text(
                            "抱歉，显示预算选择时出现了问题。请重试。",
                            reply_markup=keyboard
                        )
                    except Exception as final_error:
                        logger.error(f"Final fallback also failed: {final_error}")
                        # 最后的最后：只发送文本消息
                        await query.message.reply_text(
                            "抱歉，显示预算选择时出现了问题。请重试。"
                        )
            
        except Exception as e:
            logger.error(f"Error handling new hotel UI callback: {e}")
            # 发送带键盘的错误消息
            try:
                error_keyboard = hotel_ui_v2.get_keyboard("main_menu")
                await query.edit_message_text(
                    "抱歉，处理您的选择时出现了错误。请重试。",
                    reply_markup=error_keyboard
                )
            except:
                await query.message.reply_text("抱歉，处理您的选择时出现了错误。请重试。")

    def _extract_city_from_message(self, message: str) -> str:
        """Extract city name from message"""
        # Simple city extraction - can be enhanced
        cities = ["东京", "Tokyo", "上海", "Shanghai", "北京", "Beijing", "大阪", "Osaka", 
                 "京都", "Kyoto", "箱根", "Hakone", "纽约", "New York", "巴黎", "Paris",
                 "伦敦", "London", "新加坡", "Singapore", "香港", "Hong Kong", "台北", "Taipei"]
        
        for city in cities:
            if city in message:
                return city
        return None

    async def _send_hotel_response_with_media(
        self, 
        update: Update, 
        response: str, 
        message_text: str, 
        chat_id: int
    ):
        """Send hotel response with hotel image and TripAdvisor ratings"""
        try:
            # Extract destination from message
            destination = self._extract_destination_from_message(message_text)
            
            if destination:
                # Get real-time hotel info with TripAdvisor ratings
                realtime_hotel_info = await self.llm_service.get_realtime_hotel_info(destination)
                
                # Send text response first
                await update.message.reply_text(response, parse_mode="Markdown")
                
                # Send real-time hotel info with TripAdvisor ratings if available
                if realtime_hotel_info:
                    await update.message.reply_text(realtime_hotel_info, parse_mode="Markdown")
                
                # Get hotel media URLs for the destination
                hotel_media_urls = self.llm_service.get_hotel_media_urls_for_destination(destination)
                
                # Send hotel image
                await self.llm_service.send_media_with_text(
                    bot=update.get_bot(),
                    chat_id=chat_id,
                    text="",  # No additional text
                    media_type="photo",
                    media_url=hotel_media_urls.get("photo"),
                    caption=f"🏨 *{destination}的精选酒店* - 为您推荐优质住宿！",
                    parse_mode="Markdown"
                )
            else:
                # Fallback to regular text response
                await update.message.reply_text(response, parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Error sending hotel response with media: {e}")
            # Fallback to regular text response
            await update.message.reply_text(response, parse_mode="Markdown")

    def _extract_destination_from_message(self, message_text: str) -> str:
        """Extract destination from message text"""
        message_lower = message_text.lower()
        
        # Map of destination keywords to normalized names
        destination_map = {
            "东京": "tokyo",
            "tokyo": "tokyo",
            "纽约": "new_york", 
            "new york": "new_york",
            "巴黎": "paris",
            "paris": "paris",
            "伦敦": "london",
            "london": "london",
            "大阪": "osaka",
            "osaka": "osaka",
            "京都": "kyoto",
            "kyoto": "kyoto",
            "名古屋": "nagoya",
            "nagoya": "nagoya",
            "首尔": "seoul",
            "seoul": "seoul",
            "新加坡": "singapore",
            "singapore": "singapore",
            "吉隆坡": "kuala_lumpur",
            "kuala lumpur": "kuala_lumpur",
            "曼谷": "bangkok",
            "bangkok": "bangkok",
            "台北": "taipei",
            "taipei": "taipei",
            "香港": "hong_kong",
            "hong kong": "hong_kong",
            "上海": "shanghai",
            "shanghai": "shanghai",
            "北京": "beijing",
            "beijing": "beijing",
            "深圳": "shenzhen",
            "shenzhen": "shenzhen",
            "广州": "guangzhou",
            "guangzhou": "guangzhou",
            "成都": "chengdu",
            "chengdu": "chengdu",
            "杭州": "hangzhou",
            "hangzhou": "hangzhou",
            "南京": "nanjing",
            "nanjing": "nanjing",
            "武汉": "wuhan",
            "wuhan": "wuhan",
            "西安": "xian",
            "xian": "xian",
            "重庆": "chongqing",
            "chongqing": "chongqing",
            "天津": "tianjin",
            "tianjin": "tianjin",
            "青岛": "qingdao",
            "qingdao": "qingdao",
            "大连": "dalian",
            "dalian": "dalian",
            "厦门": "xiamen",
            "xiamen": "xiamen",
            "苏州": "suzhou",
            "suzhou": "suzhou",
            "无锡": "wuxi",
            "wuxi": "wuxi",
            "宁波": "ningbo",
            "ningbo": "ningbo",
            "温州": "wenzhou",
            "wenzhou": "wenzhou",
            "福州": "fuzhou",
            "fuzhou": "fuzhou",
            "济南": "jinan",
            "jinan": "jinan",
            "石家庄": "shijiazhuang",
            "shijiazhuang": "shijiazhuang",
            "太原": "taiyuan",
            "taiyuan": "taiyuan",
            "呼和浩特": "hohhot",
            "hohhot": "hohhot",
            "沈阳": "shenyang",
            "shenyang": "shenyang",
            "长春": "changchun",
            "changchun": "changchun",
            "哈尔滨": "harbin",
            "harbin": "harbin",
            "合肥": "hefei",
            "hefei": "hefei",
            "南昌": "nanchang",
            "nanchang": "nanchang",
            "郑州": "zhengzhou",
            "zhengzhou": "zhengzhou",
            "长沙": "changsha",
            "changsha": "changsha",
            "南宁": "nanning",
            "nanning": "nanning",
            "海口": "haikou",
            "haikou": "haikou",
            "三亚": "sanya",
            "sanya": "sanya",
            "贵阳": "guiyang",
            "guiyang": "guiyang",
            "昆明": "kunming",
            "kunming": "kunming",
            "拉萨": "lhasa",
            "lhasa": "lhasa",
            "兰州": "lanzhou",
            "lanzhou": "lanzhou",
            "西宁": "xining",
            "xining": "xining",
            "银川": "yinchuan",
            "yinchuan": "yinchuan",
            "乌鲁木齐": "urumqi",
            "urumqi": "urumqi",
            "富国岛": "phu_quoc",
            "phu quoc": "phu_quoc",
            "phuquoc": "phu_quoc",
            "巴厘岛": "bali",
            "bali": "bali",
            "巴厘": "bali",
            # 东南亚
            "普吉岛": "phuket",
            "phuket": "phuket",
            "苏梅岛": "koh_samui",
            "koh samui": "koh_samui",
            "清迈": "chiang_mai",
            "chiang mai": "chiang_mai",
            "清莱": "chiang_rai",
            "chiang rai": "chiang_rai",
            "甲米": "krabi",
            "krabi": "krabi",
            "华欣": "hua_hin",
            "hua hin": "hua_hin",
            "芭提雅": "pattaya",
            "pattaya": "pattaya",
            "马尼拉": "manila",
            "manila": "manila",
            "宿务": "cebu",
            "cebu": "cebu",
            "长滩岛": "boracay",
            "boracay": "boracay",
            "河内": "hanoi",
            "hanoi": "hanoi",
            "胡志明市": "ho_chi_minh",
            "ho chi minh": "ho_chi_minh",
            "岘港": "da_nang",
            "da nang": "da_nang",
            "会安": "hoi_an",
            "hoi an": "hoi_an",
            "芽庄": "nha_trang",
            "nha trang": "nha_trang",
            "大叻": "da_lat",
            "da lat": "da_lat",
            "雅加达": "jakarta",
            "jakarta": "jakarta",
            "日惹": "yogyakarta",
            "yogyakarta": "yogyakarta",
            "泗水": "surabaya",
            "surabaya": "surabaya",
            "棉兰": "medan",
            "medan": "medan",
            "槟城": "penang",
            "penang": "penang",
            "马六甲": "malacca",
            "malacca": "malacca",
            "兰卡威": "langkawi",
            "langkawi": "langkawi",
            "沙巴": "sabah",
            "sabah": "sabah",
            "沙捞越": "sarawak",
            "sarawak": "sarawak",
            # 东亚
            "福冈": "fukuoka",
            "fukuoka": "fukuoka",
            "广岛": "hiroshima",
            "hiroshima": "hiroshima",
            "札幌": "sapporo",
            "sapporo": "sapporo",
            "仙台": "sendai",
            "sendai": "sendai",
            "横滨": "yokohama",
            "yokohama": "yokohama",
            "神户": "kobe",
            "kobe": "kobe",
            "奈良": "nara",
            "nara": "nara",
            "冲绳": "okinawa",
            "okinawa": "okinawa",
            "釜山": "busan",
            "busan": "busan",
            "济州岛": "jeju",
            "jeju": "jeju",
            "大邱": "daegu",
            "daegu": "daegu",
            "光州": "gwangju",
            "gwangju": "gwangju",
            "大田": "daejeon",
            "daejeon": "daejeon",
            "仁川": "incheon",
            "incheon": "incheon",
            # 欧洲
            "罗马": "rome",
            "rome": "rome",
            "米兰": "milan",
            "milan": "milan",
            "威尼斯": "venice",
            "venice": "venice",
            "佛罗伦萨": "florence",
            "florence": "florence",
            "那不勒斯": "naples",
            "naples": "naples",
            "巴塞罗那": "barcelona",
            "barcelona": "barcelona",
            "马德里": "madrid",
            "madrid": "madrid",
            "塞维利亚": "seville",
            "seville": "seville",
            "柏林": "berlin",
            "berlin": "berlin",
            "慕尼黑": "munich",
            "munich": "munich",
            "汉堡": "hamburg",
            "hamburg": "hamburg",
            "阿姆斯特丹": "amsterdam",
            "amsterdam": "amsterdam",
            "鹿特丹": "rotterdam",
            "rotterdam": "rotterdam",
            "布鲁塞尔": "brussels",
            "brussels": "brussels",
            "维也纳": "vienna",
            "vienna": "vienna",
            "萨尔茨堡": "salzburg",
            "salzburg": "salzburg",
            "苏黎世": "zurich",
            "zurich": "zurich",
            "日内瓦": "geneva",
            "geneva": "geneva",
            "布拉格": "prague",
            "prague": "prague",
            "布达佩斯": "budapest",
            "budapest": "budapest",
            "华沙": "warsaw",
            "warsaw": "warsaw",
            "斯德哥尔摩": "stockholm",
            "stockholm": "stockholm",
            "哥本哈根": "copenhagen",
            "copenhagen": "copenhagen",
            "奥斯陆": "oslo",
            "oslo": "oslo",
            "赫尔辛基": "helsinki",
            "helsinki": "helsinki",
            "莫斯科": "moscow",
            "moscow": "moscow",
            "圣彼得堡": "st_petersburg",
            "st petersburg": "st_petersburg",
            # 北美
            "洛杉矶": "los_angeles",
            "los angeles": "los_angeles",
            "旧金山": "san_francisco",
            "san francisco": "san_francisco",
            "拉斯维加斯": "las_vegas",
            "las vegas": "las_vegas",
            "迈阿密": "miami",
            "miami": "miami",
            "芝加哥": "chicago",
            "chicago": "chicago",
            "波士顿": "boston",
            "boston": "boston",
            "华盛顿": "washington_dc",
            "washington dc": "washington_dc",
            "西雅图": "seattle",
            "seattle": "seattle",
            "多伦多": "toronto",
            "toronto": "toronto",
            "温哥华": "vancouver",
            "vancouver": "vancouver",
            "蒙特利尔": "montreal",
            "montreal": "montreal",
            # 大洋洲
            "悉尼": "sydney",
            "sydney": "sydney",
            "墨尔本": "melbourne",
            "melbourne": "melbourne",
            "布里斯班": "brisbane",
            "brisbane": "brisbane",
            "珀斯": "perth",
            "perth": "perth",
            "阿德莱德": "adelaide",
            "adelaide": "adelaide",
            "奥克兰": "auckland",
            "auckland": "auckland",
            "惠灵顿": "wellington",
            "wellington": "wellington",
            "基督城": "christchurch",
            "christchurch": "christchurch",
            # 中东
            "迪拜": "dubai",
            "dubai": "dubai",
            "阿布扎比": "abu_dhabi",
            "abu dhabi": "abu_dhabi",
            "多哈": "doha",
            "doha": "doha",
            "科威特": "kuwait",
            "kuwait": "kuwait",
            "利雅得": "riyadh",
            "riyadh": "riyadh",
            "吉达": "jeddah",
            "jeddah": "jeddah",
            "伊斯坦布尔": "istanbul",
            "istanbul": "istanbul",
            "安卡拉": "ankara",
            "ankara": "ankara",
            # 非洲
            "开罗": "cairo",
            "cairo": "cairo",
            "开普敦": "cape_town",
            "cape town": "cape_town",
            "约翰内斯堡": "johannesburg",
            "johannesburg": "johannesburg",
            "内罗毕": "nairobi",
            "nairobi": "nairobi",
            "拉各斯": "lagos",
            "lagos": "lagos",
            # 南美
            "圣保罗": "sao_paulo",
            "sao paulo": "sao_paulo",
            "里约热内卢": "rio_de_janeiro",
            "rio de janeiro": "rio_de_janeiro",
            "布宜诺斯艾利斯": "buenos_aires",
            "buenos aires": "buenos_aires",
            "利马": "lima",
            "lima": "lima",
            "圣地亚哥": "santiago",
            "santiago": "santiago",
            "波哥大": "bogota",
            "bogota": "bogota",
            "加拉加斯": "caracas",
            "caracas": "caracas"
        }
        
        for keyword, normalized_name in destination_map.items():
            if keyword in message_lower:
                return normalized_name
        
        return None

    async def _send_influencer_hotel_response(
        self, 
        update: Update, 
        response: str, 
        message_text: str, 
        chat_id: int
    ):
        """Send influencer hotel response with social media data"""
        try:
            # Extract destination from message
            destination = self._extract_destination_from_message(message_text)
            
            if destination:
                # Get Instagram buttons for hotels
                instagram_buttons = await self.llm_service._get_instagram_buttons_for_hotels(response, destination)
                
                if instagram_buttons:
                    # Create Instagram buttons
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    keyboard = []
                    for button_data in instagram_buttons:
                        keyboard.append([InlineKeyboardButton(
                            button_data["text"], 
                            url=button_data["url"]
                        )])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send text response with Instagram buttons in one message
                    await update.message.reply_text(
                        response,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    # Fallback to regular response
                    await update.message.reply_text(response, parse_mode="Markdown")
            else:
                # Fallback to regular response
                await update.message.reply_text(response, parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Error sending influencer hotel response: {e}")
            # Fallback to regular response
            await update.message.reply_text(response, parse_mode="Markdown")

    def _is_bot_mentioned(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Check if the bot is mentioned in the message
        
        Args:
            update: Telegram update object
            context: Bot context
            
        Returns:
            bool: True if bot is mentioned, False otherwise
        """
        try:
            message = update.message
            if not message:
                return False
            
            # Check for @mentions in the message text
            if message.text:
                # Get bot username
                bot_username = context.bot.username
                if bot_username:
                    # Check for @bot_username in the message
                    if f"@{bot_username}" in message.text:
                        return True
                
                # Check for @all or @everyone (common group mentions)
                if "@all" in message.text.lower() or "@everyone" in message.text.lower():
                    return True
            
            # Check for entities (mentions, hashtags, etc.)
            if message.entities:
                for entity in message.entities:
                    if entity.type == "mention":
                        # Extract the mentioned username
                        mentioned_username = message.text[entity.offset:entity.offset + entity.length]
                        if mentioned_username == f"@{context.bot.username}":
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking bot mention: {e}")
            return False