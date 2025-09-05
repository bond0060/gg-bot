import logging
import base64
import io
import json
import uuid
from typing import Optional, Dict, Any, List
import re
from datetime import datetime
from openai import AsyncOpenAI
from telegram import Bot, PhotoSize
from app.config.settings import settings
from app.services.conversation_memory import conversation_memory
from app.models.travel_plan import TravelPlan, TravelType, BudgetLevel, ActivityType
from app.services.plan_storage import plan_storage
from app.services.follow_up_questions import follow_up_service
from app.services.flight_search import flight_search_service
from app.services.firecrawl_service import firecrawl_service
from search.google_search import search_web

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.vision_model = "gpt-4o-mini"  # Vision-capable model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature

    async def generate_travel_response(
        self,
        message: str,
        context: Dict[str, Any],
        message_type: str = "text"
    ) -> str:
        """Generate travel-focused response using OpenAI with conversation history"""
        try:
            chat_id = context.get("chat_id")
            
            # Build system prompt for travel planning
            system_prompt = self._build_system_prompt(context, message_type)
            
            # Build conversation messages with history
            messages = self._build_conversation_messages(message, context, message_type, system_prompt)
            
            logger.info(f"Generating LLM response for {message_type} message with {len(messages)-1} history messages")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            generated_response = response.choices[0].message.content.strip()
            logger.info("Successfully generated LLM response")
            
            # Check if this is a hotel query and add TripAdvisor ratings
            if self._is_hotel_query(message):
                logger.info(f"Detected hotel query: {message}")
                destination = self._extract_destination_from_message(message)
                logger.info(f"Extracted destination: {destination}")
                if destination:
                    # Add TripAdvisor ratings
                    tripadvisor_info = await self._get_tripadvisor_info_for_destination(destination)
                    if tripadvisor_info:
                        generated_response += f"\n\n{tripadvisor_info}"
                    
                    # Note: Instagram links are now handled as buttons in the message handler
                    logger.info("Hotel query detected - Instagram buttons will be added by message handler")
                else:
                    logger.info("No destination extracted from hotel query")
            
            # Generate smart LLM-based follow-up questions
            follow_up_questions = await follow_up_service.generate_smart_follow_up_questions(
                message, generated_response, context, max_questions=2
            )
            
            # Format response with follow-up questions
            final_response = follow_up_service.format_follow_up_response(
                generated_response, follow_up_questions
            )
            
            # Store assistant response in conversation memory
            if chat_id:
                conversation_memory.add_assistant_message(
                    chat_id=chat_id,
                    content=final_response,
                    message_type="text"
                )
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._get_fallback_response(message_type, context)

    async def generate_travel_response_without_followup(
        self,
        message: str,
        context: Dict[str, Any],
        message_type: str = "text"
    ) -> str:
        """Generate travel response WITHOUT follow-up questions (for inline keyboard approach)"""
        try:
            chat_id = context.get("chat_id")
            
            # Check if this is a flight query and try to get real-time data
            flight_data = await self._get_flight_data_if_applicable(message, context)
            
            # Build system prompt for travel planning
            system_prompt = self._build_system_prompt(context, message_type)
            
            # Add flight data to context if available
            if flight_data:
                system_prompt += f"\n\nReal-time flight data available:\n{flight_data}"
                
            # Check if this is a flight query without dates
            flight_keywords = ["航班", "机票", "飞机", "flight", "airline", "airport"]
            date_patterns = ["10月", "11月", "12月", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "号", "日", "月"]
            
            message_lower = message.lower()
            has_flight_keywords = any(keyword in message_lower for keyword in flight_keywords)
            has_dates = any(pattern in message for pattern in date_patterns)
            
            if has_flight_keywords and not has_dates:
                # Flight query without dates - ask for dates first
                system_prompt += """

IMPORTANT: The user is asking about flights but hasn't provided specific dates. You should ask for the travel dates first before providing flight options.

Response format:
I'd be happy to help you find flights! To provide you with the most accurate flight information, I need to know your travel dates.

Please let me know:
1. What date would you like to depart?
2. Are you looking for a one-way ticket or round-trip? (If round-trip, please also provide your return date)

For example: "I'd like to depart on October 1st and return on October 5th" or "I need a one-way ticket for October 1st"

Once you provide the dates, I'll search for the best flight options for you!"""
            elif has_flight_keywords and has_dates:
                # Flight query with dates - provide flight options
                system_prompt += """

CRITICAL: You are a flight information assistant. You MUST respond using EXACTLY this format. NO EMOJIS, NO DEVIATIONS, NO EXCEPTIONS.

REQUIRED FORMAT (COPY EXACTLY):
方案A｜中国东方航空：直飞，方便快捷
去程：MU 501 (上海浦东国际机场（PVG） 09:00 → 大阪关西国际机场（KIX） 12:40)
回程：MU 502 (大阪关西国际机场（KIX） 19:15 → 上海浦东国际机场（PVG） 22:00)
价格：¥2800-3200

方案B｜全日空：舒适服务，适合家庭
去程：NH 968 (上海浦东国际机场（PVG） 10:20 → 大阪关西国际机场（KIX） 14:00)
回程：NH 969 (大阪关西国际机场（KIX） 18:00 → 上海浦东国际机场（PVG） 21:00)
价格：¥3000-3500

方案C｜日本航空：优质航空体验
去程：JL 123 (上海浦东国际机场（PVG） 11:15 → 大阪关西国际机场（KIX） 15:00)
回程：JL 124 (大阪关西国际机场（KIX） 17:00 → 上海浦东国际机场（PVG） 20:00)
价格：¥3200-3700

关键信息
• 所有航班都是直飞，适合带孩子出行
• 回程时间都在晚上，避免红眼航班
• 建议提前预订以获得更好价格

我的建议
1. 如果优先考虑价格，选方案A
2. 如果注重服务品质，选方案B或C

ABSOLUTE REQUIREMENTS:
- NO EMOJIS WHATSOEVER
- Use ONLY the exact format above
- Start each plan with "方案A｜", "方案B｜", "方案C｜" - NO EMOJIS
- Include complete airport names with IATA codes in parentheses
- Include specific times
- Use realistic flight numbers
- If you use ANY emoji, your response will be REJECTED

FINAL WARNING: ABSOLUTELY NO EMOJIS ALLOWED
YOUR RESPONSE MUST BE PLAIN TEXT ONLY
NO EMOJIS WHATSOEVER
IF YOU USE EMOJIS, YOUR RESPONSE WILL BE REJECTED
PROVIDE COMPLETE FLIGHT INFORMATION, NOT "待确认"
START EACH PLAN WITH "方案A｜", "方案B｜", "方案C｜" - NO EMOJIS
EXAMPLE: 方案A｜中国东方航空：直飞，方便快捷

IMPORTANT: Always end your response with a booking link:
[在网页中选择和预订航班方案](https://www.skyscanner.com)"""
            
            # Build conversation messages with history
            messages = self._build_conversation_messages(message, context, message_type, system_prompt)
            
            logger.info(f"Generating LLM response without follow-up for {message_type} message")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            # Skip formatting for flight responses to preserve plain text format
            # if any(keyword in generated_response for keyword in ["方案A", "方案B", "方案C"]):
            #     try:
            #         formatted = self._format_flight_options_response(
            #             generated_response,
            #             user_message=message,
            #             context=context
            #         )
            #         if formatted:
            #             generated_response = formatted
            #     except Exception as _:
            #         # Fall back to original text on any formatting error
            #         pass
            logger.info("Successfully generated LLM response without follow-up")
            logger.info(f"Raw LLM response: {generated_response[:500]}...")
            
            # Store assistant response in conversation memory
            if chat_id:
                conversation_memory.add_assistant_message(
                    chat_id=chat_id,
                    content=generated_response,
                    message_type="text"
                )
            
            return generated_response
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._get_fallback_response(message_type, context)

    def _format_flight_options_response(self, text: str, user_message: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """Beautify LLM flight ABC options text with emojis and clear line breaks.

        Expected input contains sections starting with lines like:
        方案A｜...\n去程 ...\n回程 ...\n近期参考总价 ...
        方案B｜...  ...
        方案C｜...  ...
        Followed optionally by sections:
        关键信息（直说）\n• ...
        我 的建议（带孩子优先级）\n1. ...\n2. ...
        """
        # Normalize line endings and split
        lines = [ln.strip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        
        # Helpers
        def is_plan_header(line: str) -> (Optional[str], Optional[str]):
            # Allow optional leading emojis or characters before "方案X"
            m = re.search(r"方案([ABC])\s*[\|｜]\s*(.+)$", line)
            if m:
                return m.group(1), m.group(2).strip()
            return None, None

        plans: Dict[str, Dict[str, str]] = {}
        current: Optional[str] = None
        header_texts: Dict[str, str] = {}
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            plan_key, header_text = is_plan_header(line)
            if plan_key:
                current = plan_key
                header_texts[current] = header_text or ""
                plans.setdefault(current, {})
                idx += 1
                continue
            if current:
                # More flexible matching for flight segments
                if (line.startswith("去程") or "去程" in line or 
                    ("去" in line and ("机场" in line or "→" in line))):
                    plans[current]["outbound"] = line
                elif (line.startswith("回程") or "回程" in line or 
                      ("回" in line and ("机场" in line or "→" in line))):
                    plans[current]["inbound"] = line
                elif line.startswith("近期参考总价") or line.startswith("参考总价") or line.startswith("价格"):
                    plans[current]["price"] = line
            idx += 1
        
        # Parse extra sections
        key_points: List[str] = []
        suggestions: List[str] = []
        section = None
        for line in lines:
            if line.startswith("关键信息"):
                section = "keys"
                continue
            if line.startswith("我的建议"):
                section = "sugg"
                continue
            if section == "keys":
                if not line:
                    section = None
                elif line.startswith("•") or line.startswith("-"):
                    # strip bullet
                    key_points.append(line.lstrip("•-").strip())
            elif section == "sugg":
                if not line:
                    section = None
                elif re.match(r"^\d+\.\s*", line):
                    suggestions.append(line)

        # Build pretty output
        pretty_parts: List[str] = []

        # Preface summarizing user's requirements if detectable
        preface = self._build_user_requirement_summary(user_message, context)
        if preface:
            pretty_parts.append(preface)
            pretty_parts.append("")
        label_emoji = {"A": "🅰️", "B": "🅱️", "C": "🅲️"}
        # Debug: print what we found
        logger.info(f"Found plans: {plans}")
        logger.info(f"Found headers: {header_texts}")

        def _normalize_date(md: Optional[re.Match]) -> Optional[str]:
            if not md:
                return None
            mm = int(md.group(1))
            dd = int(md.group(2))
            # Prefer Chinese style: 10月1日
            return f"{mm}月{dd}日"

        def _extract_paren_note(line: str) -> str:
            m = re.findall(r"（([^）]+)）", line)
            return f"（{m[-1]}）" if m else ""

        def _format_segment(line: str, label: str, emoji: str) -> List[str]:
            # Date like 10月1日
            date_m = re.search(r"(\d{1,2})月\s*(\d{1,2})[号日]?", line)
            date_str = _normalize_date(date_m)
            # Flight number like NH 955 or NH955
            fn_m = re.search(r"([A-Z]{2})\s?(\d{2,4})", line)
            fn = f"{fn_m.group(1)} {fn_m.group(2)}" if fn_m else None
            # Extract airport names and IATA codes more robustly
            # Look for patterns like: 上海浦东国际机场（PVG） or 浦东国际机场（PVG） or 羽田机场（HND）
            airport_pattern = r"([^（\s]+?(?:国际机场|机场|空港))（([A-Z]{3})）"
            airports = re.findall(airport_pattern, line)
            
            # Extract times
            times = re.findall(r"(\d{1,2}:\d{2})", line)
            
            header_parts: List[str] = [f"{emoji} {label}"]
            dt_fn = "：".join([p for p in [date_str, fn] if p])
            if dt_fn:
                header_parts.append(dt_fn)
            header = " ".join(header_parts).strip()

            # Check if we have enough information to display properly
            has_airports = len(airports) >= 2
            has_times = len(times) >= 2
            has_flight_number = fn is not None
            
            # If we don't have enough info, return a simplified version
            if not (has_airports and has_times):
                if has_flight_number:
                    return [header, "航班信息待确认", ""]
                else:
                    return [header, "具体航班待确认", ""]

            body_lines: List[str] = []
            orig_name, orig_iata = airports[0]
            dest_name, dest_iata = airports[1]
            dep_t = times[0]
            arr_t = times[1]
            body_lines.append(f"{orig_name}（{orig_iata}） {dep_t}")
            body_lines.append("→")
            body_lines.append(f"{dest_name}（{dest_iata}） {arr_t}")

            return [header, *body_lines]
        for code in ["A", "B", "C"]:
            if code in header_texts:
                header = header_texts[code]
                p = plans.get(code, {})
                pretty_parts.append(f"{label_emoji.get(code, '✨')} 方案{code}｜{header}")
                pretty_parts.append("")
                if p.get("outbound"):
                    pretty_parts.extend(_format_segment(p["outbound"], "去程", "🛫"))
                if p.get("inbound"):
                    pretty_parts.extend(_format_segment(p["inbound"], "回程", "🛬"))
                if p.get("price"):
                    # Ensure consistent label
                    price_line = re.sub(r"^近期参考总价", "近期参考总价", p["price"]).strip()
                    pretty_parts.append(f"💰 {price_line}")
                pretty_parts.append("")  # blank line between plans
                pretty_parts.append("")  # extra blank line for better spacing

        if key_points:
            pretty_parts.append("📌 关键信息")
            for item in key_points:
                pretty_parts.append(f"• {item}")
            pretty_parts.append("")

        if suggestions:
            pretty_parts.append("🧭 我的建议（带孩子优先级）")
            for s in suggestions:
                pretty_parts.append(s)

        result = "\n".join(pretty_parts).strip()
        
        # Remove any booking links that might have been generated by LLM
        result = re.sub(r'🔗\s*预订链接：.*\n?', '', result)
        result = re.sub(r'🔗\s*[Bb]ooking\s*[Ll]ink:.*\n?', '', result)
        result = re.sub(r'https?://[^\s]+\n?', '', result)
        
        # Add web page link for flight selection
        if result and any(keyword in result for keyword in ["方案A", "方案B", "方案C"]):
            logger.info(f"Generating web link for user message: {user_message}")
            logger.info(f"Flight result text: {result[:200]}...")
            try:
                web_link = self._generate_flight_web_link(result, user_message, context)
                if web_link:
                    logger.info(f"Generated web link: {web_link}")
                    result += f"\n\n[在网页中选择和预订航班方案]({web_link})"
                else:
                    logger.warning("Web link generation failed, using fallback")
                    # Generate a more specific fallback link based on the route
                    fallback_link = self._generate_fallback_booking_link(user_message, context, result)
                    if fallback_link:
                        logger.info(f"Generated fallback link: {fallback_link}")
                        result += f"\n\n[预订航班]({fallback_link})"
                    else:
                        logger.warning("Both web link and fallback link generation failed")
                        # Add a simple fallback link
                        result += f"\n\n[预订航班](https://www.skyscanner.com)"
            except Exception as e:
                logger.error(f"Error in web link generation: {e}")
                # Add a simple fallback link
                result += f"\n\n[预订航班](https://www.skyscanner.com)"
        
        # Debug: log if we have no formatted content
        if not result:
            logger.warning(f"No formatted content generated. Original text length: {len(text)}")
            logger.warning(f"Original text preview: {text[:200]}...")
        # Fallback to original if parsing failed drastically
        return result if result else text

    def _generate_flight_web_link(self, flight_text: str, user_message: Optional[str], context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Generate a web link for flight selection page"""
        try:
            import requests
            import json
            
            # Parse flight data from the formatted text
            flight_data = self._parse_flight_data_for_web(flight_text, user_message, context)
            
            # Debug: log the data being sent to web server
            logger.info(f"Sending flight data to web server: {json.dumps(flight_data, ensure_ascii=False, indent=2)}")
            
            # Send data to web server using synchronous requests
            response = requests.post('https://waypal.ai/api/flights', 
                                   json=flight_data, 
                                   timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                web_url = result.get('url')
                if web_url:
                    return f"https://waypal.ai{web_url}"
            else:
                logger.error(f"Failed to create web page: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error generating web link: {e}")
        
        return None

    def _generate_fallback_booking_link(self, user_message: Optional[str], context: Optional[Dict[str, Any]], flight_text: Optional[str] = None) -> Optional[str]:
        """Generate a fallback booking link when web generation fails"""
        if not user_message and not flight_text:
            return None
            
        # Extract route information
        departure = ""
        destination = ""
        
        # First try to extract from flight text if available
        if flight_text:
            import re
            # Look for airport patterns in flight text
            airport_pattern = r'([^（]+)（([A-Z]{3})）\s*[→→]\s*([^（]+)（([A-Z]{3})）'
            
            for line in flight_text.split('\n'):
                match = re.search(airport_pattern, line)
                if match:
                    departure_airport = match.group(1).strip()
                    destination_airport = match.group(3).strip()
                    
                    departure = self._extract_city_from_airport(departure_airport)
                    destination = self._extract_city_from_airport(destination_airport)
                    break
        
        # If no route found in flight text, try user message
        if not departure and not destination and user_message:
            import re
            route_patterns = [
                r'从\s*([^到]+?)\s*到\s*([^，。\s]+)',
                r'([^到]+?)\s*到\s*([^，。\s]+)',
                r'([^飞]+?)\s*飞\s*([^，。\s]+)'
            ]
            
            for pattern in route_patterns:
                match = re.search(pattern, user_message)
                if match:
                    departure = match.group(1).strip()
                    destination = match.group(2).strip()
                    break
        
        # Map city names to English for search
        city_mapping = {
            # Chinese cities
            '上海': 'Shanghai', '北京': 'Beijing', '深圳': 'Shenzhen', '广州': 'Guangzhou',
            '成都': 'Chengdu', '重庆': 'Chongqing', '西安': 'Xian', '杭州': 'Hangzhou',
            '南京': 'Nanjing', '武汉': 'Wuhan', '天津': 'Tianjin', '青岛': 'Qingdao',
            '大连': 'Dalian', '厦门': 'Xiamen', '福州': 'Fuzhou', '济南': 'Jinan',
            '长沙': 'Changsha', '郑州': 'Zhengzhou', '昆明': 'Kunming', '贵阳': 'Guiyang',
            '南宁': 'Nanning', '海口': 'Haikou', '三亚': 'Sanya', '乌鲁木齐': 'Urumqi',
            '兰州': 'Lanzhou', '银川': 'Yinchuan', '西宁': 'Xining', '拉萨': 'Lhasa',
            '呼和浩特': 'Hohhot', '哈尔滨': 'Harbin', '长春': 'Changchun', '沈阳': 'Shenyang',
            '石家庄': 'Shijiazhuang', '太原': 'Taiyuan', '合肥': 'Hefei', '南昌': 'Nanchang',
            '台北': 'Taipei', '高雄': 'Kaohsiung', '台中': 'Taichung', '香港': 'Hong Kong',
            '澳门': 'Macau',
            
            # Japanese cities
            '东京': 'Tokyo', '大阪': 'Osaka', '名古屋': 'Nagoya', '福冈': 'Fukuoka',
            '札幌': 'Sapporo', '仙台': 'Sendai', '广岛': 'Hiroshima', '京都': 'Kyoto',
            '神户': 'Kobe', '横滨': 'Yokohama', '川崎': 'Kawasaki', '埼玉': 'Saitama',
            '千叶': 'Chiba', '静冈': 'Shizuoka', '冈山': 'Okayama', '熊本': 'Kumamoto',
            '鹿儿岛': 'Kagoshima', '冲绳': 'Okinawa', '北海道': 'Hokkaido',
            
            # Korean cities
            '首尔': 'Seoul', '釜山': 'Busan', '大邱': 'Daegu', '仁川': 'Incheon',
            '光州': 'Gwangju', '大田': 'Daejeon', '蔚山': 'Ulsan', '水原': 'Suwon',
            
            # Southeast Asian cities
            '新加坡': 'Singapore', '吉隆坡': 'Kuala Lumpur', '曼谷': 'Bangkok',
            '雅加达': 'Jakarta', '马尼拉': 'Manila', '胡志明市': 'Ho Chi Minh City',
            '河内': 'Hanoi', '金边': 'Phnom Penh', '万象': 'Vientiane', '仰光': 'Yangon',
            
            # Other major cities
            '纽约': 'New York', '洛杉矶': 'Los Angeles', '芝加哥': 'Chicago',
            '休斯顿': 'Houston', '费城': 'Philadelphia', '凤凰城': 'Phoenix',
            '圣安东尼奥': 'San Antonio', '圣地亚哥': 'San Diego', '达拉斯': 'Dallas',
            '圣何塞': 'San Jose', '奥斯汀': 'Austin', '杰克逊维尔': 'Jacksonville',
            '伦敦': 'London', '巴黎': 'Paris', '柏林': 'Berlin', '罗马': 'Rome',
            '马德里': 'Madrid', '阿姆斯特丹': 'Amsterdam', '维也纳': 'Vienna',
            '苏黎世': 'Zurich', '布鲁塞尔': 'Brussels', '哥本哈根': 'Copenhagen',
            '斯德哥尔摩': 'Stockholm', '奥斯陆': 'Oslo', '赫尔辛基': 'Helsinki',
            '莫斯科': 'Moscow', '圣彼得堡': 'Saint Petersburg', '基辅': 'Kiev',
            '悉尼': 'Sydney', '墨尔本': 'Melbourne', '布里斯班': 'Brisbane',
            '珀斯': 'Perth', '阿德莱德': 'Adelaide', '奥克兰': 'Auckland',
            '多伦多': 'Toronto', '温哥华': 'Vancouver', '蒙特利尔': 'Montreal',
            '墨西哥城': 'Mexico City', '圣保罗': 'Sao Paulo', '里约热内卢': 'Rio de Janeiro',
            '布宜诺斯艾利斯': 'Buenos Aires', '利马': 'Lima', '波哥大': 'Bogota',
            '开罗': 'Cairo', '约翰内斯堡': 'Johannesburg', '开普敦': 'Cape Town',
            '拉各斯': 'Lagos', '内罗毕': 'Nairobi', '达累斯萨拉姆': 'Dar es Salaam'
        }
        
        # Try to get English name, fallback to original if not found
        departure_en = city_mapping.get(departure, departure)
        destination_en = city_mapping.get(destination, destination)
        
        # Generate Amadeus search link [[memory:7792854]]
        search_query = f"{departure_en} to {destination_en}"
        amadeus_link = f"https://www.amadeus.com/travel/flight-search?origin={departure_en}&destination={destination_en}&departureDate=&returnDate=&adults=1&children=0&infants=0&travelClass=economy&currency=CNY"
        
        return amadeus_link

    def _extract_city_from_airport(self, airport_name: str) -> str:
        """Extract city name from airport name using intelligent parsing"""
        import re
        
        # First try specific airport mappings for common airports (before any processing)
        airport_mappings = {
            '上海浦东国际机场': '上海',
            '上海虹桥国际机场': '上海', 
            '新加坡樟宜国际机场': '新加坡',
            '新加坡樟宜机场': '新加坡',
            '东京成田国际机场': '东京',
            '东京羽田机场': '东京',
            '大阪关西国际机场': '大阪',
            '大阪伊丹机场': '大阪',
        }
        
        for mapped_airport, city_name in airport_mappings.items():
            if mapped_airport in airport_name:
                return city_name
        
        # Remove common airport suffixes and keywords
        airport_clean = airport_name.strip()
        
        # Remove common airport suffixes in multiple languages
        suffixes_to_remove = [
            r'国际机场$', r'机场$', r'Airport$', r'International Airport$',
            r'Domestic Airport$', r'Regional Airport$', r'Field$',
            r'空港$', r'国際空港$', r'国内空港$', r'공항$', r'국제공항$'
        ]
        
        for suffix in suffixes_to_remove:
            airport_clean = re.sub(suffix, '', airport_clean, flags=re.IGNORECASE)
        
        # Remove common prefixes
        prefixes_to_remove = [
            r'^北京', r'^上海', r'^广州', r'^深圳', r'^成都', r'^重庆',
            r'^西安', r'^杭州', r'^南京', r'^武汉', r'^天津', r'^青岛',
            r'^大连', r'^厦门', r'^福州', r'^济南', r'^长沙', r'^郑州',
            r'^昆明', r'^贵阳', r'^南宁', r'^海口', r'^三亚', r'^乌鲁木齐',
            r'^兰州', r'^银川', r'^西宁', r'^拉萨', r'^呼和浩特', r'^哈尔滨',
            r'^长春', r'^沈阳', r'^石家庄', r'^太原', r'^合肥', r'^南昌',
            r'^福州', r'^台北', r'^高雄', r'^台中', r'^香港', r'^澳门'
        ]
        
        for prefix in prefixes_to_remove:
            airport_clean = re.sub(prefix, '', airport_clean)
        
        # Extract city name using various patterns
        city_patterns = [
            # Chinese cities
            r'([^国际空港机场]+?)(?:国际|国内|)?(?:空港|机场)',
            r'([^国际空港机场]+?)(?:Airport|Field)',
            # International cities - extract before common airport names
            r'([^A-Z\s]+?)(?:\s+(?:International|Domestic|Regional)?\s*Airport)',
            r'([^A-Z\s]+?)(?:\s+Field)',
            # Handle special cases like "New York JFK" -> "New York"
            r'([^A-Z\s]+?)(?:\s+[A-Z]{3,4})',
        ]
        
        for pattern in city_patterns:
            match = re.search(pattern, airport_clean, re.IGNORECASE)
            if match:
                city = match.group(1).strip()
                if city and len(city) > 1:
                    return city
        
        # If no pattern matches, try to extract meaningful parts
        # Split by common separators and take the most meaningful part
        parts = re.split(r'[\s\-_]+', airport_clean)
        
        # Filter out common airport-related words
        airport_words = {'airport', 'field', 'terminal', 'international', 'domestic', 
                        'regional', 'airport', '空港', '机场', '国际', '国内'}
        
        meaningful_parts = [part for part in parts 
                          if part.lower() not in airport_words and len(part) > 1]
        
        if meaningful_parts:
            # Return the longest meaningful part
            return max(meaningful_parts, key=len)
        
        # Final fallback: return first 2-3 characters if Chinese, or first word if English
        if re.search(r'[\u4e00-\u9fff]', airport_clean):
            return airport_clean[:2] if len(airport_clean) >= 2 else airport_clean
        else:
            first_word = airport_clean.split()[0] if airport_clean.split() else airport_clean
            return first_word[:10] if len(first_word) > 10 else first_word

    def _parse_flight_data_for_web(self, flight_text: str, user_message: Optional[str], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse flight text into structured data for web display"""
        lines = flight_text.split('\n')
        
        # Extract route information from flight text dynamically
        route = "航班查询结果"
        dates = ""
        departure = ""
        destination = ""
        departure_code = ""
        destination_code = ""
        
        # Parse route from flight text (look for airport patterns)
        import re
        
        # Look for airport patterns in flight text - handle multi-line format
        departure_airport = ""
        destination_airport = ""
        
        # Find departure airport (usually appears first)
        for line in lines:
            if '（' in line and '）' in line and not departure_airport:
                match = re.search(r'([^（]+)（([A-Z]{3})）', line)
                if match:
                    departure_airport = match.group(1).strip()
                    departure_code = match.group(2)
                    departure = self._extract_city_from_airport(departure_airport)
                    logger.info(f"Found departure airport: {departure_airport} ({departure_code}) -> {departure}")
                    break
        
        # Find destination airport (usually appears after departure)
        for line in lines:
            if '（' in line and '）' in line and departure_airport:
                match = re.search(r'([^（]+)（([A-Z]{3})）', line)
                if match:
                    airport_name = match.group(1).strip()
                    airport_code = match.group(2)
                    # Make sure this is different from departure
                    if airport_code != departure_code:
                        destination_airport = airport_name
                        destination_code = airport_code
                        destination = self._extract_city_from_airport(destination_airport)
                        logger.info(f"Found destination airport: {destination_airport} ({destination_code}) -> {destination}")
                        break
        
        if departure and destination:
            route = f"{departure} → {destination}"
            logger.info(f"Parsed route from flight text: {route} (departure: {departure_code}, destination: {destination_code})")
        else:
            logger.warning(f"Failed to parse route from flight text. Departure: {departure}, Destination: {destination}")
        
        # If no airport pattern found, try to extract from user message
        if route == "航班查询结果" and user_message:
            route_patterns = [
                r'从\s*([^到]+?)\s*到\s*([^，。\s]+)',
                r'([^到]+?)\s*到\s*([^，。\s]+)',
                r'([^飞]+?)\s*飞\s*([^，。\s]+)'
            ]
            
            for pattern in route_patterns:
                match = re.search(pattern, user_message)
                if match:
                    departure_city = match.group(1).strip()
                    destination_city = match.group(2).strip()
                    
                    # Map city names to codes (expanded list)
                    city_codes = {
                        # Chinese cities
                        '上海': 'PVG', '北京': 'PEK', '深圳': 'SZX', '广州': 'CAN',
                        '成都': 'CTU', '重庆': 'CKG', '西安': 'XIY', '杭州': 'HGH',
                        '南京': 'NKG', '武汉': 'WUH', '天津': 'TSN', '青岛': 'TAO',
                        '大连': 'DLC', '厦门': 'XMN', '福州': 'FOC', '济南': 'TNA',
                        '长沙': 'CSX', '郑州': 'CGO', '昆明': 'KMG', '贵阳': 'KWE',
                        '南宁': 'NNG', '海口': 'HAK', '三亚': 'SYX', '乌鲁木齐': 'URC',
                        '兰州': 'LHW', '银川': 'INC', '西宁': 'XNN', '拉萨': 'LXA',
                        '呼和浩特': 'HET', '哈尔滨': 'HRB', '长春': 'CGQ', '沈阳': 'SHE',
                        '石家庄': 'SJW', '太原': 'TYN', '合肥': 'HFE', '南昌': 'KHN',
                        '台北': 'TPE', '高雄': 'KHH', '台中': 'RMQ', '香港': 'HKG',
                        '澳门': 'MFM',
                        
                        # Japanese cities
                        '东京': 'NRT', '大阪': 'KIX', '名古屋': 'NGO', '福冈': 'FUK',
                        '札幌': 'CTS', '仙台': 'SDJ', '广岛': 'HIJ', '京都': 'UKY',
                        '神户': 'UKB', '横滨': 'YOK', '川崎': 'KWS', '埼玉': 'SAI',
                        '千叶': 'CHB', '静冈': 'FSZ', '冈山': 'OKJ', '熊本': 'KMJ',
                        '鹿儿岛': 'KOJ', '冲绳': 'OKA', '北海道': 'CTS',
                        
                        # Korean cities
                        '首尔': 'ICN', '釜山': 'PUS', '大邱': 'TAE', '仁川': 'ICN',
                        '光州': 'KWJ', '大田': 'TJW', '蔚山': 'USN', '水原': 'SWU',
                        
                        # Southeast Asian cities
                        '新加坡': 'SIN', '吉隆坡': 'KUL', '曼谷': 'BKK',
                        '雅加达': 'CGK', '马尼拉': 'MNL', '胡志明市': 'SGN',
                        '河内': 'HAN', '金边': 'PNH', '万象': 'VTE', '仰光': 'RGN',
                        
                        # Other major cities
                        '纽约': 'JFK', '洛杉矶': 'LAX', '芝加哥': 'ORD',
                        '休斯顿': 'IAH', '费城': 'PHL', '凤凰城': 'PHX',
                        '圣安东尼奥': 'SAT', '圣地亚哥': 'SAN', '达拉斯': 'DFW',
                        '圣何塞': 'SJC', '奥斯汀': 'AUS', '杰克逊维尔': 'JAX',
                        '伦敦': 'LHR', '巴黎': 'CDG', '柏林': 'BER', '罗马': 'FCO',
                        '马德里': 'MAD', '阿姆斯特丹': 'AMS', '维也纳': 'VIE',
                        '苏黎世': 'ZUR', '布鲁塞尔': 'BRU', '哥本哈根': 'CPH',
                        '斯德哥尔摩': 'ARN', '奥斯陆': 'OSL', '赫尔辛基': 'HEL',
                        '莫斯科': 'SVO', '圣彼得堡': 'LED', '基辅': 'KBP',
                        '悉尼': 'SYD', '墨尔本': 'MEL', '布里斯班': 'BNE',
                        '珀斯': 'PER', '阿德莱德': 'ADL', '奥克兰': 'AKL',
                        '多伦多': 'YYZ', '温哥华': 'YVR', '蒙特利尔': 'YUL',
                        '墨西哥城': 'MEX', '圣保罗': 'GRU', '里约热内卢': 'GIG',
                        '布宜诺斯艾利斯': 'EZE', '利马': 'LIM', '波哥大': 'BOG',
                        '开罗': 'CAI', '约翰内斯堡': 'JNB', '开普敦': 'CPT',
                        '拉各斯': 'LOS', '内罗毕': 'NBO', '达累斯萨拉姆': 'DAR'
                    }
                    
                    departure_code = city_codes.get(departure_city, '')
                    destination_code = city_codes.get(destination_city, '')
                    
                    route = f"{departure_city} → {destination_city}"
                    departure = departure_city
                    destination = destination_city
                    break
            
            # Extract dates
            import re
            date_matches = re.findall(r'(\d{1,2})月\s*(\d{1,2})[号日]?', user_message)
            if len(date_matches) >= 2:
                dates = f"{date_matches[0][0]}/{date_matches[0][1]} - {date_matches[1][0]}/{date_matches[1][1]}"
        
        # Parse flight plans
        plans = []
        current_plan = None
        current_segment_lines = []
        current_segment_type = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('🅰️') or line.startswith('🅱️') or line.startswith('🅲️'):
                # Save previous plan if exists
                if current_plan:
                    plans.append(current_plan)
                
                # Parse plan header
                parts = line.split('｜')
                if len(parts) >= 2:
                    plan_code = parts[0][-1]  # Get A, B, or C
                    airline_info = parts[1].strip()
                    
                    current_plan = {
                        'code': plan_code,
                        'emoji': parts[0][0],
                        'airline': airline_info.split()[0] if airline_info else '',
                        'description': airline_info,
                        'outbound': {},
                        'inbound': {},
                        'price': '',
                        'price_note': ''
                    }
            
            elif current_plan and line.startswith('🛫'):
                # End previous segment if exists
                if current_segment_type and current_segment_lines:
                    segment_text = '\n'.join(current_segment_lines)
                    logger.info(f"Parsing {current_segment_type} segment: {segment_text}")
                    if current_segment_type == 'outbound':
                        current_plan['outbound'] = self._parse_flight_segment(segment_text)
                    elif current_segment_type == 'inbound':
                        current_plan['inbound'] = self._parse_flight_segment(segment_text)
                
                # Start of outbound flight segment
                current_segment_type = 'outbound'
                current_segment_lines = [line]
            
            elif current_plan and line.startswith('🛬'):
                # End previous segment if exists
                if current_segment_type and current_segment_lines:
                    segment_text = '\n'.join(current_segment_lines)
                    logger.info(f"Parsing {current_segment_type} segment: {segment_text}")
                    if current_segment_type == 'outbound':
                        current_plan['outbound'] = self._parse_flight_segment(segment_text)
                    elif current_segment_type == 'inbound':
                        current_plan['inbound'] = self._parse_flight_segment(segment_text)
                
                # Start of inbound flight segment
                current_segment_type = 'inbound'
                current_segment_lines = [line]
            
            elif current_plan and line.startswith('💰'):
                # End previous segment if exists
                if current_segment_type and current_segment_lines:
                    segment_text = '\n'.join(current_segment_lines)
                    logger.info(f"Parsing {current_segment_type} segment: {segment_text}")
                    if current_segment_type == 'outbound':
                        current_plan['outbound'] = self._parse_flight_segment(segment_text)
                    elif current_segment_type == 'inbound':
                        current_plan['inbound'] = self._parse_flight_segment(segment_text)
                
                # Parse price
                price_text = line[2:].strip()
                current_plan['price'] = price_text
                current_plan['price_note'] = price_text
                current_segment_type = None
                current_segment_lines = []
            
            elif current_plan and current_segment_type and line and not line.startswith('🅰️') and not line.startswith('🅱️') and not line.startswith('🅲️'):
                # Collect all lines that belong to current segment
                current_segment_lines.append(line)
        
        # Parse the last segment if exists
        if current_plan and current_segment_type and current_segment_lines:
            segment_text = '\n'.join(current_segment_lines)
            logger.info(f"Parsing final {current_segment_type} segment: {segment_text}")
            if current_segment_type == 'outbound':
                current_plan['outbound'] = self._parse_flight_segment(segment_text)
            elif current_segment_type == 'inbound':
                current_plan['inbound'] = self._parse_flight_segment(segment_text)
        
        if current_plan:
            plans.append(current_plan)
        
        # For web display, use the first complete plan with both outbound and inbound segments
        selected_plan = None
        for plan in plans:
            if plan.get('outbound') and plan.get('inbound'):
                selected_plan = plan
                logger.info(f"Selected plan {plan.get('code', 'Unknown')} for web display with outbound and inbound segments")
                break
        
        # If we have a selected plan, use it for web display
        if selected_plan:
            outbound_info = selected_plan.get('outbound', {})
            inbound_info = selected_plan.get('inbound', {})
            
            logger.info(f"Web display will show outbound: {outbound_info}")
            logger.info(f"Web display will show inbound: {inbound_info}")
            
            # Update departure and destination info from the selected plan
            if outbound_info:
                departure = outbound_info.get('departure_city', departure)
                departure_code = outbound_info.get('departure_code', departure_code)
            if inbound_info:
                destination = inbound_info.get('destination_city', destination)
                destination_code = inbound_info.get('destination_code', destination_code)
            
            logger.info(f"Updated route info for web display: {departure} ({departure_code}) → {destination} ({destination_code})")
        
        return {
            'title': f'{route} 航班选择',
            'route': route,
            'dates': dates,
            'departure': departure,
            'destination': destination,
            'departure_code': departure_code,
            'destination_code': destination_code,
            'plans': plans,
            'key_points': [],
            'suggestions': []
        }

    def _parse_flight_segment(self, text: str) -> Dict[str, str]:
        """Parse a flight segment text (can be multi-line) into structured data"""
        import re
        
        logger.info(f"Parsing flight segment text: {text}")
        
        # Initialize with default values
        result = {
            'date': '',
            'flight_number': '',
            'departure_time': '',
            'departure_airport': '',
            'departure_code': '',
            'arrival_time': '',
            'arrival_airport': '',
            'arrival_code': '',
            'duration': ''
        }
        
        try:
            # Extract date pattern like "10月1日"
            date_match = re.search(r'(\d{1,2})月\s*(\d{1,2})[号日]?', text)
            if date_match:
                result['date'] = f"{date_match.group(1)}月{date_match.group(2)}日"
            
            # Extract flight number pattern like "MU 210"
            flight_match = re.search(r'([A-Z]{2})\s*(\d{3,4})', text)
            if flight_match:
                result['flight_number'] = f"{flight_match.group(1)} {flight_match.group(2)}"
            
            # Extract airport pattern like "上海浦东国际机场（PVG） 09:00"
            airport_pattern = r'([^（]+)（([A-Z]{3})）\s*(\d{1,2}:\d{2})'
            airports = re.findall(airport_pattern, text)
            
            if len(airports) >= 2:
                # First airport is departure
                result['departure_airport'] = airports[0][0].strip()
                result['departure_code'] = airports[0][1]
                result['departure_time'] = airports[0][2]
                
                # Second airport is arrival
                result['arrival_airport'] = airports[1][0].strip()
                result['arrival_code'] = airports[1][1]
                result['arrival_time'] = airports[1][2]
            
            # Calculate duration if we have both times
            if result['departure_time'] and result['arrival_time']:
                try:
                    from datetime import datetime, timedelta
                    dep_time = datetime.strptime(result['departure_time'], '%H:%M')
                    arr_time = datetime.strptime(result['arrival_time'], '%H:%M')
                    
                    # Handle overnight flights
                    if arr_time < dep_time:
                        arr_time += timedelta(days=1)
                    
                    duration = arr_time - dep_time
                    hours = duration.seconds // 3600
                    minutes = (duration.seconds % 3600) // 60
                    result['duration'] = f"{hours}h {minutes}m"
                except:
                    result['duration'] = ''
            
        except Exception as e:
            logger.error(f"Error parsing flight segment: {e}")
        
        logger.info(f"Parsed flight segment result: {result}")
        return result

    def _build_user_requirement_summary(self, user_message: Optional[str], context: Optional[Dict[str, Any]]) -> str:
        """Build a concise preface summarizing user's key requirements in Chinese.
        Heuristically extracts date, route, and family/no red-eye/no LCC preferences.
        """
        if not user_message:
            return ""
        name = (context or {}).get("user_name", "您")
        msg = user_message
        parts: List[str] = []
        # Dates
        dep = None
        ret = None
        m = re.search(r"(10|11|12|[1-9])月\s*([0-3]?\d)(号|日)?", msg)
        if m:
            dep = f"{m.group(1)}/{m.group(2)}"
        m2 = re.findall(r"(10|11|12|[1-9])月\s*([0-3]?\d)(号|日)?", msg)
        if m2 and len(m2) >= 2:
            dep = f"{m2[0][0]}/{m2[0][1]}"
            ret = f"{m2[1][0]}/{m2[1][1]}"
        # Route
        route = None
        if ("上海" in msg or "浦东" in msg or "虹桥" in msg) and ("东京" in msg or "成田" in msg or "羽田" in msg):
            route = "上海→东京"
        # Evening return
        evening = "晚上" in msg or "傍晚" in msg or "晚间" in msg
        # Preferences
        with_kids = "带孩子" in msg or "孩子" in msg or "宝宝" in msg
        no_redeye = "不坐红眼" in msg or "不红眼" in msg or "不要红眼" in msg
        no_lcc = "不选廉航" in msg or "不要廉航" in msg or "不坐廉航" in msg or "廉航不要" in msg

        reqs: List[str] = []
        if dep and route:
            reqs.append(f"{dep} {route}")
        if ret:
            when = "晚上" if evening else ""
            reqs.append(f"{ret} {when}回沪".strip())
        flags: List[str] = []
        if with_kids:
            flags.append("带孩子")
        if no_redeye:
            flags.append("不坐红眼")
        if no_lcc:
            flags.append("不选廉航")
        if flags:
            reqs.append("、".join(flags))

        if not reqs:
            return ""
        req_text = "；".join(reqs)
        return f"{name}，按你要求（{req_text}），我把最稳的全服务航司直飞组合挑好了，并给出当下可参考价区间："

    def _build_system_prompt(self, context: Dict[str, Any], message_type: str) -> str:
        """Build system prompt for travel planning context"""
        chat_type = context.get("chat_type", "private")
        user_name = context.get("user_name", "User")
        
        base_prompt = f"""You are {settings.bot_name}, an AI-powered travel planning assistant. 
You help individuals and groups plan amazing trips by providing personalized recommendations, 
itineraries, and travel advice.

Key guidelines:
- Be enthusiastic and helpful about travel planning
- Provide practical, actionable travel advice with SPECIFIC details
- Consider budget, preferences, and group dynamics
- For flight queries: Provide specific flight numbers, times, airlines, and price ranges
- For hotel queries: Use the EXACT format below for each hotel recommendation:
  - **Hotel Name (local + English if available)** (CRITICAL: Always wrap hotel names in **bold** markdown)
  - TripAdvisor评分：[rating]/5
  - 价格范围：[price range in appropriate currency - use ¥ for Chinese users, $ for English users, € for European destinations, etc.]
  - 优势：[key highlights & why it's recommended]
- For activities: Suggest specific attractions, opening hours, and ticket prices
- Always provide multiple options when possible
- Include practical tips (airport transfers, best times to visit, etc.)
- Be detailed but conversational (aim for 4-8 sentences for complex queries)
- When you don't have specific current data, acknowledge this and provide general guidance

For flight recommendations specifically:
- ALWAYS provide 3 structured options (A, B, C) with clear advantages
- Use exact format: "方案A｜[航空公司] [特点总结]"
- CRITICAL: Use ONLY the exact destinations and departure cities specified by the user. 
- If user says "从上海到北海道", use 上海 as departure and 北海道 as destination
- If user says "从北京到东京", use 北京 as departure and 东京 as destination  
- NEVER substitute with other cities like Singapore, Seoul, etc.
- NEVER change departure city (if user says 上海, don't use 北京 or other cities)
- NEVER include booking links or reservation URLs in your response
- MANDATORY: Each flight segment MUST include ALL details in this EXACT format:
  "去程 [日期]：[航班号] [出发机场全名]（[IATA代码]） [起飞时间] → [到达机场全名]（[IATA代码]） [到达时间]"
  "回程 [日期]：[航班号] [出发机场全名]（[IATA代码]） [起飞时间] → [到达机场全名]（[IATA代码]） [到达时间]"
- Example: "去程 10月1日：NH 968 上海浦东国际机场（PVG） 10:20 → 东京羽田机场（HND） 14:00"
- NEVER use incomplete information - if you don't have specific details, don't include that flight option
- Provide realistic price ranges with explanations
- Consider family-friendly options (no red-eye flights for families)
- Suggest airport choices (HND vs NRT for Tokyo, etc.)
- Include practical tips about booking timing
- End with "关键信息（直说）" and "我的建议（带孩子优先级）"

"""
        
        if chat_type in ["group", "supergroup"]:
            base_prompt += f"""Current context: You're in a group chat helping multiple people plan a trip together.
Focus on collaborative planning and group-friendly suggestions."""
        else:
            base_prompt += f"""Current context: You're in a private chat with {user_name}.
Provide personalized travel recommendations."""
        
        # Add message type specific context
        if message_type == "photo":
            base_prompt += "\n\nThe user shared a photo. Analyze the destination/scene and provide relevant travel insights."
        elif message_type == "link":
            base_prompt += "\n\nThe user shared travel-related links. Acknowledge and build upon their research."
        
        return base_prompt

    def _build_user_prompt(self, message: str, context: Dict[str, Any], message_type: str) -> str:
        """Build user prompt with message and context"""
        user_name = context.get("user_name", "User")
        chat_type = context.get("chat_type", "private")
        
        prompt = f"User: {user_name}\nChat type: {chat_type}\n"
        
        if message_type == "link":
            urls = context.get("urls", [])
            prompt += f"Message with links: {message}\nLinks found: {', '.join(urls)}\n"
        elif message_type == "photo":
            caption = context.get("caption", "")
            prompt += f"Shared a photo"
            if caption:
                prompt += f" with caption: {caption}"
            prompt += "\n"
        else:
            prompt += f"Message: {message}\n"
        
        prompt += "\nProvide a helpful travel planning response:"
        return prompt

    def _build_conversation_messages(
        self,
        current_message: str,
        context: Dict[str, Any],
        message_type: str,
        system_prompt: str
    ) -> List[Dict[str, Any]]:
        """Build conversation messages including history for OpenAI API"""
        chat_id = context.get("chat_id")
        
        # Start with system message
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if available
        if chat_id:
            # Get travel context summary
            travel_context = conversation_memory.get_travel_context_summary(chat_id)
            
            # Add context summary to system message if there's significant context
            if travel_context["destinations_mentioned"] or travel_context["photos_shared"] > 0:
                context_summary = self._format_travel_context(travel_context)
                # Preserve the original system prompt structure
                enhanced_system_prompt = f"{system_prompt}\n\nTravel Context Summary:\n{context_summary}"
                messages[0]["content"] = enhanced_system_prompt
            
            # Get recent conversation history
            history = conversation_memory.get_conversation_history(chat_id, max_messages=12)  # Last 6 exchanges
            
            # Check if current message is a flight query
            is_flight_query = ("航班" in current_message or "flight" in current_message.lower() or "机票" in current_message)
            
            # Convert history to OpenAI message format
            for hist_msg in history:
                # Skip very recent messages to avoid duplication
                if hist_msg.content == current_message:
                    continue
                
                # For flight queries, include previous flight responses to maintain context
                # but only if the current message is asking for alternatives/recommendations
                if is_flight_query and hist_msg.role == "assistant":
                    # Check if this assistant message contains flight plans
                    if ("方案A" in hist_msg.content or "方案B" in hist_msg.content or "方案C" in hist_msg.content):
                        # Only skip if current message is not asking for alternatives
                        if not any(word in current_message.lower() for word in ["再", "其他", "别的", "换", "重新", "推荐", "alternative", "other", "another"]):
                            continue
                    
                openai_message = {
                    "role": hist_msg.role,
                    "content": self._format_history_message(hist_msg)
                }
                messages.append(openai_message)
        
        # Add current user message
        current_user_prompt = self._build_user_prompt(current_message, context, message_type)
        messages.append({"role": "user", "content": current_user_prompt})
        
        return messages

    def _format_travel_context(self, travel_context: Dict[str, Any]) -> str:
        """Format travel context summary for system prompt"""
        context_parts = []
        
        if travel_context["destinations_mentioned"]:
            destinations = ", ".join(travel_context["destinations_mentioned"])
            context_parts.append(f"Destinations mentioned: {destinations}")
        
        if travel_context["group_size"]:
            context_parts.append(f"Travel type: {travel_context['group_size']}")
        
        if travel_context["photos_shared"] > 0:
            context_parts.append(f"Photos shared: {travel_context['photos_shared']}")
        
        if travel_context["links_shared"] > 0:
            context_parts.append(f"Links shared: {travel_context['links_shared']}")
        
        if travel_context["budget_mentions"]:
            context_parts.append("Budget discussed: Yes")
        
        return "\n".join(context_parts) if context_parts else "No previous travel context"

    def _format_history_message(self, message) -> str:
        """Format a history message for inclusion in conversation"""
        if message.message_type == "photo":
            base_content = f"[Photo shared by {message.user_name}]"
            if message.content and message.content.strip():
                base_content += f" Caption: {message.content}"
            return base_content
        elif message.message_type == "link":
            return f"[Links shared by {message.user_name}] {message.content}"
        elif message.message_type == "document":
            return f"[Document shared by {message.user_name}] {message.content}"
        else:
            return message.content

    async def _get_flight_data_if_applicable(self, message: str, context: Dict[str, Any]) -> Optional[str]:
        """Check if message is a flight query and get real-time data if applicable"""
        try:
            # Simple flight query detection
            flight_keywords = ["航班", "机票", "飞机", "flight", "airline", "airport"]
            date_patterns = ["10月", "11月", "12月", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月"]
            
            message_lower = message.lower()
            has_flight_keywords = any(keyword in message_lower for keyword in flight_keywords)
            has_dates = any(pattern in message for pattern in date_patterns)
            
            if not (has_flight_keywords and has_dates):
                return None
            
            # Extract basic flight info (simplified)
            # This is a basic implementation - you could use more sophisticated NLP here
            if "上海" in message and "东京" in message:
                origin = "PVG"
                destination = "NRT"
                
                            # Extract dates (simplified) - use current year + 1 for future dates
            current_year = datetime.now().year
            if "10月1号" in message or "10月1日" in message:
                departure_date = f"{current_year + 1}-10-01"
            elif "10月5号" in message or "10月5日" in message:
                departure_date = f"{current_year + 1}-10-05"
            else:
                departure_date = f"{current_year + 1}-10-01"  # Default
                
                # Check if we have API key configured
                if not settings.amadeus_api_key or settings.amadeus_api_key == "your_amadeus_api_key_here":
                    return None  # Skip flight search, use general recommendations
                
                # Search for flights
                logger.info(f"Searching flights: {origin} -> {destination} on {departure_date}")
                flight_results = await flight_search_service.search_flights(
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date
                )
                
                if "error" not in flight_results and flight_results.get("flights"):
                    return flight_search_service.format_flight_summary(flight_results)
                else:
                    return "Real-time flight data unavailable. Using general recommendations."
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting flight data: {e}")
            return None

    def _get_fallback_response(self, message_type: str, context: Dict[str, Any]) -> str:
        """Fallback response when LLM fails"""
        user_name = context.get("user_name", "User")
        
        fallbacks = {
            "text": f"Thanks for sharing, {user_name}! I'd love to help you plan an amazing trip. Could you tell me more about your travel preferences?",
            "photo": f"Beautiful destination, {user_name}! 📸 This looks like a great place to visit. What kind of activities interest you there?",
            "link": f"Thanks for the travel resources, {user_name}! 🔗 I'll help you make the most of these destinations.",
        }
        
        return fallbacks.get(message_type, fallbacks["text"])

    async def analyze_photo(
        self,
        bot: Bot,
        photo: PhotoSize,
        caption: str,
        context: Dict[str, Any]
    ) -> str:
        """Download and analyze photo using OpenAI Vision"""
        try:
            # Download the photo
            photo_file = await bot.get_file(photo.file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Convert to base64 for OpenAI
            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            
            # Build system prompt for photo analysis
            system_prompt = self._build_photo_analysis_prompt(context)
            
            # Build user prompt with image
            user_prompt = self._build_photo_user_prompt(caption, context)
            
            logger.info("Analyzing photo with OpenAI Vision")
            
            # Call OpenAI Vision API
            response = await self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{photo_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            analysis_result = response.choices[0].message.content.strip()
            logger.info("Successfully analyzed photo")
            
            # Generate smart follow-up questions for photo analysis
            follow_up_questions = await follow_up_service.generate_smart_follow_up_questions(
                f"[Photo shared] {caption}" if caption else "[Photo shared]", 
                analysis_result, context, max_questions=2
            )
            
            # Format response with follow-up questions
            final_response = follow_up_service.format_follow_up_response(
                analysis_result, follow_up_questions
            )
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error analyzing photo: {e}")
            return self._get_fallback_response("photo", context)

    def _build_photo_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt for photo analysis"""
        user_name = context.get("user_name", "User")
        chat_type = context.get("chat_type", "private")
        
        prompt = f"""You are {settings.bot_name}, an AI travel planning assistant with vision capabilities.
Analyze the image provided and give travel-related insights.

Key guidelines:
- Identify what's in the image (locations, food, activities, etc.)
- Provide relevant travel advice and recommendations
- If it's a menu, help with food choices and local cuisine insights
- If it's a destination photo, suggest activities and nearby attractions
- If it's travel documents, help interpret information
- Be enthusiastic and helpful
- Keep responses conversational and practical (3-5 sentences)
- Focus on actionable travel advice

"""
        
        if chat_type in ["group", "supergroup"]:
            prompt += f"Context: You're helping a group plan their trip together."
        else:
            prompt += f"Context: You're helping {user_name} with personal travel planning."
            
        return prompt

    def _build_photo_user_prompt(self, caption: str, context: Dict[str, Any]) -> str:
        """Build user prompt for photo analysis"""
        user_name = context.get("user_name", "User")
        
        prompt = f"{user_name} shared this image."
        
        if caption:
            prompt += f" They added this caption: '{caption}'"
        
        prompt += " Please analyze the image and provide helpful travel insights."
        
        return prompt

    async def analyze_document_image(
        self,
        image_bytes: bytes,
        filename: str,
        context: Dict[str, Any]
    ) -> str:
        """Analyze image document using OpenAI Vision"""
        try:
            # Convert to base64 for OpenAI
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Build system prompt for document analysis
            system_prompt = self._build_document_analysis_prompt(context, filename)
            
            # Build user prompt
            user_prompt = self._build_document_user_prompt(filename, context)
            
            logger.info(f"Analyzing document image: {filename}")
            
            # Call OpenAI Vision API
            response = await self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            analysis_result = response.choices[0].message.content.strip()
            logger.info("Successfully analyzed document image")
            
            # Generate smart follow-up questions for document analysis
            follow_up_questions = await follow_up_service.generate_smart_follow_up_questions(
                f"[Document shared] {filename}", 
                analysis_result, context, max_questions=2
            )
            
            # Format response with follow-up questions
            final_response = follow_up_service.format_follow_up_response(
                analysis_result, follow_up_questions
            )
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error analyzing document image: {e}")
            return self._get_fallback_response("photo", context)

    def _build_document_analysis_prompt(self, context: Dict[str, Any], filename: str) -> str:
        """Build system prompt for document image analysis"""
        user_name = context.get("user_name", "User")
        chat_type = context.get("chat_type", "private")
        
        prompt = f"""You are {settings.bot_name}, an AI travel planning assistant with vision capabilities.
Analyze the document/image provided and give travel-related insights.

Key guidelines:
- Identify the type of document (menu, map, ticket, brochure, etc.)
- Extract key travel information (prices, locations, times, etc.)
- If it's a menu, recommend dishes and explain local cuisine
- If it's a map or brochure, suggest routes and attractions  
- If it's travel documents, help interpret important details
- Provide practical travel advice based on what you see
- Be enthusiastic and helpful
- Keep responses conversational and actionable (3-6 sentences)

Document filename: {filename}

"""
        
        if chat_type in ["group", "supergroup"]:
            prompt += f"Context: You're helping a group plan their trip together."
        else:
            prompt += f"Context: You're helping {user_name} with personal travel planning."
            
        return prompt

    def _build_document_user_prompt(self, filename: str, context: Dict[str, Any]) -> str:
        """Build user prompt for document analysis"""
        user_name = context.get("user_name", "User")
        
        prompt = f"{user_name} shared this document: {filename}. Please analyze the image and provide helpful travel insights based on what you can see."
        
        return prompt

    async def generate_welcome_message(self, user_name: str, chat_type: str) -> str:
        """Generate personalized welcome message"""
        try:
            system_prompt = f"""You are {settings.bot_name}, a friendly travel planning assistant. 
Generate a warm, welcoming message for a new user. Keep it concise (2-3 sentences) and enthusiastic."""
            
            user_prompt = f"Generate a welcome message for {user_name} in a {chat_type} chat."
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            return f"🌍 Welcome {user_name}! I'm {settings.bot_name}, your AI travel planning assistant. Let's plan an amazing trip together! ✈️"

    async def generate_structured_travel_plan(
        self,
        context: Dict[str, Any],
        user_requirements: str = ""
    ) -> TravelPlan:
        """Generate a comprehensive structured travel plan using OpenAI"""
        try:
            chat_id = context.get("chat_id")
            user_name = context.get("user_name", "User")
            
            # Get conversation context for better planning
            travel_context = conversation_memory.get_travel_context_summary(chat_id) if chat_id else {}
            conversation_history = conversation_memory.get_recent_context(chat_id, max_messages=15) if chat_id else ""
            
            # Build system prompt for structured plan generation
            system_prompt = self._build_plan_generation_prompt()
            
            # Build user prompt with all available context
            user_prompt = self._build_plan_user_prompt(
                user_requirements, travel_context, conversation_history, context
            )
            
            logger.info(f"Generating structured travel plan for {user_name}")
            
            # Call OpenAI with JSON mode for structured output
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,  # Increase for detailed plans
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            plan_json = json.loads(response.choices[0].message.content)
            
            # Create TravelPlan object with generated data
            travel_plan = self._create_travel_plan_from_json(plan_json, context)
            
            # Save plan to storage
            plan_id = plan_storage.save_plan(travel_plan)
            
            logger.info(f"Successfully generated and saved travel plan {plan_id}")
            return travel_plan
            
        except Exception as e:
            logger.error(f"Error generating structured travel plan: {e}")
            # Return a basic fallback plan
            return self._create_fallback_plan(context, user_requirements)

    def _build_plan_generation_prompt(self) -> str:
        """Build system prompt for structured travel plan generation"""
        return f"""You are {settings.bot_name}, an expert travel planning AI. Generate comprehensive, detailed travel plans in JSON format.

IMPORTANT: You must respond with valid JSON only. No additional text outside the JSON.

The JSON structure must include:
{{
  "title": "Engaging plan title",
  "destination": "Primary destination",
  "duration": "Trip length (e.g., '5 days', '1 week')",
  "travel_type": "solo|couple|family|group|business",
  "budget_level": "budget|moderate|luxury|unlimited",
  "group_size": 1,
  "overview": "Compelling trip overview highlighting key experiences",
  "accommodations": [
    {{
      "name": "Hotel/accommodation name",
      "type": "hotel|hostel|apartment|resort",
      "location": "Area/neighborhood",
      "price_range": "$50-100/night",
      "rating": 4.5,
      "amenities": ["wifi", "breakfast", "pool"],
      "booking_notes": "Book early for best rates"
    }}
  ],
  "itinerary": [
    {{
      "day": 1,
      "date": "Optional date",
      "theme": "Day theme (e.g., 'Arrival & City Exploration')",
      "activities": [
        {{
          "name": "Activity name",
          "type": "sightseeing|adventure|cultural|food|relaxation|shopping|nightlife|nature",
          "location": "Specific location",
          "duration": "2-3 hours",
          "cost": "$10-20",
          "description": "Detailed activity description",
          "tips": "Helpful tips",
          "booking_required": false
        }}
      ],
      "meals": ["Restaurant recommendations"],
      "transportation": [
        {{
          "method": "taxi|metro|bus|walk|flight",
          "from_location": "Start point",
          "to_location": "End point",
          "cost": "$5-10",
          "duration": "30 minutes",
          "notes": "Additional transport info"
        }}
      ],
      "estimated_cost": "$80-120",
      "tips": "Daily tips and advice"
    }}
  ],
  "total_budget_estimate": "$500-800 per person",
  "packing_list": ["Essential items to pack"],
  "local_tips": ["Cultural tips and customs"],
  "emergency_info": {{
    "emergency_number": "Local emergency number",
    "embassy": "Embassy contact",
    "hospital": "Recommended hospital"
  }},
  "tags": ["adventure", "culture", "budget-friendly"]
}}

Guidelines:
- Create realistic, detailed itineraries with specific activities
- Include practical information (costs, timings, bookings)
- Provide diverse activity types for balanced experiences
- Consider local culture, weather, and logistics
- Give actionable tips and recommendations
- Ensure all costs are realistic estimates
- Include 3-7 day itineraries typically"""

    def _build_plan_user_prompt(
        self,
        user_requirements: str,
        travel_context: Dict[str, Any],
        conversation_history: str,
        context: Dict[str, Any]
    ) -> str:
        """Build user prompt for plan generation"""
        user_name = context.get("user_name", "User")
        chat_type = context.get("chat_type", "private")
        
        prompt = f"Generate a detailed travel plan for {user_name}.\n\n"
        
        # Add user requirements
        if user_requirements:
            prompt += f"User Requirements: {user_requirements}\n\n"
        
        # Add travel context if available
        if travel_context and (travel_context.get("destinations_mentioned") or travel_context.get("photos_shared", 0) > 0):
            prompt += "Previous Conversation Context:\n"
            if travel_context.get("destinations_mentioned"):
                destinations = ", ".join(travel_context["destinations_mentioned"])
                prompt += f"- Destinations discussed: {destinations}\n"
            if travel_context.get("group_size"):
                prompt += f"- Travel type: {travel_context['group_size']}\n"
            if travel_context.get("photos_shared", 0) > 0:
                prompt += f"- Photos shared: {travel_context['photos_shared']} (consider user's visual preferences)\n"
            if travel_context.get("budget_mentions"):
                prompt += "- Budget preferences discussed\n"
            prompt += "\n"
        
        # Add recent conversation for context
        if conversation_history and conversation_history != "No previous conversation history.":
            prompt += f"Recent Conversation:\n{conversation_history}\n\n"
        
        # Add specific requirements based on chat type
        if chat_type in ["group", "supergroup"]:
            prompt += "This is for a group chat - consider collaborative planning and group-friendly activities.\n\n"
        
        prompt += "Create a comprehensive travel plan in the specified JSON format. Be specific, practical, and engaging."
        
        return prompt

    def _create_travel_plan_from_json(self, plan_json: Dict[str, Any], context: Dict[str, Any]) -> TravelPlan:
        """Create TravelPlan object from JSON response"""
        try:
            # Generate unique ID
            plan_id = str(uuid.uuid4())[:8]
            
            # Extract context info
            chat_id = context.get("chat_id", 0)
            user_name = context.get("user_name", "User")
            
            # Map string enums to proper enum values
            travel_type_map = {
                "solo": TravelType.SOLO,
                "couple": TravelType.COUPLE,
                "family": TravelType.FAMILY,
                "group": TravelType.GROUP,
                "business": TravelType.BUSINESS
            }
            
            budget_map = {
                "budget": BudgetLevel.BUDGET,
                "moderate": BudgetLevel.MODERATE,
                "luxury": BudgetLevel.LUXURY,
                "unlimited": BudgetLevel.UNLIMITED
            }
            
            # Create TravelPlan with proper validation
            travel_plan = TravelPlan(
                id=plan_id,
                title=plan_json.get("title", "Travel Plan"),
                destination=plan_json.get("destination", "Unknown"),
                duration=plan_json.get("duration", "Unknown"),
                travel_dates=plan_json.get("travel_dates"),
                travel_type=travel_type_map.get(plan_json.get("travel_type", "solo"), TravelType.SOLO),
                budget_level=budget_map.get(plan_json.get("budget_level", "moderate"), BudgetLevel.MODERATE),
                group_size=plan_json.get("group_size", 1),
                overview=plan_json.get("overview", ""),
                accommodations=plan_json.get("accommodations", []),
                itinerary=plan_json.get("itinerary", []),
                total_budget_estimate=plan_json.get("total_budget_estimate", "Not specified"),
                packing_list=plan_json.get("packing_list", []),
                local_tips=plan_json.get("local_tips", []),
                emergency_info=plan_json.get("emergency_info", {}),
                created_by=user_name,
                chat_id=chat_id,
                tags=plan_json.get("tags", [])
            )
            
            return travel_plan
            
        except Exception as e:
            logger.error(f"Error creating TravelPlan from JSON: {e}")
            raise

    def _create_fallback_plan(self, context: Dict[str, Any], user_requirements: str) -> TravelPlan:
        """Create a basic fallback plan if JSON generation fails"""
        plan_id = str(uuid.uuid4())[:8]
        chat_id = context.get("chat_id", 0)
        user_name = context.get("user_name", "User")
        
        return TravelPlan(
            id=plan_id,
            title="Basic Travel Plan",
            destination="To be determined",
            duration="To be planned",
            travel_type=TravelType.SOLO,
            budget_level=BudgetLevel.MODERATE,
            overview=f"Travel plan for {user_name}. Requirements: {user_requirements}",
            itinerary=[],
            total_budget_estimate="To be calculated",
            created_by=user_name,
            chat_id=chat_id,
            tags=["basic", "needs-refinement"]
        )

    async def debug(
            self,
            messages: List[Dict[str, Any]]
    ) -> str:
        """Generate travel-focused response using OpenAI with conversation history"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web for up-to-date information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    },
                }
            }
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                # tools=tools,
                # tool_choice="auto",
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                messages.append(msg)
                for tool_call in msg.tool_calls:
                    if tool_call.function.name == "search_web":
                        print(tool_call.function)
                        args = json.loads(tool_call.function.arguments)
                        query = args.get("query")
                        ret = search_web(query)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(ret)
                        })
                print(messages)
                response2 = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                generated_response = response2.choices[0].message.content.strip()
                logger.info("Successfully generated LLM response")
                return generated_response

            generated_response = response.choices[0].message.content.strip()
            logger.info("Successfully generated LLM response")

            return generated_response

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return "error"

    async def send_media_with_text(
        self, 
        bot, 
        chat_id: int, 
        text: str, 
        media_type: str = "photo", 
        media_url: str = None, 
        media_file_id: str = None,
        caption: str = None,
        parse_mode: str = "Markdown"
    ) -> bool:
        """
        Send media (photo, video, document) with text
        
        Args:
            bot: Telegram bot instance
            chat_id: Chat ID to send to
            text: Text message to send
            media_type: Type of media ("photo", "video", "document", "animation")
            media_url: URL of the media file
            media_file_id: Telegram file ID of the media
            caption: Caption for the media
            parse_mode: Parse mode for text formatting
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Send text message first
            if text and text.strip():
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode
                )
            
            # Send media
            if media_type == "photo":
                if media_url:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=media_url,
                        caption=caption,
                        parse_mode=parse_mode
                    )
                elif media_file_id:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=media_file_id,
                        caption=caption,
                        parse_mode=parse_mode
                    )
            
            elif media_type == "video":
                if media_url:
                    await bot.send_video(
                        chat_id=chat_id,
                        video=media_url,
                        caption=caption,
                        parse_mode=parse_mode
                    )
                elif media_file_id:
                    await bot.send_video(
                        chat_id=chat_id,
                        video=media_file_id,
                        caption=caption,
                        parse_mode=parse_mode
                    )
            
            elif media_type == "document":
                if media_url:
                    await bot.send_document(
                        chat_id=chat_id,
                        document=media_url,
                        caption=caption,
                        parse_mode=parse_mode
                    )
                elif media_file_id:
                    await bot.send_document(
                        chat_id=chat_id,
                        document=media_file_id,
                        caption=caption,
                        parse_mode=parse_mode
                    )
            
            elif media_type == "animation":
                if media_url:
                    await bot.send_animation(
                        chat_id=chat_id,
                        animation=media_url,
                        caption=caption,
                        parse_mode=parse_mode
                    )
                elif media_file_id:
                    await bot.send_animation(
                        chat_id=chat_id,
                        animation=media_file_id,
                        caption=caption,
                        parse_mode=parse_mode
                    )
            
            logger.info(f"Successfully sent {media_type} with text to chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending media with text: {e}")
            return False

    def get_media_urls_for_destination(self, destination: str) -> dict:
        """
        Get media URLs for a specific destination
        
        Args:
            destination: Destination name (e.g., "Tokyo", "Paris")
        
        Returns:
            dict: Dictionary with media URLs for different types
        """
        # This is a placeholder - in a real implementation, you would:
        # 1. Use an image API (like Unsplash, Pixabay, etc.)
        # 2. Have a database of curated images
        # 3. Use a travel API that provides images
        
        media_urls = {
            "tokyo": {
                "photo": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800",
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "paris": {
                "photo": "https://images.unsplash.com/photo-1502602898536-47ad22581b52?w=800",
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "new_york": {
                "photo": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800",
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "london": {
                "photo": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800",
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            }
        }
        
        # Normalize destination name
        dest_key = destination.lower().replace(" ", "_").replace("市", "").replace("市", "")
        
        return media_urls.get(dest_key, {
            "photo": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800",  # Default travel image
            "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
        })

    def get_hotel_media_urls_for_destination(self, destination: str) -> dict:
        """
        Get hotel media URLs for a specific destination
        
        Args:
            destination: Destination name (e.g., "Tokyo", "Paris")
        
        Returns:
            dict: Dictionary with hotel media URLs
        """
        # Hotel-specific images for different destinations
        hotel_media_urls = {
            "tokyo": {
                "photo": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",  # Tokyo hotel
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "paris": {
                "photo": "https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800",  # Paris hotel
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "new_york": {
                "photo": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800",  # NYC hotel
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "london": {
                "photo": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800",  # London hotel
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "osaka": {
                "photo": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",  # Osaka hotel
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "kyoto": {
                "photo": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",  # Kyoto hotel
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "seoul": {
                "photo": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",  # Seoul hotel
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            },
            "singapore": {
                "photo": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",  # Singapore hotel
                "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            }
        }
        
        # Normalize destination name
        dest_key = destination.lower().replace(" ", "_").replace("市", "").replace("市", "")
        
        return hotel_media_urls.get(dest_key, {
            "photo": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",  # Default hotel image
            "video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
        })

    async def get_realtime_travel_info(self, destination: str, info_type: str = "general") -> Optional[str]:
        """
        Get real-time travel information using Firecrawl
        
        Args:
            destination: Destination name
            info_type: Type of information (general, hotels, restaurants, attractions)
            
        Returns:
            Formatted travel information string or None if failed
        """
        try:
            logger.info(f"Getting real-time travel info for {destination} - {info_type}")
            
            # Get travel info from Firecrawl
            travel_info = await firecrawl_service.get_travel_info(destination, info_type)
            
            if not travel_info:
                return None
            
            # Format the information for LLM
            formatted_info = self._format_firecrawl_travel_info(travel_info)
            
            return formatted_info
            
        except Exception as e:
            logger.error(f"Error getting real-time travel info for {destination}: {e}")
            return None

    async def get_realtime_flight_info(self, origin: str, destination: str) -> Optional[str]:
        """
        Get real-time flight information using Firecrawl
        
        Args:
            origin: Origin city
            destination: Destination city
            
        Returns:
            Formatted flight information string or None if failed
        """
        try:
            logger.info(f"Getting real-time flight info from {origin} to {destination}")
            
            # Get flight info from Firecrawl
            flight_info = await firecrawl_service.get_flight_info(origin, destination)
            
            if not flight_info:
                return None
            
            # Format the information for LLM
            formatted_info = self._format_firecrawl_flight_info(flight_info)
            
            return formatted_info
            
        except Exception as e:
            logger.error(f"Error getting real-time flight info from {origin} to {destination}: {e}")
            return None

    async def get_realtime_hotel_info(self, destination: str, check_in: str = None, check_out: str = None) -> Optional[str]:
        """
        Get real-time hotel information using Firecrawl
        
        Args:
            destination: Destination city
            check_in: Check-in date (optional)
            check_out: Check-out date (optional)
            
        Returns:
            Formatted hotel information string or None if failed
        """
        try:
            logger.info(f"Getting real-time hotel info for {destination}")
            
            # Get hotel info from Firecrawl
            hotel_info = await firecrawl_service.get_hotel_info(destination, check_in, check_out)
            
            if not hotel_info:
                return None
            
            # Get TripAdvisor ratings
            tripadvisor_ratings = await firecrawl_service.get_tripadvisor_hotel_ratings(destination)
            
            # Add TripAdvisor ratings to hotel info
            hotel_info["tripadvisor_ratings"] = tripadvisor_ratings
            
            # Format the information for LLM
            formatted_info = self._format_firecrawl_hotel_info(hotel_info)
            
            return formatted_info
            
        except Exception as e:
            logger.error(f"Error getting real-time hotel info for {destination}: {e}")
            return None

    def _format_firecrawl_travel_info(self, travel_info: Dict[str, Any]) -> str:
        """Format Firecrawl travel information for LLM consumption"""
        try:
            destination = travel_info.get("destination", "")
            info_type = travel_info.get("info_type", "")
            sources = travel_info.get("sources", [])
            combined_content = travel_info.get("combined_content", "")
            
            formatted = f"🌍 **{destination}的{info_type}信息** (实时数据)\n\n"
            
            if sources:
                formatted += "📚 **信息来源:**\n"
                for i, source in enumerate(sources[:3], 1):
                    title = source.get("title", "无标题")
                    url = source.get("url", "")
                    formatted += f"{i}. {title}\n   {url}\n"
                formatted += "\n"
            
            # Truncate content if too long
            if len(combined_content) > 2000:
                combined_content = combined_content[:2000] + "..."
            
            formatted += f"📝 **详细信息:**\n{combined_content}\n\n"
            formatted += "💡 *以上信息来自实时网页抓取，请以最新数据为准*"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting Firecrawl travel info: {e}")
            return "获取实时信息时出现错误"

    def _format_firecrawl_flight_info(self, flight_info: Dict[str, Any]) -> str:
        """Format Firecrawl flight information for LLM consumption"""
        try:
            origin = flight_info.get("origin", "")
            destination = flight_info.get("destination", "")
            sources = flight_info.get("sources", [])
            combined_content = flight_info.get("combined_content", "")
            
            formatted = f"✈️ **{origin}到{destination}的航班信息** (实时数据)\n\n"
            
            if sources:
                formatted += "📚 **信息来源:**\n"
                for i, source in enumerate(sources[:3], 1):
                    title = source.get("title", "无标题")
                    url = source.get("url", "")
                    formatted += f"{i}. {title}\n   {url}\n"
                formatted += "\n"
            
            # Truncate content if too long
            if len(combined_content) > 2000:
                combined_content = combined_content[:2000] + "..."
            
            formatted += f"📝 **航班详情:**\n{combined_content}\n\n"
            formatted += "💡 *以上信息来自实时网页抓取，请以最新数据为准*"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting Firecrawl flight info: {e}")
            return "获取实时航班信息时出现错误"

    def _format_firecrawl_hotel_info(self, hotel_info: Dict[str, Any]) -> str:
        """Format Firecrawl hotel information for LLM consumption"""
        try:
            destination = hotel_info.get("destination", "")
            check_in = hotel_info.get("check_in", "")
            check_out = hotel_info.get("check_out", "")
            sources = hotel_info.get("sources", [])
            combined_content = hotel_info.get("combined_content", "")
            tripadvisor_ratings = hotel_info.get("tripadvisor_ratings", {})
            
            formatted = f"🏨 **{destination}的酒店信息** (实时数据)\n\n"
            
            if check_in and check_out:
                formatted += f"📅 **入住日期:** {check_in} - {check_out}\n\n"
            
            # Add TripAdvisor ratings section
            if tripadvisor_ratings:
                formatted += "⭐ **TripAdvisor评分:**\n"
                for hotel_name, rating_info in list(tripadvisor_ratings.items())[:5]:
                    rating = rating_info.get("rating", "")
                    review_count = rating_info.get("review_count", "")
                    url = rating_info.get("url", "")
                    rank = rating_info.get("rank", "")
                    
                    formatted += f"• **{hotel_name}**"
                    if rating:
                        formatted += f" - {rating}/5"
                    if review_count:
                        formatted += f" ({review_count}条评价)"
                    if rank:
                        formatted += f" (排名#{rank})"
                    if url:
                        formatted += f"\n  🔗 {url}"
                    formatted += "\n"
                formatted += "\n"
            
            if sources:
                formatted += "📚 **信息来源:**\n"
                for i, source in enumerate(sources[:3], 1):
                    title = source.get("title", "无标题")
                    url = source.get("url", "")
                    formatted += f"{i}. {title}\n   {url}\n"
                formatted += "\n"
            
            # Truncate content if too long
            if len(combined_content) > 2000:
                combined_content = combined_content[:2000] + "..."
            
            formatted += f"📝 **酒店详情:**\n{combined_content}\n\n"
            formatted += "💡 *以上信息来自实时网页抓取，请以最新数据为准*"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting Firecrawl hotel info: {e}")
            return "获取实时酒店信息时出现错误"

    async def get_influencer_hotel_recommendations(self, destination: str, platform: str = "xiaohongshu") -> Optional[str]:
        """
        Get influencer hotel recommendations from social media platforms
        
        Args:
            destination: Destination city
            platform: Platform to search ("xiaohongshu", "instagram", "both")
            
        Returns:
            Formatted influencer hotel information string or None if failed
        """
        try:
            logger.info(f"Getting influencer hotel recommendations for {destination} from {platform}")
            
            # Get influencer hotel info from Firecrawl
            influencer_info = await firecrawl_service.get_influencer_hotels(destination, platform)
            
            if not influencer_info:
                return None
            
            # Get TripAdvisor ratings for the recommended hotels
            hotel_recommendations = influencer_info.get("hotel_recommendations", [])
            hotel_names = [hotel.get("hotel_name", "") for hotel in hotel_recommendations if hotel.get("hotel_name")]
            
            if hotel_names:
                tripadvisor_ratings = await firecrawl_service.get_tripadvisor_hotel_ratings(destination, hotel_names)
                influencer_info["tripadvisor_ratings"] = tripadvisor_ratings
            
            # Format the information for LLM
            formatted_info = self._format_influencer_hotel_info(influencer_info)
            
            return formatted_info
            
        except Exception as e:
            logger.error(f"Error getting influencer hotel recommendations for {destination}: {e}")
            return None

    def _format_influencer_hotel_info(self, influencer_info: Dict[str, Any]) -> str:
        """Format influencer hotel information for LLM consumption"""
        try:
            destination = influencer_info.get("destination", "")
            platform = influencer_info.get("platform", "")
            influencer_posts = influencer_info.get("influencer_posts", [])
            hotel_recommendations = influencer_info.get("hotel_recommendations", [])
            tripadvisor_ratings = influencer_info.get("tripadvisor_ratings", {})
            
            formatted = f"🌟 **{destination}网红酒店推荐** (来自{platform}平台)\n\n"
            
            # Add influencer posts section
            if influencer_posts:
                formatted += "📱 **网红博主推荐:**\n"
                for i, post in enumerate(influencer_posts[:5], 1):
                    title = post.get("title", "无标题")
                    platform_name = post.get("platform", "未知平台")
                    content_preview = post.get("content_preview", "")
                    url = post.get("url", "")
                    
                    formatted += f"{i}. **{title}** ({platform_name})\n"
                    formatted += f"   {content_preview}\n"
                    if url:
                        formatted += f"   🔗 {url}\n"
                    formatted += "\n"
            
            # Add hotel recommendations section
            if hotel_recommendations:
                formatted += "🏨 **精选酒店推荐:**\n"
                for i, hotel in enumerate(hotel_recommendations[:5], 1):
                    hotel_name = hotel.get("hotel_name", "未知酒店")
                    price_range = hotel.get("price_range", "")
                    rating = hotel.get("rating", "")
                    highlights = hotel.get("highlights", [])
                    platform_name = hotel.get("platform", "未知平台")
                    source_url = hotel.get("source_url", "")
                    
                    formatted += f"{i}. **{hotel_name}** ({platform_name})\n"
                    if price_range:
                        formatted += f"   💰 价格: {price_range}\n"
                    if rating:
                        formatted += f"   ⭐ 评分: {rating}\n"
                    if highlights:
                        formatted += f"   ✨ 亮点: {', '.join(highlights[:3])}\n"
                    if source_url:
                        formatted += f"   🔗 {source_url}\n"
                    formatted += "\n"
            
            # Add TripAdvisor ratings section
            if tripadvisor_ratings:
                formatted += "⭐ **TripAdvisor评分参考:**\n"
                for hotel_name, rating_info in list(tripadvisor_ratings.items())[:5]:
                    rating = rating_info.get("rating", "")
                    review_count = rating_info.get("review_count", "")
                    url = rating_info.get("url", "")
                    rank = rating_info.get("rank", "")
                    
                    formatted += f"• **{hotel_name}**"
                    if rating:
                        formatted += f" - {rating}/5"
                    if review_count:
                        formatted += f" ({review_count}条评价)"
                    if rank:
                        formatted += f" (排名#{rank})"
                    if url:
                        formatted += f"\n  🔗 {url}"
                    formatted += "\n"
                formatted += "\n"
            
            formatted += "💡 *以上推荐来自社交媒体平台，仅供参考，请以实际预订信息为准*"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting influencer hotel info: {e}")
            return "获取网红酒店推荐时出现错误"

    def _is_hotel_query(self, message: str) -> bool:
        """Check if the message is asking about hotels"""
        hotel_keywords = [
            "酒店", "hotel", "住宿", "宾馆", "旅馆", "resort", "boutique", 
            "accommodation", "lodging", "inn", "suite", "lodge"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in hotel_keywords)

    def _extract_destination_from_message(self, message: str) -> Optional[str]:
        """Extract destination from message text"""
        message_lower = message.lower()
        
        # Map of destination keywords to normalized names
        destination_map = {
            "东京": "tokyo",
            "tokyo": "tokyo",
            "纽约": "new_york", 
            "new york": "new_york",
            "巴黎": "paris",
            "paris": "paris",
            "伦敦": "london",
            "london": "london",
            "大阪": "osaka",
            "osaka": "osaka",
            "京都": "kyoto",
            "kyoto": "kyoto",
            "首尔": "seoul",
            "seoul": "seoul",
            "新加坡": "singapore",
            "singapore": "singapore",
            "北京": "beijing",
            "beijing": "beijing",
            "上海": "shanghai",
            "shanghai": "shanghai",
            "香港": "hong_kong",
            "hong kong": "hong_kong",
            "台北": "taipei",
            "taipei": "taipei"
        }
        
        for keyword, normalized_name in destination_map.items():
            if keyword in message_lower:
                return normalized_name
        
        return None

    async def _get_tripadvisor_info_for_destination(self, destination: str) -> Optional[str]:
        """Get TripAdvisor information for a destination"""
        try:
            # Get TripAdvisor ratings
            tripadvisor_ratings = await firecrawl_service.get_tripadvisor_hotel_ratings(destination)
            
            if not tripadvisor_ratings:
                return None
            
            # Format TripAdvisor information
            formatted = "⭐ **TripAdvisor评分参考:**\n"
            for hotel_name, rating_info in list(tripadvisor_ratings.items())[:5]:
                rating = rating_info.get("rating", "")
                review_count = rating_info.get("review_count", "")
                url = rating_info.get("url", "")
                rank = rating_info.get("rank", "")
                
                formatted += f"• **{hotel_name}**"
                if rating:
                    formatted += f" - {rating}/5"
                if review_count:
                    formatted += f" ({review_count}条评价)"
                if rank:
                    formatted += f" (排名#{rank})"
                if url:
                    formatted += f"\n  🔗 {url}"
                formatted += "\n"
            
            formatted += "\n💡 *以上评分来自TripAdvisor，仅供参考*"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error getting TripAdvisor info for {destination}: {e}")
            return None

    async def _get_instagram_links_for_hotels(self, response_text: str, destination: str) -> Optional[str]:
        """Get Instagram search result links for hotels mentioned in the response"""
        try:
            logger.info(f"Extracting hotel names from response: {response_text[:200]}...")
            # Extract hotel names from the response
            hotel_names = self._extract_hotel_names_from_response(response_text)
            logger.info(f"Extracted hotel names: {hotel_names}")
            
            if not hotel_names:
                logger.info("No hotel names extracted from response")
                return None
            
            # Get Instagram search URLs for each hotel
            all_links = []
            for hotel_name in hotel_names[:3]:  # Limit to 3 hotels
                logger.info(f"Getting Instagram search for hotel: {hotel_name}")
                ig_search = await firecrawl_service.get_instagram_hotel_posts(hotel_name, destination)
                logger.info(f"Instagram search result: {ig_search}")
                if ig_search:
                    all_links.append({
                        "hotel_name": hotel_name,
                        "instagram_posts": ig_search.get("instagram_posts", []),
                        "hashtag_url": ig_search.get("hashtag_url", ""),
                        "search_query": ig_search.get("search_query", "")
                    })
            
            logger.info(f"All links collected: {all_links}")
            if not all_links:
                logger.info("No valid Instagram links found")
                return None
            
            # Format Instagram search links as buttons
            formatted = "\n\n📱 **查看酒店Instagram内容:**\n\n"
            
            for i, hotel_data in enumerate(all_links[:3], 1):  # Limit to 3 hotels
                hotel_name = hotel_data["hotel_name"]
                
                # Extract English name from hotel name
                english_name = self._extract_english_name_from_hotel(hotel_name)
                
                # Create Instagram search URL for the hotel using English name
                # Clean the English name for Instagram hashtag (remove special characters, convert to lowercase)
                clean_name = english_name.lower()
                clean_name = ''.join(c for c in clean_name if c.isalnum())  # Keep only alphanumeric characters
                instagram_search_url = f"https://www.instagram.com/explore/tags/{clean_name}/"
                
                # Create button format
                formatted += f"🔘 **{i}. {hotel_name}**\n"
                formatted += f"   👆 [点击查看Instagram内容]({instagram_search_url})\n\n"
            
            formatted += "💡 *点击按钮查看Instagram上的真实用户分享和照片*"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error getting Instagram links for hotels: {e}")
            return None

    async def _get_instagram_buttons_for_hotels(self, response_text: str, destination: str) -> Optional[List[Dict[str, str]]]:
        """Get Instagram button data for hotels mentioned in the response"""
        try:
            logger.info(f"Extracting hotel names from response: {response_text[:200]}...")
            # Extract hotel names from the response
            hotel_names = self._extract_hotel_names_from_response(response_text)
            logger.info(f"Extracted hotel names: {hotel_names}")
            
            if not hotel_names:
                logger.info("No hotel names extracted from response")
                return None
            
            # Get Instagram search URLs for each hotel
            all_links = []
            for hotel_name in hotel_names[:3]:  # Limit to 3 hotels
                logger.info(f"Getting Instagram search for hotel: {hotel_name}")
                ig_search = await firecrawl_service.get_instagram_hotel_posts(hotel_name, destination)
                logger.info(f"Instagram search result: {ig_search}")
                if ig_search:
                    all_links.append({
                        "hotel_name": hotel_name,
                        "instagram_posts": ig_search.get("instagram_posts", []),
                        "hashtag_url": ig_search.get("hashtag_url", ""),
                        "search_query": ig_search.get("search_query", "")
                    })
            
            logger.info(f"All links collected: {all_links}")
            
            # Create button data - generate buttons for all extracted hotels, even if Instagram search failed
            buttons = []
            for i, hotel_name in enumerate(hotel_names[:3], 1):  # Limit to 3 hotels
                # Extract English name from hotel name
                english_name = self._extract_english_name_from_hotel(hotel_name)
                
                # Create Instagram search URL with separate hashtags: hotel brand + destination
                # Clean the English name for Instagram hashtag (remove special characters, convert to lowercase)
                clean_brand = english_name.lower()
                clean_brand = ''.join(c for c in clean_brand if c.isalnum())  # Keep only alphanumeric characters
                
                # Get destination name for second hashtag
                destination_hashtag = self._get_destination_hashtag(destination)
                
                # Create search URL with separate hashtags (brand + destination)
                # Use Instagram's search with multiple hashtags separated by space
                search_hashtags = f"{clean_brand} {destination_hashtag}"
                instagram_search_url = f"https://www.instagram.com/explore/tags/{clean_brand}/"
                
                # Create button data with two hashtags display
                button_text = f"📱 {hotel_name}\n#{clean_brand} #{destination_hashtag}"
                buttons.append({
                    "text": button_text,
                    "url": instagram_search_url
                })
            
            logger.info(f"Generated {len(buttons)} Instagram buttons")
            return buttons
            
        except Exception as e:
            logger.error(f"Error getting Instagram buttons for hotels: {e}")
            return None

    def _get_destination_hashtag(self, destination: str) -> str:
        """Get destination hashtag for Instagram search"""
        try:
            # Map destinations to their Instagram-friendly hashtags
            destination_mapping = {
                "nagoya": "nagoya",
                "tokyo": "tokyo", 
                "osaka": "osaka",
                "kyoto": "kyoto",
                "shanghai": "shanghai",
                "beijing": "beijing",
                "hong_kong": "hongkong",
                "taipei": "taipei",
                "seoul": "seoul",
                "singapore": "singapore",
                "kuala_lumpur": "kualalumpur",
                "bangkok": "bangkok",
                "paris": "paris",
                "london": "london",
                "new_york": "newyork",
                "los_angeles": "losangeles",
                "sydney": "sydney",
                "melbourne": "melbourne",
                "phu_quoc": "phuquoc"
            }
            
            # Get the hashtag, default to destination if not found
            hashtag = destination_mapping.get(destination.lower(), destination.lower())
            return hashtag
            
        except Exception as e:
            logger.error(f"Error getting destination hashtag for {destination}: {e}")
            return destination.lower()

    def _extract_english_name_from_hotel(self, hotel_name: str) -> str:
        """Extract English name from hotel name for Instagram search"""
        try:
            import re
            
            # Look for English name in parentheses
            # Pattern: 中文名 (English Name) or 中文名（English Name）
            # Include comma, period, and other common punctuation in English names
            english_match = re.search(r'[（(]([A-Za-z\s&,.\-]+)[）)]', hotel_name)
            if english_match:
                english_name = english_match.group(1).strip()
                
                # Extract core brand name (first 1-2 words before common hotel terms)
                # Remove common hotel terms to get just the brand
                hotel_terms = ['hotel', 'resort', 'spa', 'suites', 'inn', 'lodge', 'palace', 'tower', 'plaza', 'center', 'centre', 'emerald', 'bay', 'phu', 'quoc', 'nagoya', 'associa', 'bangkok', 'mahanakhon', 'maalai']
                words = english_name.split()
                core_words = []
                
                for word in words:
                    if word.lower() not in hotel_terms:
                        core_words.append(word)
                    else:
                        break
                
                if core_words:
                    english_name = ' '.join(core_words)
                else:
                    # If no core words found, use first 2 words
                    words = english_name.split()
                    english_name = ' '.join(words[:2]) if len(words) >= 2 else words[0]
                
                # Clean up the English name - remove extra spaces and special characters
                english_name = re.sub(r'\s+', '', english_name)  # Remove spaces
                english_name = re.sub(r'[^\w]', '', english_name)  # Keep only alphanumeric
                if english_name and len(english_name) > 2:  # Make sure it's meaningful
                    return english_name
            
            # If no parentheses found, try to extract from the end of the string
            # Look for English words at the end
            english_words = re.findall(r'[A-Za-z\s&]+', hotel_name)
            if english_words:
                # Take the last English word/phrase
                last_english = english_words[-1].strip()
                last_english = re.sub(r'\s+', '', last_english)  # Remove spaces
                last_english = re.sub(r'[^\w]', '', last_english)  # Keep only alphanumeric
                if last_english and len(last_english) > 2:  # Make sure it's meaningful
                    return last_english
            
            # If no English found, try to extract meaningful English words from the beginning
            # Look for English words at the start
            english_words = re.findall(r'[A-Za-z\s&]+', hotel_name)
            if english_words:
                # Take the first English word/phrase
                first_english = english_words[0].strip()
                first_english = re.sub(r'\s+', '', first_english)  # Remove spaces
                first_english = re.sub(r'[^\w]', '', first_english)  # Keep only alphanumeric
                if first_english and len(first_english) > 2:  # Make sure it's meaningful
                    return first_english
            
            # If still no English found, use a generic name based on the hotel name
            # Extract the first meaningful part before any Chinese characters
            chinese_match = re.search(r'^([A-Za-z\s&]+)', hotel_name)
            if chinese_match:
                generic_name = chinese_match.group(1).strip()
                generic_name = re.sub(r'\s+', '', generic_name)  # Remove spaces
                generic_name = re.sub(r'[^\w]', '', generic_name)  # Keep only alphanumeric
                if generic_name and len(generic_name) > 2:
                    return generic_name
            
            # Last resort: try to extract meaningful keywords from Chinese hotel name
            # Map common Chinese hotel brand names to English equivalents
            brand_mapping = {
                "万豪": "Marriott",
                "希尔顿": "Hilton", 
                "凯悦": "Hyatt",
                "大仓": "Okura",
                "东急": "Tokyu",
                "丽思卡尔顿": "RitzCarlton",
                "四季": "FourSeasons",
                "文华东方": "MandarinOriental",
                "香格里拉": "ShangriLa",
                "洲际": "InterContinental",
                "威斯汀": "Westin",
                "喜来登": "Sheraton",
                "皇冠假日": "CrownPlaza",
                "假日": "HolidayInn",
                "索菲特": "Sofitel",
                "雅高": "Accor",
                "瑰丽": "Rosewood",
                "柏悦": "ParkHyatt",
                "瑞吉": "StRegis",
                "艾迪逊": "EDITION",
                "安达仕": "Andaz",
                "君悦": "GrandHyatt",
                "凯宾斯基": "Kempinski",
                "朗廷": "Langham",
                "半岛": "Peninsula",
                "华尔道夫": "Waldorf",
                "康莱德": "Conrad",
                "JW万豪": "JWMarriott",
                "威斯汀": "Westin",
                "喜来登": "Sheraton"
            }
            
            # Try to find brand names in the hotel name
            for chinese_brand, english_brand in brand_mapping.items():
                if chinese_brand in hotel_name:
                    return english_brand
            
            # If no brand found, try to extract city name and use it
            city_mapping = {
                "名古屋": "Nagoya",
                "东京": "Tokyo", 
                "大阪": "Osaka",
                "京都": "Kyoto",
                "上海": "Shanghai",
                "北京": "Beijing",
                "香港": "HongKong",
                "台北": "Taipei",
                "首尔": "Seoul",
                "新加坡": "Singapore",
                "吉隆坡": "KualaLumpur",
                "曼谷": "Bangkok",
                "巴黎": "Paris",
                "伦敦": "London",
                "纽约": "NewYork",
                "洛杉矶": "LosAngeles",
                "悉尼": "Sydney",
                "墨尔本": "Melbourne"
            }
            
            for chinese_city, english_city in city_mapping.items():
                if chinese_city in hotel_name:
                    return f"{english_city}Hotel"
            
            # Final fallback
            return "Hotel"
            
        except Exception as e:
            logger.error(f"Error extracting English name from {hotel_name}: {e}")
            return "Hotel"

    def _extract_hotel_names_from_response(self, response_text: str) -> List[str]:
        """Extract hotel names from the response text"""
        try:
            import re
            
            hotel_names = []
            lines = response_text.split('\n')
            
            for line in lines:
                line = line.strip()
                # Look for lines that start with "- " or number format and contain hotel indicators
                if (line.startswith('- ') or re.match(r'^\d+\.', line)) and any(keyword in line.lower() for keyword in ['hotel', '酒店', 'resort', 'inn', 'suite', 'lodge']):
                    # Skip lines that start with "优势：" or other descriptive text
                    if line.startswith('优势：') or line.startswith('价格范围：') or line.startswith('TripAdvisor评分：'):
                        continue
                    
                    # Extract hotel name (remove the "- " or "1. " prefix)
                    if line.startswith('- '):
                        hotel_name = line[2:].strip()
                    else:
                        # Remove number prefix (e.g., "1. " -> "")
                        hotel_name = re.sub(r'^\d+\.\s*', '', line).strip()
                    
                    # Keep the full hotel name including parentheses for button generation
                    # Don't remove parentheses as they contain important English names
                    
                    # Only add if it looks like a hotel name (not descriptive text)
                    if (hotel_name and len(hotel_name) > 3 and 
                        not hotel_name.startswith('优势：') and 
                        not hotel_name.startswith('价格范围：') and
                        not hotel_name.startswith('TripAdvisor评分：') and
                        not '：' in hotel_name):  # Skip lines with colons (descriptive text)
                        hotel_names.append(hotel_name)
            
            # If no hotels found with the above method, try a more general approach
            if not hotel_names:
                # Look for any line that contains hotel-related keywords
                for line in lines:
                    line = line.strip()
                    if (any(keyword in line.lower() for keyword in ['hotel', '酒店', 'resort', 'inn', 'suite', 'lodge']) and
                        not line.startswith('优势：') and 
                        not line.startswith('价格范围：') and
                        not line.startswith('TripAdvisor评分：') and
                        not '：' in line):  # Skip descriptive lines
                        # Try to extract hotel name from the line
                        # Look for patterns like "Hotel Name -" or "酒店名称 -"
                        match = re.search(r'^[-•]\s*([^-•\n]+?)(?:\s*-\s*|$)', line)
                        if match:
                            hotel_name = match.group(1).strip()
                            # Clean up the name
                            hotel_name = re.sub(r'\s*\([^)]*\)$', '', hotel_name)
                            hotel_name = re.sub(r'\s*（[^）]*）$', '', hotel_name)
                            if hotel_name and len(hotel_name) > 3:
                                hotel_names.append(hotel_name)
            
            logger.info(f"Extracted hotel names: {hotel_names}")
            return hotel_names[:5]  # Return max 5 hotel names
            
        except Exception as e:
            logger.error(f"Error extracting hotel names from response: {e}")
            return []