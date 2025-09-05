#!/usr/bin/env python3
"""Test button text generation"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import LLMService

def test_button_text():
    """Test button text generation with sample hotel names"""
    
    # Sample hotel names
    hotel_names = [
        "**阿玛尼酒店（Armani Hotel Dubai）**",
        "**布尔吉阿尔阿拉伯酒店（Burj Al Arab Jumeirah）**",
        "**迪拜万豪酒店（JW Marriott Marquis Hotel Dubai）**"
    ]
    
    # Create LLM service instance
    llm_service = LLMService()
    
    # Test button generation
    destination = "dubai"
    buttons = []
    
    for i, hotel_name in enumerate(hotel_names, 1):
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
        
        # Create button data with English name only
        button_text = english_name
        instagram_search_url = f"https://www.instagram.com/explore/tags/{clean_brand}/"
        
        buttons.append({
            "text": button_text,
            "url": instagram_search_url
        })
    
    print("Generated Instagram buttons:")
    for i, button in enumerate(buttons, 1):
        print(f"{i}. Button Text: '{button['text']}'")
        print(f"   URL: {button['url']}")
        print()

if __name__ == "__main__":
    test_button_text()
