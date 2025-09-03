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

logger = logging.getLogger(__name__)


class MessageHandlers:
    def __init__(self):
        self.llm_service = LLMService()

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
            
            # Try to remove the inline keyboard (optional)
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
                # No follow-up questions, just send the main response
                if response and response.strip():
                    await update.message.reply_text(response, parse_mode="Markdown")
                else:
                    # Fallback if no response and no questions
                    fallback_text = f"Thanks for your message, {user_name}! I'm here to help with your travel planning."
                    await update.message.reply_text(fallback_text)
            
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