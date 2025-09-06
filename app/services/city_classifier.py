#!/usr/bin/env python3
"""City classification service based on hotel data mapping"""

import json
import os
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class CityClassifier:
    """City classifier based on hotel count data"""
    
    def __init__(self):
        self.classification_data = self._load_classification_data()
    
    def _load_classification_data(self) -> Dict:
        """Load city classification data from JSON file"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_file = os.path.join(current_dir, '..', 'data', 'city_classification.json')
            
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded city classification data with {len(data.get('A_class_cities', {}).get('cities', {}))} A-class cities")
            return data
        except Exception as e:
            logger.error(f"Error loading city classification data: {e}")
            return self._get_fallback_data()
    
    def _get_fallback_data(self) -> Dict:
        """Fallback data if JSON file cannot be loaded"""
        return {
            "A_class_cities": {"cities": {}},
            "B_class_cities": {"cities": {}},
            "C_class_cities": {"cities": {}},
            "fallback_rules": {
                "default_tier": "C",
                "message": "该城市酒店数量有限，以下是可行的3-5家推荐"
            }
        }
    
    def classify_city(self, city_name: str) -> Tuple[str, Dict]:
        """
        Classify a city into A, B, or C tier based on hotel data
        
        Args:
            city_name: Name of the city to classify
            
        Returns:
            Tuple of (tier, city_info)
        """
        city_name_lower = city_name.lower().strip()
        
        # Search through all city categories
        for tier in ['A_class_cities', 'B_class_cities', 'C_class_cities']:
            cities = self.classification_data.get(tier, {}).get('cities', {})
            
            for city_key, city_info in cities.items():
                # Check exact match
                if city_name_lower == city_key.lower():
                    return city_info['tier'], city_info
                
                # Check keywords
                keywords = city_info.get('keywords', [])
                if any(city_name_lower == keyword.lower() for keyword in keywords):
                    return city_info['tier'], city_info
        
        # Fallback for unknown cities
        fallback_rules = self.classification_data.get('fallback_rules', {})
        default_tier = fallback_rules.get('default_tier', 'C')
        
        logger.info(f"City '{city_name}' not found in classification data, using fallback tier: {default_tier}")
        
        return default_tier, {
            'hotel_count': 0,
            'tier': default_tier,
            'keywords': [city_name_lower],
            'is_fallback': True
        }
    
    def get_city_info(self, city_name: str) -> Dict:
        """
        Get detailed information about a city
        
        Args:
            city_name: Name of the city
            
        Returns:
            Dictionary with city information
        """
        tier, city_info = self.classify_city(city_name)
        return city_info
    
    def get_hotel_count(self, city_name: str) -> int:
        """
        Get hotel count for a city
        
        Args:
            city_name: Name of the city
            
        Returns:
            Number of hotels in the city
        """
        city_info = self.get_city_info(city_name)
        return city_info.get('hotel_count', 0)
    
    def should_collect_preferences(self, city_name: str, user_message: str) -> bool:
        """
        Determine if preferences should be collected for a city
        
        Args:
            city_name: Name of the city
            user_message: User's message
            
        Returns:
            True if preferences should be collected
        """
        tier, _ = self.classify_city(city_name)
        
        # For A and B class cities, check if user has already provided preferences
        if tier in ["A", "B"]:
            # Check if user message contains preference information
            preference_keywords = [
                "预算", "budget", "价格", "price", "星级", "star", "星级", "rating",
                "位置", "location", "商圈", "district", "品牌", "brand", "万豪", "marriott",
                "希尔顿", "hilton", "凯悦", "hyatt", "洲际", "intercontinental",
                "奢华", "luxury", "豪华", "deluxe", "经济", "economy", "商务", "business",
                "附近", "nearby", "便利", "convenient", "交通", "transport", "市中心", "downtown",
                "机场", "airport", "景点", "attraction", "购物", "shopping", "商业", "commercial"
            ]
            
            # If user message contains preference keywords, don't ask for more info
            if any(keyword in user_message.lower() for keyword in preference_keywords):
                return False
            
            # If user message is very specific (contains hotel names, specific requests)
            specific_keywords = ["推荐", "recommend", "酒店", "hotel", "住宿", "accommodation"]
            if any(keyword in user_message.lower() for keyword in specific_keywords):
                return True
            
            return True
        
        # For C class cities, don't collect preferences
        return False
    
    def build_preference_prompt(self, city_name: str) -> str:
        """
        Build preference collection prompt based on city tier
        
        Args:
            city_name: Name of the city
            
        Returns:
            Preference collection prompt
        """
        tier, city_info = self.classify_city(city_name)
        hotel_count = city_info.get('hotel_count', 0)
        
        if tier == "A":
            return f"""{city_name}的酒店选择非常多（约{hotel_count}家），在给到您具体的推荐酒店之前，请告诉我您对酒店的单晚预算和星级要求，以及对于酒店位置和品牌是否有特别的偏好呢？

请提供以下信息：
• 单晚预算（如：¥500-1000、¥1000-2000等）
• 酒店星级（如：4星、5星等）
• 位置/商圈偏好（如：市中心、机场附近、特定商圈等）
• 酒店品牌偏好（如：万豪、希尔顿、凯悦等，可选）

您也可以选择浏览以下推荐清单：
• 黄金地段酒店清单
• 奢华酒店清单  
• 豪华酒店清单
• 美景酒店清单
• 高性价比酒店清单"""
        
        elif tier == "B":
            return f"""{city_name}有比较多的酒店选择（约{hotel_count}家），在给到您具体的推荐酒店之前，请告诉我您对酒店的单晚预算和星级要求，以及对于酒店位置是否有特别的偏好呢？

请提供以下信息：
• 单晚预算（如：¥300-800、¥800-1500等）
• 酒店星级（如：3星、4星、5星等）
• 位置/商圈偏好（如：市中心、景点附近、交通便利等）

（B类城市可以不用主要问品牌要求，因为可选品牌可能不多）"""
        
        else:  # C class
            fallback_rules = self.classification_data.get('fallback_rules', {})
            message = fallback_rules.get('message', '该城市酒店数量有限，以下是可行的3-5家推荐')
            return f"""{message}"""
    
    def get_city_statistics(self) -> Dict:
        """
        Get statistics about classified cities
        
        Returns:
            Dictionary with city statistics
        """
        stats = {
            'A_class_count': len(self.classification_data.get('A_class_cities', {}).get('cities', {})),
            'B_class_count': len(self.classification_data.get('B_class_cities', {}).get('cities', {})),
            'C_class_count': len(self.classification_data.get('C_class_cities', {}).get('cities', {})),
            'total_cities': 0
        }
        
        stats['total_cities'] = stats['A_class_count'] + stats['B_class_count'] + stats['C_class_count']
        
        return stats

# Global instance
city_classifier = CityClassifier()
