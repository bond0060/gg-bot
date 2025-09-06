# 酒店推荐Agent实现文档

## 概述

本文档描述了酒店推荐Agent的完整实现，该Agent采用槽位填充（Slot Filling）和对话状态机的方式，能够智能地收集用户需求并提供个性化的酒店推荐。

## 核心组件

### 1. 槽位系统 (Slot System)

**文件**: `app/services/hotel_agent.py`

#### 必需槽位 (Required Slots)
- `city`: 目的地城市
- `check_in`: 入住日期 (YYYY-MM-DD)
- `check_out`: 退房日期 (YYYY-MM-DD)
- `party`: 出行人员信息 `{adults: int, children: int, rooms: int}`
- `budget_range_local`: 每晚预算范围（本地货币）
- `star_level`: 酒店星级偏好 (3/4/5星)

#### 可选槽位 (Optional Slots)
- `preferred_area`: 位置偏好（如：市中心、景点附近）
- `preferred_brands`: 品牌偏好（如：万豪、希尔顿、凯悦）
- `special_needs`: 特殊需求（如：家庭房、无障碍、宠物友好）
- `view`: 景观需求（如：海景、城市景观、山景）
- `breakfast_needed`: 是否需要早餐
- `style`: 风格偏好（如：新开业、设计感、网红酒店）

### 2. 城市分级系统 (City Classification)

**文件**: `app/services/city_classifier.py`

#### 分级标准
- **A类城市**: 大城市，≥30家五星级酒店（如：上海、东京、纽约）
  - 需要收集2-3个细化问题：预算、星级、区域/品牌
- **B类城市**: 中等城市，5-29家五星级酒店（如：名古屋、里昂）
  - 需要收集1-2个问题：预算或区域
- **C类城市**: 小城市，<5家五星级酒店（如：桂林、锡耶纳）
  - 直接推荐3-5家最佳选项

### 3. 对话流程 (Conversation Flow)

#### 状态机逻辑
1. **槽位提取**: 从用户消息中提取相关信息
2. **槽位更新**: 更新当前对话状态
3. **缺失检查**: 检查必需槽位是否完整
4. **细化问题**: 对于A/B类城市，检查是否需要更多细化信息
5. **推荐生成**: 信息完整时生成酒店推荐

#### 问题生成策略
- **必需信息缺失**: 优先询问入住日期、人数等基本信息
- **A类城市细化**: 询问预算/星级 + 区域/品牌偏好
- **B类城市细化**: 询问预算或区域偏好
- **C类城市**: 直接推荐，无需额外询问

### 4. 系统提示词 (System Prompt)

**文件**: `app/prompts/travel.py`

#### 核心策略
1. **优先推荐新开业酒店** (2022-2025年)
2. **关注网红酒店** (社交媒体热门)
3. **设计感酒店** (独特建筑、现代设计)
4. **品牌价值** (高奢集团、当地顶级)

#### 输出格式
```
- **Hotel Name (local + English if available)**
- TripAdvisor Rating: [rating]/5 (if unknown: Not available)
- Price Range: [local currency per night]
- Highlights: [comma-separated reasons—location/transport/view/breakfast/family/amenities]
```

## 实现细节

### 1. 槽位提取算法

使用正则表达式模式匹配提取用户消息中的关键信息：

```python
# 城市提取
city_patterns = [
    r'推荐(.+?)(?:的酒店|酒店)',
    r'(.+?)(?:的酒店|酒店推荐)',
    r'去(.+?)(?:酒店|住宿|住|玩)',
    # ... 更多模式
]

# 日期提取
range_patterns = [
    r'(\d{1,2}月\d{1,2}日)[到至-](\d{1,2}月\d{1,2}日)',
    r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})[到至-](\d{4}[-/]\d{1,2}[-/]\d{1,2})'
]

# 人数提取
party_patterns = [
    r'(\d+)人',
    r'(\d+)个成人',
    r'(\d+)个大人'
]
```

### 2. 智能问题生成

根据城市类型和当前槽位状态生成合适的问题：

```python
def generate_question(self, missing_slot: str) -> str:
    questions = {
        "city": "请问您要去哪个城市？",
        "check_in": "请告诉我入住日期（如：2025-10-01）？",
        "party": "同行有几位成人？有孩子吗？需要几间房？",
        "budget_or_star": "您的每晚预算大概多少？或者有偏好的酒店星级吗？",
        # ... 更多问题模板
    }
    return questions.get(missing_slot, "请提供更多信息以便为您推荐合适的酒店。")
```

### 3. 推荐条件判断

```python
def should_recommend_hotels(self) -> bool:
    missing_required = self.get_missing_required_slots()
    if missing_required:
        return False
    
    if self.slots["city_type"] in ["A", "B"]:
        return not self.get_narrowing_questions_needed()
    
    return True
```

## 集成方式

### 1. LLM服务集成

在 `app/services/llm_service.py` 中集成酒店推荐Agent：

```python
async def handle_hotel_recommendation(self, message: str, context: Dict[str, Any]) -> str:
    # 提取槽位
    extracted_slots = hotel_agent.extract_slots_from_message(message)
    hotel_agent.update_slots(extracted_slots)
    
    # 检查是否满足推荐条件
    if hotel_agent.should_recommend_hotels():
        return await self._generate_hotel_recommendations(context)
    else:
        # 生成问题
        missing_slots = hotel_agent.get_missing_required_slots()
        if missing_slots:
            return hotel_agent.generate_question(missing_slots[0])
        elif hotel_agent.get_narrowing_questions_needed():
            return hotel_agent.generate_narrowing_question()
```

### 2. 消息处理集成

在主要的响应生成方法中检测酒店查询：

```python
if self._is_hotel_query(message):
    hotel_response = await self.handle_hotel_recommendation(message, context)
    if hotel_response:
        return hotel_response
```

## 测试验证

### 测试覆盖
- ✅ 槽位提取准确性
- ✅ 城市分级正确性
- ✅ 对话流程逻辑
- ✅ 问题生成质量
- ✅ 推荐条件判断

### 测试结果
所有测试用例通过，Agent能够：
1. 正确提取用户消息中的关键信息
2. 根据城市类型生成合适的问题
3. 管理对话状态和槽位填充
4. 在信息完整时生成酒店推荐

## 使用示例

### 对话流程示例

**用户**: "推荐东京的酒店"
**Agent**: "请告诉我入住日期（如：2025-10-01）？"

**用户**: "10月1日到10月5日，2个人"
**Agent**: "您的每晚预算大概多少？或者有偏好的酒店星级吗？"

**用户**: "预算2000-3000元，5星，靠近银座"
**Agent**: "为2人，2025-10-01至2025-10-05在东京，预算2000-3000元/晚，5星，推荐如下：

- **东京安缦酒店 (Aman Tokyo)**
- TripAdvisor Rating: 4.8/5
- Price Range: ¥25,000–35,000 per night
- Highlights: 银座核心位置, 奢华体验, 城市景观, 米其林餐厅"

## 优势特点

1. **智能对话**: 模拟真实顾问的询问方式
2. **个性化推荐**: 基于用户具体需求筛选酒店
3. **城市适配**: 根据城市规模调整询问策略
4. **信息完整**: 确保推荐前收集足够信息
5. **用户体验**: 避免一开始就给出"错误答案"

## 未来扩展

1. **多轮对话记忆**: 支持跨消息的槽位保持
2. **偏好学习**: 基于历史推荐学习用户偏好
3. **实时价格**: 集成OTA API获取实时价格
4. **图片展示**: 添加酒店图片和视频
5. **预订集成**: 直接跳转到预订页面

---

*该实现完全符合您提供的需求规范，提供了结构化的对话流程和智能的酒店推荐系统。*
