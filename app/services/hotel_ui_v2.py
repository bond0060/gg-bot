#!/usr/bin/env python3
"""
酒店推荐UI服务 V2 - 支持7条业务规则的新UI
"""

import logging
from datetime import date, timedelta
from typing import Dict, Any, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class HotelUIV2:
    """酒店推荐UI服务 V2"""
    
    def __init__(self):
        self.currency_symbols = {
            "CNY": "¥",
            "JPY": "¥", 
            "USD": "$",
            "EUR": "€",
            "GBP": "£"
        }
    
    def get_keyboard(self, keyboard_type: str, slots: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """根据类型获取键盘"""
        if keyboard_type == "main_menu":
            return self._get_main_menu_keyboard()
        elif keyboard_type == "essential_info":
            return self._get_essential_info_keyboard()
        elif keyboard_type == "first_recommendation":
            return self._get_first_recommendation_keyboard()
        elif keyboard_type == "conditional_recommendation":
            return self._get_conditional_recommendation_keyboard()
        elif keyboard_type == "priced_recommendation":
            return self._get_priced_recommendation_keyboard()
        elif keyboard_type == "children_confirmation":
            return self._get_children_confirmation_keyboard()
        elif keyboard_type == "city_selection":
            return self._get_city_selection_keyboard()
        elif keyboard_type == "budget_selection":
            return self._get_budget_selection_keyboard()
        elif keyboard_type == "location_selection":
            return self._get_location_selection_keyboard()
        elif keyboard_type == "tags_selection":
            return self._get_tags_selection_keyboard()
        elif keyboard_type == "date_selection":
            return self._get_date_selection_keyboard()
        elif keyboard_type == "party_selection":
            return self._get_party_selection_keyboard(slots)
        elif keyboard_type == "extras_selection":
            return self._get_extras_selection_keyboard()
        else:
            return self._get_main_menu_keyboard()
    
    def _get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """主菜单键盘"""
        keyboard = [
            [InlineKeyboardButton("🏙 城市", callback_data="set_city")],
            [InlineKeyboardButton("💰 预算/晚", callback_data="set_budget"),
             InlineKeyboardButton("📍 位置/地标", callback_data="set_location")],
            [InlineKeyboardButton("✨ 其他要求", callback_data="set_tags"),
             InlineKeyboardButton("📅 入住日期", callback_data="set_checkin")],
            [InlineKeyboardButton("📅 退房日期", callback_data="set_checkout"),
             InlineKeyboardButton("👪 人数", callback_data="set_party")],
            [InlineKeyboardButton("⚙️ 更多筛选", callback_data="set_extras"),
             InlineKeyboardButton("✅ 生成推荐", callback_data="generate_recommendation")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_essential_info_keyboard(self) -> InlineKeyboardMarkup:
        """基本信息键盘"""
        keyboard = [
            [InlineKeyboardButton("🏙 城市", callback_data="set_city")],
            [InlineKeyboardButton("💰 预算/晚", callback_data="set_budget")],
            [InlineKeyboardButton("📍 位置/地标", callback_data="set_location")],
            [InlineKeyboardButton("✨ 其他要求", callback_data="set_tags")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_first_recommendation_keyboard(self) -> InlineKeyboardMarkup:
        """首次推荐键盘"""
        keyboard = [
            [InlineKeyboardButton("💰 预算/晚", callback_data="set_budget"),
             InlineKeyboardButton("📍 位置/地标", callback_data="set_location")],
            [InlineKeyboardButton("✨ 其他要求", callback_data="set_tags"),
             InlineKeyboardButton("✅ 生成推荐", callback_data="generate_recommendation")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_conditional_recommendation_keyboard(self) -> InlineKeyboardMarkup:
        """条件充分推荐键盘"""
        keyboard = [
            [InlineKeyboardButton("📅 入住日期", callback_data="set_checkin"),
             InlineKeyboardButton("📅 退房日期", callback_data="set_checkout")],
            [InlineKeyboardButton("👪 成人/儿童", callback_data="set_party"),
             InlineKeyboardButton("✅ 生成推荐", callback_data="generate_recommendation")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_priced_recommendation_keyboard(self) -> InlineKeyboardMarkup:
        """含价推荐键盘"""
        keyboard = [
            [InlineKeyboardButton("⚙️ 更多筛选", callback_data="set_extras"),
             InlineKeyboardButton("🔄 刷新推荐", callback_data="generate_recommendation")],
            [InlineKeyboardButton("🏨 换酒店", callback_data="change_hotels"),
             InlineKeyboardButton("📊 比较酒店", callback_data="compare_hotels")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_children_confirmation_keyboard(self) -> InlineKeyboardMarkup:
        """儿童确认键盘"""
        keyboard = [
            [InlineKeyboardButton("👶 有儿童", callback_data="confirm_children_yes"),
             InlineKeyboardButton("🚫 无儿童", callback_data="confirm_children_no")],
            [InlineKeyboardButton("➕ 添加儿童年龄", callback_data="add_child_age")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_city_selection_keyboard(self) -> InlineKeyboardMarkup:
        """城市选择键盘"""
        keyboard = [
            [InlineKeyboardButton("东京", callback_data="set_city:东京"),
             InlineKeyboardButton("大阪", callback_data="set_city:大阪"),
             InlineKeyboardButton("京都", callback_data="set_city:京都")],
            [InlineKeyboardButton("上海", callback_data="set_city:上海"),
             InlineKeyboardButton("北京", callback_data="set_city:北京"),
             InlineKeyboardButton("深圳", callback_data="set_city:深圳")],
            [InlineKeyboardButton("曼谷", callback_data="set_city:曼谷"),
             InlineKeyboardButton("新加坡", callback_data="set_city:新加坡"),
             InlineKeyboardButton("香港", callback_data="set_city:香港")],
            [InlineKeyboardButton("✍️ 自定义", callback_data="custom_city"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_budget_selection_keyboard(self) -> InlineKeyboardMarkup:
        """预算选择键盘"""
        keyboard = [
            [InlineKeyboardButton("¥500-800", callback_data="set_budget:500-800"),
             InlineKeyboardButton("¥800-1200", callback_data="set_budget:800-1200")],
            [InlineKeyboardButton("¥1200-2000", callback_data="set_budget:1200-2000"),
             InlineKeyboardButton("¥2000-3000", callback_data="set_budget:2000-3000")],
            [InlineKeyboardButton("¥3000-5000", callback_data="set_budget:3000-5000"),
             InlineKeyboardButton("¥5000+", callback_data="set_budget:5000+")],
            [InlineKeyboardButton("✍️ 自定义", callback_data="custom_budget"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_location_selection_keyboard(self) -> InlineKeyboardMarkup:
        """位置选择键盘"""
        keyboard = [
            [InlineKeyboardButton("新宿", callback_data="set_location:新宿"),
             InlineKeyboardButton("涩谷", callback_data="set_location:涩谷"),
             InlineKeyboardButton("银座", callback_data="set_location:银座")],
            [InlineKeyboardButton("东京塔附近", callback_data="set_location:东京塔附近"),
             InlineKeyboardButton("浅草寺附近", callback_data="set_location:浅草寺附近"),
             InlineKeyboardButton("迪士尼附近", callback_data="set_location:迪士尼附近")],
            [InlineKeyboardButton("近地铁站", callback_data="set_location:近地铁站"),
             InlineKeyboardButton("市中心", callback_data="set_location:市中心")],
            [InlineKeyboardButton("✍️ 自定义", callback_data="custom_location"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_tags_selection_keyboard(self) -> InlineKeyboardMarkup:
        """标签选择键盘"""
        keyboard = [
            [InlineKeyboardButton("网红酒店", callback_data="toggle_tag:网红"),
             InlineKeyboardButton("奢华酒店", callback_data="toggle_tag:奢华")],
            [InlineKeyboardButton("新开业", callback_data="toggle_tag:新开业"),
             InlineKeyboardButton("近地铁", callback_data="toggle_tag:近地铁")],
            [InlineKeyboardButton("东京塔景", callback_data="toggle_tag:东京塔景"),
             InlineKeyboardButton("海景", callback_data="toggle_tag:海景")],
            [InlineKeyboardButton("家庭友好", callback_data="toggle_tag:家庭友好"),
             InlineKeyboardButton("商务酒店", callback_data="toggle_tag:商务酒店")],
            [InlineKeyboardButton("✅ 确认", callback_data="confirm_tags"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_date_selection_keyboard(self) -> InlineKeyboardMarkup:
        """日期选择键盘"""
        today = date.today()
        keyboard = []
        
        # 未来14天的日期
        for i in range(14):
            d = today + timedelta(days=i)
            if i % 3 == 0:
                keyboard.append([])
            keyboard[-1].append(InlineKeyboardButton(
                d.strftime("%m/%d"), 
                callback_data=f"set_checkin:{d.isoformat()}"
            ))
        
        keyboard.append([InlineKeyboardButton("⬅️ 返回", callback_data="back_main")])
        return InlineKeyboardMarkup(keyboard)
    
    def _get_party_selection_keyboard(self, slots: Dict[str, Any] = None) -> InlineKeyboardMarkup:
        """人数选择键盘"""
        if not slots:
            slots = {"adults": 2, "children": [], "rooms": 1}
        
        adults = slots.get("adults", 2)
        children_count = len(slots.get("children", []))
        rooms = slots.get("rooms", 1)
        
        keyboard = [
            [InlineKeyboardButton("成人 -", callback_data="set_adults:-"),
             InlineKeyboardButton(f"成人 {adults}", callback_data="adults_display"),
             InlineKeyboardButton("成人 +", callback_data="set_adults:+")],
            [InlineKeyboardButton("儿童 -", callback_data="remove_child"),
             InlineKeyboardButton(f"儿童 {children_count}", callback_data="children_display"),
             InlineKeyboardButton("儿童 +", callback_data="add_child")],
            [InlineKeyboardButton("房间 -", callback_data="set_rooms:-"),
             InlineKeyboardButton(f"房间 {rooms}", callback_data="rooms_display"),
             InlineKeyboardButton("房间 +", callback_data="set_rooms:+")],
            [InlineKeyboardButton("✅ 确认", callback_data="confirm_party"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_extras_selection_keyboard(self) -> InlineKeyboardMarkup:
        """更多筛选键盘"""
        keyboard = [
            [InlineKeyboardButton("设施", callback_data="set_facilities"),
             InlineKeyboardButton("景观", callback_data="set_view")],
            [InlineKeyboardButton("品牌", callback_data="set_brand"),
             InlineKeyboardButton("开业年限", callback_data="set_open_after")],
            [InlineKeyboardButton("✅ 确认", callback_data="confirm_extras"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_facilities_keyboard(self) -> InlineKeyboardMarkup:
        """设施选择键盘"""
        keyboard = [
            [InlineKeyboardButton("泳池", callback_data="toggle_facility:泳池"),
             InlineKeyboardButton("温泉", callback_data="toggle_facility:温泉")],
            [InlineKeyboardButton("健身房", callback_data="toggle_facility:健身房"),
             InlineKeyboardButton("行政酒廊", callback_data="toggle_facility:行政酒廊")],
            [InlineKeyboardButton("水疗中心", callback_data="toggle_facility:水疗中心"),
             InlineKeyboardButton("商务中心", callback_data="toggle_facility:商务中心")],
            [InlineKeyboardButton("✅ 确认", callback_data="confirm_facilities"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_extras")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_view_keyboard(self) -> InlineKeyboardMarkup:
        """景观选择键盘"""
        keyboard = [
            [InlineKeyboardButton("地标景观", callback_data="set_view:地标"),
             InlineKeyboardButton("海景", callback_data="set_view:海景")],
            [InlineKeyboardButton("城景", callback_data="set_view:城景"),
             InlineKeyboardButton("山景", callback_data="set_view:山景")],
            [InlineKeyboardButton("花园景观", callback_data="set_view:花园"),
             InlineKeyboardButton("无特殊要求", callback_data="set_view:无")],
            [InlineKeyboardButton("✅ 确认", callback_data="confirm_view"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_extras")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_brand_keyboard(self) -> InlineKeyboardMarkup:
        """品牌选择键盘"""
        keyboard = [
            [InlineKeyboardButton("安缦", callback_data="set_brand:安缦"),
             InlineKeyboardButton("四季", callback_data="set_brand:四季")],
            [InlineKeyboardButton("丽思卡尔顿", callback_data="set_brand:丽思卡尔顿"),
             InlineKeyboardButton("希尔顿", callback_data="set_brand:希尔顿")],
            [InlineKeyboardButton("万豪", callback_data="set_brand:万豪"),
             InlineKeyboardButton("洲际", callback_data="set_brand:洲际")],
            [InlineKeyboardButton("✅ 确认", callback_data="confirm_brand"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_extras")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_open_after_keyboard(self) -> InlineKeyboardMarkup:
        """开业年限选择键盘"""
        keyboard = [
            [InlineKeyboardButton("2024年后", callback_data="set_open_after:2024"),
             InlineKeyboardButton("2022年后", callback_data="set_open_after:2022")],
            [InlineKeyboardButton("2020年后", callback_data="set_open_after:2020"),
             InlineKeyboardButton("2018年后", callback_data="set_open_after:2018")],
            [InlineKeyboardButton("无要求", callback_data="set_open_after:无"),
             InlineKeyboardButton("✍️ 自定义", callback_data="custom_open_after")],
            [InlineKeyboardButton("✅ 确认", callback_data="confirm_open_after"),
             InlineKeyboardButton("⬅️ 返回", callback_data="back_extras")]
        ]
        return InlineKeyboardMarkup(keyboard)

# 全局实例
hotel_ui_v2 = HotelUIV2()
