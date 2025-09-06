#!/usr/bin/env python3
"""
酒店推荐槽位数据模型 - 按照7条业务规则设计
"""

from typing import Dict, Any, List, Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)

class HotelSlotsModel:
    """酒店推荐槽位数据模型"""
    
    def __init__(self):
        self.slots = self._initialize_slots()
    
    def _initialize_slots(self) -> Dict[str, Any]:
        """初始化空槽位"""
        return {
            "city": None,                       # 城市
            "budget_per_night": None,           # 单晚预算（本地货币，区间或上限/下限）
            "location": None,                   # 期望位置/地标/片区（如 "新宿/近东京塔/名站"）
            "tags": [],                         # 风格标签：["网红","奢华","东京塔景","近地铁","新开业",...]
            "check_in": None,                   # YYYY-MM-DD
            "check_out": None,                  # YYYY-MM-DD
            "adults": None,                     # 成人数
            "children": [],                     # 儿童年龄数组，如 [4, 10]
            "rooms": 1,                         # 房间数（可默认 1）
            "extras": {                         # 进一步要求（第5条）
                "facilities": [],               # 设施：["泳池","温泉","健身房","行政酒廊",...]
                "view": None,                   # 景观：["地标","海景","城景","山景"]
                "open_after_year": None,        # 开业/翻新年限阈值，如 2022
                "brand": None                   # 品牌偏好（可选）
            },
            "city_type": None,                  # A/B/C（可选：用于前置提问策略）
            "consent_children": None            # 是否已确认儿童随行信息（true/false）
        }
    
    def update_slot(self, key: str, value: Any) -> bool:
        """更新单个槽位"""
        try:
            if key in self.slots:
                self.slots[key] = value
                logger.info(f"Updated slot {key}: {value}")
                return True
            else:
                logger.warning(f"Unknown slot key: {key}")
                return False
        except Exception as e:
            logger.error(f"Error updating slot {key}: {e}")
            return False
    
    def update_extras(self, key: str, value: Any) -> bool:
        """更新extras中的槽位"""
        try:
            if key in self.slots["extras"]:
                self.slots["extras"][key] = value
                logger.info(f"Updated extras.{key}: {value}")
                return True
            else:
                logger.warning(f"Unknown extras key: {key}")
                return False
        except Exception as e:
            logger.error(f"Error updating extras.{key}: {e}")
            return False
    
    def toggle_tag(self, tag: str) -> bool:
        """切换标签（添加或移除）"""
        try:
            if tag in self.slots["tags"]:
                self.slots["tags"].remove(tag)
                logger.info(f"Removed tag: {tag}")
            else:
                self.slots["tags"].append(tag)
                logger.info(f"Added tag: {tag}")
            return True
        except Exception as e:
            logger.error(f"Error toggling tag {tag}: {e}")
            return False
    
    def add_child(self, age: int) -> bool:
        """添加儿童年龄"""
        try:
            if age not in self.slots["children"]:
                self.slots["children"].append(age)
                self.slots["children"].sort()  # 按年龄排序
                logger.info(f"Added child age: {age}")
            return True
        except Exception as e:
            logger.error(f"Error adding child age {age}: {e}")
            return False
    
    def remove_child(self, age: int) -> bool:
        """移除儿童年龄"""
        try:
            if age in self.slots["children"]:
                self.slots["children"].remove(age)
                logger.info(f"Removed child age: {age}")
            return True
        except Exception as e:
            logger.error(f"Error removing child age {age}: {e}")
            return False
    
    def get_state(self) -> str:
        """根据当前槽位状态判断当前状态"""
        # S0: INIT - 新对话或/start
        if not self.slots["city"]:
            return "S0"
        
        # S1: 采集城市与预算（必需）- 有城市但缺少预算
        if self.slots["city"] and not self.slots["budget_per_night"]:
            return "S1"
        
        # S2: 首次推荐（不带价格）- 有城市且有任一其他信息
        has_other_info = any([
            self.slots["location"],
            self.slots["tags"],
            self.slots["extras"]["brand"],
            self.slots["extras"]["view"]
        ])
        if self.slots["city"] and has_other_info and not all([self.slots["budget_per_night"], self.slots["location"]]):
            return "S2"
        
        # S4: 条件充分（城市+预算+位置）→ 推荐 & 引导日期/人数
        if all([self.slots["city"], self.slots["budget_per_night"], self.slots["location"]]):
            if not all([self.slots["check_in"], self.slots["check_out"], self.slots["adults"] is not None]):
                return "S4"
        
        # S6: 已知日期与人数 → 带房型与价格的推荐
        if all([self.slots["check_in"], self.slots["check_out"], self.slots["adults"] is not None]):
            return "S6"
        
        # 默认返回S0
        return "S0"
    
    def can_recommend(self) -> tuple[bool, str]:
        """判断是否可以推荐，返回(是否可以推荐, 推荐类型)"""
        # 规则1：无城市 → 不推荐
        if not self.slots["city"]:
            return False, "no_city"
        
        # 规则2：有城市 + 任一其他信息 → 可首次推荐（不含价）
        has_other_info = any([
            self.slots["location"],
            self.slots["tags"],
            self.slots["extras"]["brand"],
            self.slots["extras"]["view"]
        ])
        if has_other_info and not all([self.slots["budget_per_night"], self.slots["location"]]):
            return True, "first_recommendation"
        
        # 规则4：有 城市+预算+位置 → 推荐（仍可不含价）
        if all([self.slots["city"], self.slots["budget_per_night"], self.slots["location"]]):
            if not all([self.slots["check_in"], self.slots["check_out"], self.slots["adults"] is not None]):
                return True, "conditional_recommendation"
        
        # 规则6：有日期+人数(+儿童年龄) → 带房型与价格的推荐
        if all([self.slots["check_in"], self.slots["check_out"], self.slots["adults"] is not None]):
            return True, "priced_recommendation"
        
        return False, "insufficient_info"
    
    def needs_children_info(self) -> bool:
        """是否需要儿童信息确认"""
        return (
            self.slots["children"] == [] and 
            self.slots["consent_children"] is not True and
            all([self.slots["check_in"], self.slots["check_out"], self.slots["adults"] is not None])
        )
    
    def get_summary(self) -> str:
        """获取当前槽位摘要"""
        parts = []
        
        if self.slots["city"]:
            parts.append(f"城市：{self.slots['city']}")
        
        if self.slots["budget_per_night"]:
            parts.append(f"预算：{self.slots['budget_per_night']}/晚")
        
        if self.slots["location"]:
            parts.append(f"位置：{self.slots['location']}")
        
        if self.slots["tags"]:
            parts.append(f"标签：{', '.join(self.slots['tags'])}")
        
        if self.slots["check_in"] and self.slots["check_out"]:
            parts.append(f"日期：{self.slots['check_in']} 至 {self.slots['check_out']}")
        
        if self.slots["adults"] is not None:
            adults = self.slots["adults"]
            children = len(self.slots["children"])
            if children > 0:
                parts.append(f"人数：{adults}成人{children}儿童")
            else:
                parts.append(f"人数：{adults}人")
        
        if self.slots["rooms"] > 1:
            parts.append(f"房间：{self.slots['rooms']}间")
        
        return "，".join(parts) if parts else "暂无信息"
    
    def reset(self):
        """重置所有槽位"""
        self.slots = self._initialize_slots()
        logger.info("Reset all slots")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.slots.copy()
    
    def from_dict(self, data: Dict[str, Any]):
        """从字典加载数据"""
        try:
            self.slots.update(data)
            logger.info("Loaded slots from dict")
        except Exception as e:
            logger.error(f"Error loading slots from dict: {e}")

# 全局实例
hotel_slots = HotelSlotsModel()
