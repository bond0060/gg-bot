#!/usr/bin/env python3
"""
酒店推荐UI服务 - 使用Telegram Inline Keyboard
"""

import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class HotelUIService:
    """酒店推荐UI服务，提供Inline Keyboard界面"""
    
    def __init__(self):
        self.currency_symbols = {
            "CNY": "¥",
            "JPY": "¥", 
            "USD": "$",
            "EUR": "€",
            "GBP": "£"
        }
    
    def get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """主菜单键盘"""
        keyboard = [
            [InlineKeyboardButton("🏙 目的地", callback_data="hotel_ui:ask_city")],
            [InlineKeyboardButton("📅 入住日期", callback_data="hotel_ui:ask_checkin"),
             InlineKeyboardButton("🛏 住几晚", callback_data="hotel_ui:ask_nights")],
            [InlineKeyboardButton("💰 预算/晚", callback_data="hotel_ui:ask_budget")],
            [InlineKeyboardButton("👪 同行人数", callback_data="hotel_ui:ask_party")],
            [InlineKeyboardButton("✅ 完成推荐", callback_data="hotel_ui:done")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_quick_dates_keyboard(self, days: int = 14) -> InlineKeyboardMarkup:
        """快速日期选择键盘（未来N天）"""
        today = date.today()
        rows = []
        row = []
        
        for i in range(days):
            d = today + timedelta(days=i)
            row.append(InlineKeyboardButton(
                d.strftime("%m/%d"), 
                callback_data=f"hotel_ui:set_ci:{d.isoformat()}"
            ))
            if len(row) == 5:
                rows.append(row)
                row = []
        
        if row:
            rows.append(row)
        
        rows.append([InlineKeyboardButton("⬅ 返回", callback_data="hotel_ui:back_main")])
        return InlineKeyboardMarkup(rows)
    
    def get_nights_keyboard(self) -> InlineKeyboardMarkup:
        """住宿晚数选择键盘"""
        nights_options = [1, 2, 3, 4, 5, 6, 7, 10, 14]
        rows = []
        row = []
        
        for n in nights_options:
            row.append(InlineKeyboardButton(
                f"{n} 晚", 
                callback_data=f"hotel_ui:set_nights:{n}"
            ))
            if len(row) == 5:
                rows.append(row)
                row = []
        
        if row:
            rows.append(row)
        
        rows.append([InlineKeyboardButton("⬅ 返回", callback_data="hotel_ui:back_main")])
        return InlineKeyboardMarkup(rows)
    
    def get_budget_keyboard(self, currency: str = "CNY") -> InlineKeyboardMarkup:
        """预算选择键盘"""
        symbol = self.currency_symbols.get(currency, "¥")
        
        # 根据货币调整预算选项
        if currency == "JPY":
            options = ["5000-8000", "8000-12000", "12000-20000", "20000-30000", "30000-50000"]
        elif currency == "USD":
            options = ["50-80", "80-120", "120-200", "200-300", "300-500"]
        elif currency == "EUR":
            options = ["50-80", "80-120", "120-200", "200-300", "300-500"]
        else:  # CNY
            options = ["500-800", "800-1200", "1200-2000", "2000-3000", "3000-5000"]
        
        rows = []
        for opt in options:
            rows.append([InlineKeyboardButton(
                f"{symbol}{opt}", 
                callback_data=f"hotel_ui:set_budget:{opt}"
            )])
        
        rows.append([
            InlineKeyboardButton("✍️ 自定义", callback_data="hotel_ui:custom_budget"),
            InlineKeyboardButton("⬅ 返回", callback_data="hotel_ui:back_main")
        ])
        
        return InlineKeyboardMarkup(rows)
    
    def get_party_keyboard(self) -> InlineKeyboardMarkup:
        """同行人数选择键盘"""
        keyboard = [
            [
                InlineKeyboardButton("成人 -", callback_data="hotel_ui:adult:-"),
                InlineKeyboardButton("成人 +", callback_data="hotel_ui:adult:+")
            ],
            [
                InlineKeyboardButton("儿童 -", callback_data="hotel_ui:child:-"),
                InlineKeyboardButton("儿童 +", callback_data="hotel_ui:child:+")
            ],
            [
                InlineKeyboardButton("房间 -", callback_data="hotel_ui:room:-"),
                InlineKeyboardButton("房间 +", callback_data="hotel_ui:room:+")
            ],
            [InlineKeyboardButton("⬅ 返回", callback_data="hotel_ui:back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_summary_text(self, slots: Dict[str, Any]) -> str:
        """生成信息摘要文本"""
        party = slots.get("party", {"adults": 2, "children": 0, "rooms": 1})
        
        text = "📌 当前酒店预订信息：\n\n"
        text += f"🏙 目的地：{slots.get('city', '未设置')}\n"
        text += f"📅 入住：{slots.get('check_in', '未设置')}\n"
        text += f"🛏 住几晚：{slots.get('nights', '未设置')}\n"
        text += f"📅 退房：{slots.get('check_out', '未设置')}\n"
        text += f"💰 预算/晚：{slots.get('budget_range_local', '未设置')}\n"
        text += f"👪 人数：成人{party.get('adults', 2)} 儿童{party.get('children', 0)} 房间{party.get('rooms', 1)}\n"
        
        return text
    
    def get_initial_message(self, slots: Dict[str, Any]) -> str:
        """获取初始消息文本"""
        return (
            "🏨 **酒店推荐助手**\n\n"
            "请使用下方按钮完善您的酒店预订信息，我将为您推荐最合适的酒店！\n\n"
            + self.get_summary_text(slots)
        )
    
    def get_city_input_message(self) -> str:
        """获取城市输入提示消息"""
        return (
            "🏙 **请告诉我目的地城市**\n\n"
            "请输入您想要预订酒店的城市名称，例如：\n"
            "• Tokyo / 东京\n"
            "• 上海\n"
            "• New York\n"
            "• 巴黎\n\n"
            "请直接发送城市名称："
        )
    
    def get_budget_input_message(self) -> str:
        """获取预算输入提示消息"""
        return (
            "💰 **请输入自定义预算**\n\n"
            "请输入每晚预算区间，例如：\n"
            "• ¥1500-2200\n"
            "• 1500-2200\n"
            "• $100-150\n\n"
            "请直接发送预算信息："
        )
    
    def get_completion_message(self, slots: Dict[str, Any]) -> str:
        """获取完成收集信息后的消息"""
        return (
            "✅ **信息收集完成！**\n\n"
            + self.get_summary_text(slots) +
            "\n\n正在为您搜索最合适的酒店推荐..."
        )
    
    def update_slots_from_callback(self, slots: Dict[str, Any], callback_data: str) -> bool:
        """根据回调数据更新slots，返回是否成功更新"""
        try:
            if callback_data.startswith("hotel_ui:set_ci:"):
                # 设置入住日期
                try:
                    check_in = callback_data.split(":", 2)[2]
                    logger.info(f"Setting check_in date: {check_in}")
                    slots["check_in"] = check_in
                    
                    # 如果已设置晚数，自动计算退房日期
                    if slots.get("nights"):
                        ci_date = date.fromisoformat(check_in)
                        co_date = ci_date + timedelta(days=int(slots["nights"]))
                        slots["check_out"] = co_date.isoformat()
                        logger.info(f"Calculated check_out date: {slots['check_out']}")
                    
                    return True
                except Exception as e:
                    logger.error(f"Error setting check-in date: {e}")
                    return False
                
            elif callback_data.startswith("hotel_ui:set_nights:"):
                # 设置住宿晚数
                nights = int(callback_data.split(":", 2)[2])
                slots["nights"] = nights
                
                # 如果已设置入住日期，自动计算退房日期
                if slots.get("check_in"):
                    ci_date = date.fromisoformat(slots["check_in"])
                    co_date = ci_date + timedelta(days=nights)
                    slots["check_out"] = co_date.isoformat()
                
                return True
                
            elif callback_data.startswith("hotel_ui:set_budget:"):
                # 设置预算
                budget = callback_data.split(":", 2)[2]
                slots["budget_range_local"] = budget
                return True
                
            elif callback_data.startswith(("hotel_ui:adult:", "hotel_ui:child:", "hotel_ui:room:")):
                # 调整人数/房间
                parts = callback_data.split(":")
                kind = parts[1]
                operation = parts[2]
                
                if "party" not in slots:
                    slots["party"] = {"adults": 2, "children": 0, "rooms": 1}
                
                if kind == "adult":
                    current = slots["party"]["adults"]
                    slots["party"]["adults"] = max(1, current + (1 if operation == "+" else -1))
                elif kind == "child":
                    current = slots["party"]["children"]
                    slots["party"]["children"] = max(0, current + (1 if operation == "+" else -1))
                elif kind == "room":
                    current = slots["party"]["rooms"]
                    slots["party"]["rooms"] = max(1, current + (1 if operation == "+" else -1))
                
                return True
                
        except Exception as e:
            logger.error(f"Error updating slots from callback {callback_data}: {e}")
            return False
        
        return False
    
    def update_slots_from_text(self, slots: Dict[str, Any], text: str, awaiting: str) -> bool:
        """根据文本输入更新slots，返回是否成功更新"""
        try:
            if awaiting == "city":
                slots["city"] = text.strip()
                return True
            elif awaiting == "budget":
                # 清理货币符号
                budget_text = text.strip().replace("¥", "").replace("$", "").replace("€", "").replace("£", "")
                slots["budget_range_local"] = budget_text
                return True
        except Exception as e:
            logger.error(f"Error updating slots from text {text}: {e}")
            return False
        
        return False
