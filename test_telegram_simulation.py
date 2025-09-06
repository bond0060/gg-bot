#!/usr/bin/env python3
"""
模拟Telegram交互的测试脚本
"""
import asyncio
import logging
from datetime import datetime
from app.services.hotel_state_machine import HotelStateMachine
from app.services.hotel_ui_v2 import hotel_ui_v2

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockQuery:
    """模拟Telegram Query对象"""
    def __init__(self, data):
        self.data = data
        self.message = MockMessage()

class MockMessage:
    """模拟Telegram Message对象"""
    def __init__(self):
        self.text = "测试消息"
    
    async def reply_text(self, text, reply_markup=None, parse_mode=None):
        print(f"📤 发送新消息:")
        print(f"   文本: {text[:100]}...")
        print(f"   键盘: {'有' if reply_markup else '无'}")
        print(f"   解析模式: {parse_mode}")
        return True

async def test_telegram_simulation():
    """模拟Telegram交互"""
    print("🤖 开始模拟Telegram交互...")
    
    # 创建状态机实例
    state_machine = HotelStateMachine()
    
    # 模拟用户发送"推荐一下东京的酒店"
    print("\n👤 用户: 推荐一下东京的酒店")
    state, message, keyboard_data = state_machine.process_message("推荐一下东京的酒店", None)
    print(f"🤖 机器人状态: {state}")
    print(f"🤖 机器人消息: {message}")
    print(f"🤖 键盘数据: {keyboard_data}")
    
    # 模拟用户点击预算按钮
    print("\n👤 用户点击: 💰 预算/晚")
    mock_query = MockQuery("set_budget")
    
    # 处理回调
    state, message, keyboard_data = state_machine.process_message(None, "set_budget")
    print(f"🤖 状态机返回:")
    print(f"   状态: {state}")
    print(f"   消息长度: {len(message)}")
    print(f"   消息内容: {message}")
    print(f"   键盘数据: {keyboard_data}")
    
    # 生成键盘
    keyboard = hotel_ui_v2.get_keyboard(keyboard_data["type"])
    print(f"🤖 键盘生成:")
    print(f"   键盘类型: {keyboard_data['type']}")
    print(f"   键盘对象: {'✅' if keyboard else '❌'}")
    if keyboard:
        print(f"   按钮行数: {len(keyboard.inline_keyboard)}")
        for i, row in enumerate(keyboard.inline_keyboard):
            print(f"     行{i}: {[btn.text for btn in row]}")
    
    # 模拟消息编辑失败，发送新消息
    print(f"\n📤 模拟发送新消息:")
    try:
        await mock_query.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        print("✅ 消息发送成功!")
    except Exception as e:
        print(f"❌ 消息发送失败: {e}")
    
    print("\n✅ 模拟测试完成!")

if __name__ == "__main__":
    asyncio.run(test_telegram_simulation())

