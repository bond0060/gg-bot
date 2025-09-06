#!/usr/bin/env python3
"""
酒店推荐状态机 - 实现7条业务规则
"""

import logging
from typing import Dict, Any, Tuple
from app.services.hotel_slots_model import HotelSlotsModel

logger = logging.getLogger(__name__)

class HotelStateMachine:
    """酒店推荐状态机"""
    
    def __init__(self):
        self.slots = HotelSlotsModel()
    
    def process_message(self, message: str, callback_data: str = None) -> Tuple[str, str, Dict[str, Any]]:
        """
        处理消息并返回状态、回复文案、按钮数据
        返回: (state, message, keyboard_data)
        """
        try:
            # 处理回调数据
            if callback_data:
                # 检查是否是特殊按钮（需要显示子菜单）
                if callback_data in ["set_city", "set_budget", "set_location", "set_tags", "set_checkin", "set_checkout", "set_party", "set_extras"]:
                    return self._handle_special_button(callback_data)
                else:
                    self._handle_callback(callback_data)
            
            # 处理文本消息
            if message:
                self._handle_text_message(message)
            
            # 获取当前状态
            current_state = self.slots.get_state()
            logger.info(f"Current state: {current_state}")
            
            # 根据状态返回相应的回复
            return self._get_state_response(current_state)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "S0", "抱歉，处理您的请求时出现了错误。请重试。", {}
    
    def _handle_special_button(self, callback_data: str) -> Tuple[str, str, Dict[str, Any]]:
        """处理特殊按钮（需要显示子菜单）"""
        try:
            import time
            current_info = self.slots.get_summary()
            timestamp = int(time.time() * 1000) % 10000  # 获取时间戳后4位
            
            if callback_data == "set_city":
                message = f"🏙 **选择城市**\n\n当前信息：{current_info}\n\n请选择您要去的城市：\n\n⏰ {timestamp}"
                keyboard_data = {"type": "city_selection"}
            elif callback_data == "set_budget":
                message = f"💰 **选择预算**\n\n当前信息：{current_info}\n\n请选择您的每晚预算范围：\n\n⏰ {timestamp}"
                keyboard_data = {"type": "budget_selection"}
            elif callback_data == "set_location":
                message = f"📍 **选择位置**\n\n当前信息：{current_info}\n\n请选择您希望的位置/地标：\n\n⏰ {timestamp}"
                keyboard_data = {"type": "location_selection"}
            elif callback_data == "set_tags":
                message = f"✨ **其他要求**\n\n当前信息：{current_info}\n\n请选择您的其他要求：\n\n⏰ {timestamp}"
                keyboard_data = {"type": "tags_selection"}
            elif callback_data == "set_checkin":
                message = f"📅 **入住日期**\n\n当前信息：{current_info}\n\n请选择您的入住日期：\n\n⏰ {timestamp}"
                keyboard_data = {"type": "date_selection"}
            elif callback_data == "set_checkout":
                message = f"📅 **退房日期**\n\n当前信息：{current_info}\n\n请选择您的退房日期：\n\n⏰ {timestamp}"
                keyboard_data = {"type": "date_selection"}
            elif callback_data == "set_party":
                message = f"👪 **设置人数**\n\n当前信息：{current_info}\n\n请设置同行人数：\n\n⏰ {timestamp}"
                keyboard_data = {"type": "party_selection"}
            elif callback_data == "set_extras":
                message = f"⚙️ **更多筛选**\n\n当前信息：{current_info}\n\n请选择更多筛选条件：\n\n⏰ {timestamp}"
                keyboard_data = {"type": "extras_selection"}
            else:
                message = f"请选择：\n\n当前信息：{current_info}\n\n⏰ {timestamp}"
                keyboard_data = {"type": "main_menu"}
            
            return "S0", message, keyboard_data
            
        except Exception as e:
            logger.error(f"Error handling special button {callback_data}: {e}")
            return "S0", "抱歉，处理您的请求时出现了错误。请重试。", {}
    
    def _handle_callback(self, callback_data: str):
        """处理回调数据"""
        try:
            if callback_data.startswith("set_city:"):
                city = callback_data.split(":", 1)[1]
                self.slots.update_slot("city", city)
            
            elif callback_data.startswith("set_budget:"):
                budget = callback_data.split(":", 1)[1]
                self.slots.update_slot("budget_per_night", budget)
            
            elif callback_data.startswith("set_location:"):
                location = callback_data.split(":", 1)[1]
                self.slots.update_slot("location", location)
            
            elif callback_data.startswith("toggle_tag:"):
                tag = callback_data.split(":", 1)[1]
                self.slots.toggle_tag(tag)
            
            elif callback_data.startswith("set_checkin:"):
                check_in = callback_data.split(":", 1)[1]
                self.slots.update_slot("check_in", check_in)
            
            elif callback_data.startswith("set_checkout:"):
                check_out = callback_data.split(":", 1)[1]
                self.slots.update_slot("check_out", check_out)
            
            elif callback_data.startswith("set_adults:"):
                operation = callback_data.split(":", 1)[1]
                current = self.slots.slots.get("adults", 0) or 0
                if operation == "+":
                    self.slots.update_slot("adults", current + 1)
                elif operation == "-" and current > 1:
                    self.slots.update_slot("adults", current - 1)
            
            elif callback_data.startswith("set_child_age:"):
                age = int(callback_data.split(":", 1)[1])
                self.slots.add_child(age)
            
            elif callback_data.startswith("remove_child_age:"):
                age = int(callback_data.split(":", 1)[1])
                self.slots.remove_child(age)
            
            elif callback_data.startswith("set_rooms:"):
                operation = callback_data.split(":", 1)[1]
                current = self.slots.slots.get("rooms", 1)
                if operation == "+":
                    self.slots.update_slot("rooms", current + 1)
                elif operation == "-" and current > 1:
                    self.slots.update_slot("rooms", current - 1)
            
            elif callback_data.startswith("toggle_facility:"):
                facility = callback_data.split(":", 1)[1]
                facilities = self.slots.slots["extras"]["facilities"]
                if facility in facilities:
                    facilities.remove(facility)
                else:
                    facilities.append(facility)
            
            elif callback_data.startswith("set_view:"):
                view = callback_data.split(":", 1)[1]
                self.slots.update_extras("view", view)
            
            elif callback_data.startswith("set_open_after:"):
                year = int(callback_data.split(":", 1)[1])
                self.slots.update_extras("open_after_year", year)
            
            elif callback_data.startswith("set_brand:"):
                brand = callback_data.split(":", 1)[1]
                self.slots.update_extras("brand", brand)
            
            elif callback_data == "confirm_children_no":
                self.slots.update_slot("consent_children", True)
            
            elif callback_data == "confirm_children_yes":
                self.slots.update_slot("consent_children", True)
            
            elif callback_data == "generate_recommendation":
                # 生成推荐
                pass
            
        except Exception as e:
            logger.error(f"Error handling callback {callback_data}: {e}")
    
    def _handle_text_message(self, message: str):
        """处理文本消息"""
        try:
            # 简单的文本解析逻辑
            message_lower = message.lower()
            
            # 检测城市
            if any(keyword in message_lower for keyword in ["东京", "tokyo", "大阪", "osaka", "京都", "kyoto"]):
                if "东京" in message_lower or "tokyo" in message_lower:
                    self.slots.update_slot("city", "东京")
                elif "大阪" in message_lower or "osaka" in message_lower:
                    self.slots.update_slot("city", "大阪")
                elif "京都" in message_lower or "kyoto" in message_lower:
                    self.slots.update_slot("city", "京都")
            
            # 检测预算
            import re
            budget_pattern = r'(\d+)[-~](\d+)|(\d+)\s*万|(\d+)\s*千'
            budget_match = re.search(budget_pattern, message)
            if budget_match:
                if budget_match.group(1) and budget_match.group(2):
                    budget = f"{budget_match.group(1)}-{budget_match.group(2)}"
                elif budget_match.group(3):
                    budget = f"{int(budget_match.group(3)) * 10000}"
                elif budget_match.group(4):
                    budget = f"{int(budget_match.group(4)) * 1000}"
                self.slots.update_slot("budget_per_night", budget)
            
            # 检测标签
            tags = []
            if any(keyword in message_lower for keyword in ["网红", "网红酒店", "ins", "instagram"]):
                tags.append("网红")
            if any(keyword in message_lower for keyword in ["奢华", "豪华", "luxury", "高端"]):
                tags.append("奢华")
            if any(keyword in message_lower for keyword in ["新开业", "新开", "新酒店"]):
                tags.append("新开业")
            if any(keyword in message_lower for keyword in ["近地铁", "地铁", "交通便利"]):
                tags.append("近地铁")
            
            for tag in tags:
                if tag not in self.slots.slots["tags"]:
                    self.slots.slots["tags"].append(tag)
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
    
    def _get_state_response(self, state: str) -> Tuple[str, str, Dict[str, Any]]:
        """根据状态返回相应的回复"""
        if state == "S0":
            return self._get_s0_response()
        elif state == "S1":
            return self._get_s1_response()
        elif state == "S2":
            return self._get_s2_response()
        elif state == "S4":
            return self._get_s4_response()
        elif state == "S6":
            return self._get_s6_response()
        else:
            return self._get_s0_response()
    
    def _get_s0_response(self) -> Tuple[str, str, Dict[str, Any]]:
        """S0: INIT - 新对话或/start"""
        message = f"""🏨 **酒店推荐助手**

当前信息：{self.slots.get_summary()}

为了给出合适的酒店推荐，请先告诉我：
• 你要住的城市
• 你的每晚预算（当地货币范围）

也可以顺便说一下是否有其他要求（如"网红/奢华/地标附近"等）。

👇点击下方按钮填写信息"""
        
        keyboard_data = {
            "type": "main_menu",
            "buttons": [
                ["🏙 城市", "set_city"],
                ["💰 预算/晚", "set_budget"],
                ["📍 位置/地标", "set_location"],
                ["✨ 其他要求", "set_tags"],
                ["📅 入住日期", "set_checkin"],
                ["📅 退房日期", "set_checkout"],
                ["👪 人数", "set_party"],
                ["⚙️ 更多筛选", "set_extras"]
            ]
        }
        
        return "S0", message, keyboard_data
    
    def _get_s1_response(self) -> Tuple[str, str, Dict[str, Any]]:
        """S1: 采集城市与预算（必需）"""
        current_info = self.slots.get_summary()
        
        # 根据已有信息调整提示
        if self.slots.slots["city"]:
            message = f"""📝 **完善预算信息**

当前信息：{current_info}

✅ 已选择城市：{self.slots.slots["city"]}
❌ 还需要：每晚预算（当地货币范围）

请告诉我您的预算范围，例如：
• ¥500-1000（人民币）
• $100-200（美元）
• €80-150（欧元）

也可以顺便说一下是否有其他要求（如"网红/奢华/地标附近"等）。

👇点击下方按钮填写"""
        else:
            message = f"""📝 **完善基本信息**

当前信息：{current_info}

为了给出合适的酒店推荐，请先告诉我：
• 你要住的城市
• 你的每晚预算（当地货币范围）

也可以顺便说一下是否有其他要求（如"网红/奢华/地标附近"等）。

👇点击下方按钮填写"""
        
        keyboard_data = {
            "type": "essential_info",
            "buttons": [
                ["🏙 城市", "set_city"],
                ["💰 预算/晚", "set_budget"],
                ["📍 位置/地标", "set_location"],
                ["✨ 其他要求", "set_tags"]
            ]
        }
        
        return "S1", message, keyboard_data
    
    def _get_s2_response(self) -> Tuple[str, str, Dict[str, Any]]:
        """S2: 首次推荐（不带价格）"""
        # 这里应该调用推荐引擎
        recommendations = self._get_recommendations_without_price()
        
        message = f"""🎯 **初步推荐**（不含价格）

当前信息：{self.slots.get_summary()}

我先按你给的信息做了初步筛选，看看这几家对不对味：

{recommendations}

你可以继续补充：预算/位置/其他要求

👇点击下方按钮完善信息"""
        
        keyboard_data = {
            "type": "first_recommendation",
            "buttons": [
                ["💰 预算/晚", "set_budget"],
                ["📍 位置/地标", "set_location"],
                ["✨ 其他要求", "set_tags"],
                ["✅ 生成推荐", "generate_recommendation"]
            ]
        }
        
        return "S2", message, keyboard_data
    
    def _get_s4_response(self) -> Tuple[str, str, Dict[str, Any]]:
        """S4: 条件充分（城市+预算+位置）→ 推荐 & 引导日期/人数"""
        recommendations = self._get_recommendations_without_price()
        
        message = f"""🏨 **推荐酒店**（暂不含价格）

当前信息：{self.slots.get_summary()}

这几家符合你的城市、预算和位置偏好：

{recommendations}

为了给出房型与价格，请补充 入住/退房日期 和 随行人数（成人/儿童及年龄）。

👇点击下方按钮完善信息"""
        
        keyboard_data = {
            "type": "conditional_recommendation",
            "buttons": [
                ["📅 入住日期", "set_checkin"],
                ["📅 退房日期", "set_checkout"],
                ["👪 成人/儿童", "set_party"],
                ["✅ 生成推荐", "generate_recommendation"]
            ]
        }
        
        return "S4", message, keyboard_data
    
    def _get_s6_response(self) -> Tuple[str, str, Dict[str, Any]]:
        """S6: 含价推荐（已知日期+人数）"""
        # 检查是否需要儿童信息确认
        if self.slots.needs_children_info():
            return self._get_children_confirmation_response()
        
        recommendations = self._get_recommendations_with_price()
        
        message = f"""💰 **推荐酒店**（含房型与价格）

当前信息：{self.slots.get_summary()}

根据你的日期与人数，推荐以下可入住的房型与价格：

{recommendations}

需要更进一步筛选吗（设施/景观/开业年限等）？

👇点击下方按钮"""
        
        keyboard_data = {
            "type": "priced_recommendation",
            "buttons": [
                ["⚙️ 更多筛选", "set_extras"],
                ["🔄 刷新推荐", "generate_recommendation"],
                ["🏨 换酒店", "change_hotels"]
            ]
        }
        
        return "S6", message, keyboard_data
    
    def _get_children_confirmation_response(self) -> Tuple[str, str, Dict[str, Any]]:
        """儿童信息确认"""
        message = f"""👶 **确认儿童信息**

当前信息：{self.slots.get_summary()}

需要确认一下是否有儿童同行？如果有，请告诉我每个孩子的年龄，我会只呈现允许该年龄段入住的房型与价格。

👇请选择"""
        
        keyboard_data = {
            "type": "children_confirmation",
            "buttons": [
                ["👶 有儿童", "confirm_children_yes"],
                ["🚫 无儿童", "confirm_children_no"],
                ["➕ 添加儿童年龄", "add_child_age"]
            ]
        }
        
        return "S6", message, keyboard_data
    
    def _get_recommendations_without_price(self) -> str:
        """获取不含价格的推荐"""
        # 这里应该调用实际的推荐引擎
        return """- **东京安缦酒店 (Aman Tokyo)**
- TripAdvisor评分: 4.8/5
- Price Range: Not available
- Highlights: 奢华体验, 东京塔景, 新开业, 近地铁

- **东京湾喜来登酒店 (Sheraton Grande Tokyo Bay)**
- TripAdvisor评分: 4.4/5
- Price Range: Not available
- Highlights: 家庭友好, 近迪士尼, 泳池设施"""
    
    def _get_recommendations_with_price(self) -> str:
        """获取含价格的推荐"""
        # 这里应该调用实际的推荐引擎，包含价格和房型信息
        return """- **东京安缦酒店 (Aman Tokyo)**
- TripAdvisor评分: 4.8/5
- Price Range: ¥22,000–28,000 per night（含税/含早/可取消）
- Highlights: 家庭房可用, 接受5岁以上儿童, 近地铁, 地标景观

- **东京湾喜来登酒店 (Sheraton Grande Tokyo Bay)**
- TripAdvisor评分: 4.4/5
- Price Range: ¥18,000–25,000 per night（含税/含早/可取消）
- Highlights: 家庭房可用, 接受所有年龄儿童, 近迪士尼, 泳池设施"""

# 全局实例
hotel_state_machine = HotelStateMachine()
