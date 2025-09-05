#!/usr/bin/env python3
"""Test hotel detection logic"""

def test_hotel_detection():
    """Test hotel detection for various message patterns"""
    
    # Test cases
    test_cases = [
        ("换3家", "这里推荐3家酒店：1. 阿玛尼酒店 2. 布尔吉酒店 3. 万豪酒店"),
        ("推荐几家酒店", "以下是几家推荐酒店：1. 希尔顿酒店 2. 凯悦酒店"),
        ("再推荐一些", "好的，这里还有几家酒店：1. 丽思卡尔顿 2. 四季酒店"),
        ("其他选择", "以下是其他酒店选择：1. 香格里拉 2. 文华东方"),
        ("重新推荐", "重新为您推荐：1. 洲际酒店 2. 威斯汀酒店"),
        ("酒店推荐", "推荐以下酒店：1. 万豪酒店 2. 希尔顿酒店"),
        ("hotel recommendation", "Here are some hotels: 1. Marriott 2. Hilton"),
        ("普通消息", "这是一条普通消息，不包含酒店信息"),
        ("换几家餐厅", "推荐几家餐厅：1. 米其林餐厅 2. 本地餐厅"),
    ]
    
    hotel_keywords = ["酒店", "hotel", "住宿", "宾馆", "旅馆", "resort", "boutique", "accommodation", "lodging", "inn", "suite", "lodge"]
    hotel_recommendation_patterns = ["换", "家", "推荐", "再", "其他", "别的", "重新"]
    
    print("Testing hotel detection logic:")
    print("=" * 50)
    
    for message, response in test_cases:
        is_hotel_query = (
            any(keyword in message.lower() for keyword in hotel_keywords) or
            (any(pattern in message.lower() for pattern in hotel_recommendation_patterns) and 
             any(word in response.lower() for word in ["酒店", "hotel", "住宿", "宾馆", "旅馆", "resort"]))
        )
        
        status = "✅ HOTEL QUERY" if is_hotel_query else "❌ NOT HOTEL"
        print(f"Message: '{message}'")
        print(f"Response: '{response[:50]}...'")
        print(f"Result: {status}")
        print("-" * 30)

if __name__ == "__main__":
    test_hotel_detection()
