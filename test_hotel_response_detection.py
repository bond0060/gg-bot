#!/usr/bin/env python3
"""Test hotel response detection logic"""

def test_hotel_response_detection():
    """Test hotel response detection for various response patterns"""
    
    # Test cases - different user questions but all with hotel responses
    test_cases = [
        # User question, AI response, Expected result
        ("换3家", "这里推荐3家酒店：1. 阿玛尼酒店 2. 布尔吉酒店 3. 万豪酒店", True),
        ("有什么好玩的", "推荐几个景点和酒店：1. 故宫 2. 希尔顿酒店 3. 长城", True),
        ("天气怎么样", "今天天气很好，顺便推荐几家酒店：1. 万豪酒店 2. 凯悦酒店", True),
        ("帮我规划行程", "好的，这里有个3天行程，包括住宿：1. 丽思卡尔顿酒店 2. 四季酒店", True),
        ("推荐餐厅", "推荐几家餐厅和酒店：1. 米其林餐厅 2. 香格里拉酒店", True),
        ("机票价格", "机票价格是1000元，住宿推荐：1. 洲际酒店 2. 威斯汀酒店", True),
        ("普通聊天", "今天天气不错，适合出去走走", False),
        ("景点介绍", "这个景点很漂亮，有很多历史建筑", False),
        ("餐厅推荐", "推荐几家好吃的餐厅：1. 川菜馆 2. 粤菜馆", False),
        ("航班信息", "航班信息如下：CA123 北京-上海 10:00-12:00", False),
    ]
    
    hotel_response_keywords = ["酒店", "hotel", "住宿", "宾馆", "旅馆", "resort", "boutique", "accommodation", "lodging", "inn", "suite", "lodge"]
    
    print("Testing hotel response detection logic:")
    print("=" * 60)
    
    for user_question, ai_response, expected in test_cases:
        is_hotel_response = any(keyword in ai_response.lower() for keyword in hotel_response_keywords)
        
        status = "✅ HOTEL RESPONSE" if is_hotel_response else "❌ NOT HOTEL"
        correct = "✅ CORRECT" if is_hotel_response == expected else "❌ WRONG"
        
        print(f"User: '{user_question}'")
        print(f"AI Response: '{ai_response[:50]}...'")
        print(f"Detection: {status} | Expected: {expected} | {correct}")
        print("-" * 50)

if __name__ == "__main__":
    test_hotel_response_detection()
