#!/usr/bin/env python3
"""
测试酒店UI功能的脚本
"""
import asyncio
import logging
from app.services.hotel_state_machine import HotelStateMachine
from app.services.hotel_ui_v2 import hotel_ui_v2

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_hotel_ui():
    """测试酒店UI功能"""
    print("🧪 开始测试酒店UI功能...")
    
    # 创建状态机实例
    state_machine = HotelStateMachine()
    
    # 测试1: 初始状态
    print("\n📝 测试1: 初始状态")
    state, message, keyboard_data = state_machine.process_message("推荐一下东京的酒店", None)
    print(f"状态: {state}")
    print(f"消息: {message}")
    print(f"键盘数据: {keyboard_data}")
    
    # 测试2: 点击预算按钮
    print("\n💰 测试2: 点击预算按钮")
    state, message, keyboard_data = state_machine.process_message(None, "set_budget")
    print(f"状态: {state}")
    print(f"消息: {message}")
    print(f"键盘数据: {keyboard_data}")
    
    # 测试3: 生成预算选择键盘
    print("\n⌨️ 测试3: 生成预算选择键盘")
    keyboard = hotel_ui_v2.get_keyboard("budget_selection")
    print(f"键盘对象: {keyboard}")
    if keyboard:
        print(f"键盘按钮数量: {len(keyboard.inline_keyboard)}")
        for i, row in enumerate(keyboard.inline_keyboard):
            print(f"  行 {i}: {[btn.text for btn in row]}")
    else:
        print("❌ 键盘生成失败!")
    
    # 测试4: 测试其他键盘类型
    print("\n🔍 测试4: 测试其他键盘类型")
    keyboard_types = ["main_menu", "city_selection", "location_selection", "tags_selection"]
    for kt in keyboard_types:
        kb = hotel_ui_v2.get_keyboard(kt)
        print(f"{kt}: {'✅' if kb else '❌'}")
    
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_hotel_ui())

