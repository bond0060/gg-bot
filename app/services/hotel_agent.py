#!/usr/bin/env python3
"""Hotel Recommendation Agent with slot filling and conversation flow"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class HotelAgent:
    """Hotel recommendation agent with structured conversation flow"""
    
    def __init__(self):
        self.slots = self._initialize_slots()
        self.city_classifier = None  # Will be injected
        self.llm_service = None  # Will be injected
        
    def _initialize_slots(self) -> Dict[str, Any]:
        """Initialize empty slots for hotel recommendation"""
        return {
            "city": None,
            "check_in": None,
            "check_out": None,
            "party": {"adults": None, "children": 0, "rooms": 1},
            "budget_range_local": None,
            "star_level": None,
            "preferred_area": None,
            "preferred_brands": None,
            "special_needs": [],
            "view": None,
            "breakfast_needed": None,
            "style": None,
            "city_type": None
        }
    
    def set_dependencies(self, city_classifier, llm_service):
        """Set external dependencies"""
        self.city_classifier = city_classifier
        self.llm_service = llm_service
    
    def extract_slots_from_message(self, user_message: str) -> Dict[str, Any]:
        """Extract slot values from user message"""
        extracted = {}
        message_lower = user_message.lower()
        
        # Extract city - improved patterns
        city_patterns = [
            r'推荐(.+?)(?:的酒店|酒店)',
            r'(.+?)(?:的酒店|酒店推荐)',
            r'去(.+?)(?:酒店|住宿|住|玩)',
            r'在(.+?)(?:酒店|住宿|住)',
            r'(.+?)(?:有什么|有什么好|有什么推荐)',
            r'(.+?)(?:酒店|住宿)'
        ]
        
        for pattern in city_patterns:
            match = re.search(pattern, user_message)
            if match:
                city = match.group(1).strip()
                # Clean up city name
                city = re.sub(r'[的有什么好推荐]', '', city)
                if len(city) > 1 and city not in ['酒店', '住宿', '推荐']:
                    extracted["city"] = city
                    break
        
        # Extract dates - improved patterns
        date_patterns = [
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'(\d{1,2}月\d{1,2}日)',
            r'(\d{1,2}日)'
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, user_message)
            dates.extend(matches)
        
        # Look for date ranges
        range_patterns = [
            r'(\d{1,2}月\d{1,2}日)[到至-](\d{1,2}月\d{1,2}日)',
            r'(\d{1,2}日)[到至-](\d{1,2}日)',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})[到至-](\d{4}[-/]\d{1,2}[-/]\d{1,2})'
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, user_message)
            if match:
                extracted["check_in"] = match.group(1)
                extracted["check_out"] = match.group(2)
                break
        else:
            # If no range found, use individual dates
            if len(dates) >= 2:
                extracted["check_in"] = dates[0]
                extracted["check_out"] = dates[1]
            elif len(dates) == 1:
                extracted["check_in"] = dates[0]
        
        # Extract party information - improved patterns
        party_patterns = [
            r'(\d+)人',
            r'(\d+)个成人',
            r'(\d+)个大人',
            r'(\d+)个房间',
            r'(\d+)间房'
        ]
        
        for pattern in party_patterns:
            match = re.search(pattern, user_message)
            if match:
                num = int(match.group(1))
                if '人' in pattern or '成人' in pattern or '大人' in pattern:
                    extracted["party"] = {"adults": num, "children": 0, "rooms": 1}
                elif '房间' in pattern or '间房' in pattern:
                    if "party" not in extracted:
                        extracted["party"] = {"adults": 2, "children": 0, "rooms": 1}
                    extracted["party"]["rooms"] = num
                break
        
        # Also check for simple number patterns like "2个人"
        simple_party_pattern = r'(\d+)个?人'
        match = re.search(simple_party_pattern, user_message)
        if match and "party" not in extracted:
            num = int(match.group(1))
            extracted["party"] = {"adults": num, "children": 0, "rooms": 1}
        
        # Look for combined party info
        combined_patterns = [
            r'(\d+)个成人[，,]?(\d+)个孩子',
            r'(\d+)个大人[，,]?(\d+)个小孩',
            r'(\d+)人[，,]?(\d+)个孩子'
        ]
        
        for pattern in combined_patterns:
            match = re.search(pattern, user_message)
            if match:
                adults = int(match.group(1))
                children = int(match.group(2))
                extracted["party"] = {"adults": adults, "children": children, "rooms": 1}
                break
        
        # Extract budget
        budget_patterns = [
            r'预算[：:]?\s*(\d+)[-~到至](\d+)',
            r'(\d+)[-~到至](\d+)(?:元|块|¥)',
            r'(\d+)(?:元|块|¥)(?:左右|上下|以内)'
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, user_message)
            if match:
                if len(match.groups()) == 2:
                    extracted["budget_range_local"] = f"{match.group(1)}-{match.group(2)}"
                else:
                    extracted["budget_range_local"] = f"{match.group(1)}左右"
                break
        
        # Extract star level
        star_patterns = [
            r'(\d+)星',
            r'(\d+)\*',
            r'(\d+)星级'
        ]
        
        for pattern in star_patterns:
            match = re.search(pattern, user_message)
            if match:
                extracted["star_level"] = int(match.group(1))
                break
        
        # Extract area preferences
        area_keywords = [
            '市中心', 'downtown', '商业区', '商圈', '景点', 'attraction',
            '机场', 'airport', '车站', 'station', '地铁', 'subway',
            '银座', '新宿', '涩谷', '原宿', '六本木', '丸之内'
        ]
        
        for keyword in area_keywords:
            if keyword in user_message:
                extracted["preferred_area"] = keyword
                break
        
        # Extract brand preferences
        brand_keywords = [
            '万豪', 'marriott', '希尔顿', 'hilton', '凯悦', 'hyatt',
            '洲际', 'intercontinental', '香格里拉', 'shangri-la',
            '丽思卡尔顿', 'ritz-carlton', '四季', 'four seasons'
        ]
        
        for keyword in brand_keywords:
            if keyword in user_message:
                if "preferred_brands" not in extracted:
                    extracted["preferred_brands"] = []
                extracted["preferred_brands"].append(keyword)
        
        # Extract special needs
        special_keywords = [
            '家庭房', 'family', '连通房', 'connecting', '无障碍', 'accessible',
            '宠物', 'pet', '婴儿床', 'crib', '早餐', 'breakfast'
        ]
        
        for keyword in special_keywords:
            if keyword in user_message:
                if "special_needs" not in extracted:
                    extracted["special_needs"] = []
                extracted["special_needs"].append(keyword)
        
        return extracted
    
    def update_slots(self, extracted_slots: Dict[str, Any]) -> None:
        """Update slots with extracted values"""
        for key, value in extracted_slots.items():
            if value is not None:
                if key == "party" and isinstance(value, dict):
                    self.slots["party"].update(value)
                elif key == "special_needs" and isinstance(value, list):
                    self.slots["special_needs"].extend(value)
                elif key == "preferred_brands" and isinstance(value, list):
                    if self.slots["preferred_brands"] is None:
                        self.slots["preferred_brands"] = []
                    self.slots["preferred_brands"].extend(value)
                else:
                    self.slots[key] = value
    
    def get_missing_required_slots(self) -> List[str]:
        """Get list of missing required slots based on city type"""
        if not self.slots["city"]:
            return ["city"]
        
        # Determine city type if not set
        if not self.slots["city_type"] and self.city_classifier:
            tier, _ = self.city_classifier.classify_city(self.slots["city"])
            self.slots["city_type"] = tier
        
        missing = []
        
        # Always required
        if not self.slots["check_in"]:
            missing.append("check_in")
        if not self.slots["check_out"]:
            missing.append("check_out")
        if not self.slots["party"]["adults"]:
            missing.append("party")
        
        # Required for A/B cities
        if self.slots["city_type"] in ["A", "B"]:
            if not self.slots["budget_range_local"] and not self.slots["star_level"]:
                missing.append("budget_or_star")
        
        return missing
    
    def get_narrowing_questions_needed(self) -> bool:
        """Check if narrowing questions are needed for A/B cities"""
        if self.slots["city_type"] not in ["A", "B"]:
            return False
        
        # For A cities: need budget/star + area/brand
        if self.slots["city_type"] == "A":
            has_budget_or_star = self.slots["budget_range_local"] or self.slots["star_level"]
            has_area_or_brand = self.slots["preferred_area"] or self.slots["preferred_brands"]
            return not (has_budget_or_star and has_area_or_brand)
        
        # For B cities: need budget or area
        if self.slots["city_type"] == "B":
            has_budget = self.slots["budget_range_local"] or self.slots["star_level"]
            has_area = self.slots["preferred_area"]
            return not (has_budget or has_area)
        
        return False
    
    def generate_question(self, missing_slot: str) -> str:
        """Generate appropriate question for missing slot"""
        questions = {
            "city": "请问您要去哪个城市？",
            "check_in": "请告诉我入住日期（如：2025-10-01）？",
            "check_out": "请告诉我退房日期（如：2025-10-05）？",
            "party": "同行有几位成人？有孩子吗？需要几间房？",
            "budget_or_star": "您的每晚预算大概多少？或者有偏好的酒店星级吗？",
            "area": "更想住在哪个区域？比如市中心、景点附近、交通便利的地方？",
            "brand": "有特别喜欢的酒店品牌吗？比如万豪、希尔顿、凯悦等？"
        }
        
        return questions.get(missing_slot, "请提供更多信息以便为您推荐合适的酒店。")
    
    def generate_narrowing_question(self) -> str:
        """Generate narrowing question based on city type and current slots"""
        if self.slots["city_type"] == "A":
            if not (self.slots["budget_range_local"] or self.slots["star_level"]):
                return "为便于筛选，请给一个每晚预算范围（当地货币即可，比如 ¥12,000–20,000）？"
            elif not (self.slots["preferred_area"] or self.slots["preferred_brands"]):
                return "更想住在哪片区域/靠近什么地标（如车站、商圈或景点）？"
            else:
                return "还有其他特殊需求吗？比如家庭房、含早餐、带泳池等？"
        
        elif self.slots["city_type"] == "B":
            if not (self.slots["budget_range_local"] or self.slots["star_level"]):
                return "大概预算是多少？或者有偏好的酒店等级吗？"
            elif not self.slots["preferred_area"]:
                return "更靠近车站/市中心/某景点？"
            else:
                return "还有其他特殊需求吗？"
        
        return "请提供更多信息以便为您推荐合适的酒店。"
    
    def should_recommend_hotels(self) -> bool:
        """Check if we have enough information to recommend hotels"""
        missing_required = self.get_missing_required_slots()
        if missing_required:
            return False
        
        if self.slots["city_type"] in ["A", "B"]:
            return not self.get_narrowing_questions_needed()
        
        return True
    
    def build_recommendation_summary(self) -> str:
        """Build summary of user requirements for hotel recommendation"""
        summary_parts = []
        
        # Basic info
        if self.slots["party"]["adults"]:
            adults = self.slots["party"]["adults"]
            children = self.slots["party"]["children"]
            rooms = self.slots["party"]["rooms"]
            
            if children > 0:
                summary_parts.append(f"{adults}成人{children}儿童")
            else:
                summary_parts.append(f"{adults}人")
            
            if rooms > 1:
                summary_parts.append(f"{rooms}间房")
        
        # Dates
        if self.slots["check_in"] and self.slots["check_out"]:
            summary_parts.append(f"{self.slots['check_in']}至{self.slots['check_out']}")
        
        # City
        if self.slots["city"]:
            summary_parts.append(f"在{self.slots['city']}")
        
        # Budget
        if self.slots["budget_range_local"]:
            summary_parts.append(f"预算{self.slots['budget_range_local']}/晚")
        
        # Star level
        if self.slots["star_level"]:
            summary_parts.append(f"{self.slots['star_level']}星")
        
        return "，".join(summary_parts)
    
    def reset_slots(self) -> None:
        """Reset all slots to initial state"""
        self.slots = self._initialize_slots()
    
    def get_slots_summary(self) -> Dict[str, Any]:
        """Get current slots summary for debugging"""
        return {
            "filled_slots": {k: v for k, v in self.slots.items() if v is not None and v != []},
            "missing_required": self.get_missing_required_slots(),
            "needs_narrowing": self.get_narrowing_questions_needed(),
            "ready_to_recommend": self.should_recommend_hotels()
        }

# Global instance
hotel_agent = HotelAgent()
