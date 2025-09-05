#!/usr/bin/env python3
"""Test hotel name extraction"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import LLMService

def test_hotel_extraction():
    """Test hotel name extraction with sample response"""
    
    # Sample response text (similar to what the bot would generate)
    sample_response = """
当然可以，黄天赐！迪拜有很多豪华酒店，以下是几家非常推荐的选择：

1. **阿玛尼酒店（Armani Hotel Dubai）**
   - TripAdvisor评分：4.5/5
   - 价格范围：¥3,000 - ¥5,000每晚
   - 优势：位于哈利法塔内，设计时尚，服务一流，是迪拜最奢华的酒店之一。

2. **布尔吉阿尔阿拉伯酒店（Burj Al Arab Jumeirah）**
   - TripAdvisor评分：4.6/5
   - 价格范围：¥2,500 - ¥4,500每晚
   - 优势：帆船造型的独特建筑，拥有私人海滩和直升机停机坪，是迪拜的地标性酒店。

3. **迪拜万豪酒店（JW Marriott Marquis Hotel Dubai）**
   - TripAdvisor评分：4.4/5
   - 价格范围：¥1,800 - ¥3,200每晚
   - 优势：世界最高的5星级酒店，提供豪华住宿和壮丽城市景观。

这些酒店都非常适合豪华旅行，记得提前预订哦！
"""
    
    # Create LLM service instance
    llm_service = LLMService()
    
    # Test hotel name extraction
    hotel_names = llm_service._extract_hotel_names_from_response(sample_response)
    
    print("Extracted hotel names:")
    for i, name in enumerate(hotel_names, 1):
        print(f"{i}. {name}")
    
    print(f"\nTotal hotels found: {len(hotel_names)}")
    
    # Test Instagram button generation
    destination = "dubai"
    buttons = []
    
    for i, hotel_name in enumerate(hotel_names[:3], 1):
        # Extract English name from hotel name
        english_name = llm_service._extract_english_name_from_hotel(hotel_name)
        
        # Create Instagram search URL
        clean_brand = english_name.lower()
        clean_brand = ''.join(c for c in clean_brand if c.isalnum())
        
        # If brand name is too short/simple, add "hotel"
        if len(clean_brand) <= 6 and 'hotel' not in clean_brand and 'resort' not in clean_brand:
            clean_brand = f"{clean_brand}hotel"
        
        # Get destination hashtag
        destination_hashtag = llm_service._get_destination_hashtag(destination)
        
        # Create button data
        button_text = f"📱 {hotel_name}\n#{clean_brand} #{destination_hashtag}"
        instagram_search_url = f"https://www.instagram.com/explore/tags/{clean_brand}/"
        
        buttons.append({
            "text": button_text,
            "url": instagram_search_url
        })
    
    print(f"\nGenerated {len(buttons)} Instagram buttons:")
    for i, button in enumerate(buttons, 1):
        print(f"{i}. {button['text']}")
        print(f"   URL: {button['url']}")
        print()

if __name__ == "__main__":
    test_hotel_extraction()
