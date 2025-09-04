import logging
from typing import Optional, Dict, Any, List
from firecrawl import FirecrawlApp
from app.config.settings import settings

logger = logging.getLogger(__name__)


class FirecrawlService:
    """Service for web scraping using Firecrawl API"""
    
    def __init__(self):
        self.api_key = settings.firecrawl_api_key
        self.client = FirecrawlApp(api_key=self.api_key)
    
    async def scrape_url(self, url: str, include_links: bool = False) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL and return structured content
        
        Args:
            url: URL to scrape
            include_links: Whether to include links in the response
            
        Returns:
            Dict containing scraped content or None if failed
        """
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Scrape the URL
            scrape_result = self.client.scrape_url(
                url=url,
                params={
                    "formats": ["markdown", "html"],
                    "includeLinks": include_links,
                    "onlyMainContent": True
                }
            )
            
            if scrape_result and scrape_result.get("success"):
                return {
                    "url": url,
                    "title": scrape_result.get("data", {}).get("metadata", {}).get("title", ""),
                    "description": scrape_result.get("data", {}).get("metadata", {}).get("description", ""),
                    "content": scrape_result.get("data", {}).get("markdown", ""),
                    "html": scrape_result.get("data", {}).get("html", ""),
                    "links": scrape_result.get("data", {}).get("links", []) if include_links else [],
                    "success": True
                }
            else:
                logger.error(f"Failed to scrape URL {url}: {scrape_result}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {e}")
            return None
    
    async def search_and_scrape(self, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search for URLs related to a query and scrape them
        
        Args:
            query: Search query
            num_results: Number of results to scrape
            
        Returns:
            List of scraped content dictionaries
        """
        try:
            logger.info(f"Searching and scraping for query: {query}")
            
            # Search for URLs
            search_result = self.client.search(
                query=query,
                num_results=num_results
            )
            
            if not search_result or not search_result.get("success"):
                logger.error(f"Search failed for query: {query}")
                return []
            
            # Scrape each found URL
            scraped_results = []
            for result in search_result.get("data", []):
                url = result.get("url")
                if url:
                    scraped_content = await self.scrape_url(url)
                    if scraped_content:
                        scraped_results.append(scraped_content)
            
            return scraped_results
            
        except Exception as e:
            logger.error(f"Error in search and scrape for query {query}: {e}")
            return []
    
    async def get_travel_info(self, destination: str, info_type: str = "general") -> Optional[Dict[str, Any]]:
        """
        Get travel information for a specific destination
        
        Args:
            destination: Destination name
            info_type: Type of information (general, hotels, restaurants, attractions)
            
        Returns:
            Dict containing travel information or None if failed
        """
        try:
            # Build search query based on info type
            if info_type == "hotels":
                query = f"{destination} hotels accommodation booking"
            elif info_type == "restaurants":
                query = f"{destination} restaurants food dining"
            elif info_type == "attractions":
                query = f"{destination} attractions things to do tourism"
            else:
                query = f"{destination} travel guide tourism information"
            
            # Search and scrape
            results = await self.search_and_scrape(query, num_results=2)
            
            if results:
                # Combine results
                combined_content = {
                    "destination": destination,
                    "info_type": info_type,
                    "sources": results,
                    "combined_content": "\n\n".join([r.get("content", "") for r in results]),
                    "titles": [r.get("title", "") for r in results],
                    "urls": [r.get("url", "") for r in results]
                }
                return combined_content
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting travel info for {destination}: {e}")
            return None
    
    async def get_flight_info(self, origin: str, destination: str) -> Optional[Dict[str, Any]]:
        """
        Get flight information from travel websites
        
        Args:
            origin: Origin city
            destination: Destination city
            
        Returns:
            Dict containing flight information or None if failed
        """
        try:
            query = f"flights from {origin} to {destination} booking"
            results = await self.search_and_scrape(query, num_results=2)
            
            if results:
                return {
                    "origin": origin,
                    "destination": destination,
                    "sources": results,
                    "combined_content": "\n\n".join([r.get("content", "") for r in results]),
                    "booking_urls": [r.get("url", "") for r in results]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting flight info from {origin} to {destination}: {e}")
            return None
    
    async def get_hotel_info(self, destination: str, check_in: str = None, check_out: str = None) -> Optional[Dict[str, Any]]:
        """
        Get hotel information for a destination
        
        Args:
            destination: Destination city
            check_in: Check-in date (optional)
            check_out: Check-out date (optional)
            
        Returns:
            Dict containing hotel information or None if failed
        """
        try:
            query = f"{destination} hotels booking accommodation"
            if check_in and check_out:
                query += f" {check_in} to {check_out}"
            
            results = await self.search_and_scrape(query, num_results=2)
            
            if results:
                return {
                    "destination": destination,
                    "check_in": check_in,
                    "check_out": check_out,
                    "sources": results,
                    "combined_content": "\n\n".join([r.get("content", "") for r in results]),
                    "booking_urls": [r.get("url", "") for r in results]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting hotel info for {destination}: {e}")
            return None

    async def get_influencer_hotels(self, destination: str, platform: str = "xiaohongshu") -> Optional[Dict[str, Any]]:
        """
        Get influencer hotel recommendations from social media platforms
        
        Args:
            destination: Destination city
            platform: Platform to search ("xiaohongshu", "instagram", "both")
            
        Returns:
            Dict containing influencer hotel information or None if failed
        """
        try:
            logger.info(f"Getting influencer hotels for {destination} from {platform}")
            
            # Build platform-specific search queries
            if platform == "xiaohongshu" or platform == "both":
                xhs_query = f"小红书 {destination} 网红酒店 推荐 打卡"
                xhs_results = await self._search_social_platform(xhs_query, "xiaohongshu")
            else:
                xhs_results = []
            
            if platform == "instagram" or platform == "both":
                ig_query = f"Instagram {destination} influencer hotel recommendation"
                ig_results = await self._search_social_platform(ig_query, "instagram")
            else:
                ig_results = []
            
            # Combine results
            all_results = xhs_results + ig_results
            
            if all_results:
                return {
                    "destination": destination,
                    "platform": platform,
                    "sources": all_results,
                    "combined_content": "\n\n".join([r.get("content", "") for r in all_results]),
                    "influencer_posts": self._extract_influencer_posts(all_results),
                    "hotel_recommendations": self._extract_hotel_recommendations(all_results)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting influencer hotels for {destination}: {e}")
            return None

    async def _search_social_platform(self, query: str, platform: str) -> List[Dict[str, Any]]:
        """Search specific social media platform for content"""
        try:
            # Use platform-specific search strategies
            if platform == "xiaohongshu":
                # Search for Xiaohongshu content
                search_queries = [
                    f"site:xiaohongshu.com {query}",
                    f"小红书 {query}",
                    f"小紅書 {query}"
                ]
            elif platform == "instagram":
                # Search for Instagram content
                search_queries = [
                    f"site:instagram.com {query}",
                    f"Instagram {query}",
                    f"#{query.replace(' ', '')}"
                ]
            else:
                search_queries = [query]
            
            all_results = []
            for search_query in search_queries:
                results = await self.search_and_scrape(search_query, num_results=2)
                all_results.extend(results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Error searching {platform}: {e}")
            return []

    def _extract_influencer_posts(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract influencer post information from search results"""
        influencer_posts = []
        
        for result in results:
            content = result.get("content", "")
            title = result.get("title", "")
            url = result.get("url", "")
            
            # Look for influencer indicators
            if any(keyword in content.lower() for keyword in ["网红", "博主", "达人", "influencer", "blogger", "打卡", "推荐"]):
                influencer_posts.append({
                    "title": title,
                    "url": url,
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                    "platform": self._detect_platform(url)
                })
        
        return influencer_posts

    def _extract_hotel_recommendations(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract hotel recommendations from search results"""
        hotel_recommendations = []
        
        for result in results:
            content = result.get("content", "")
            title = result.get("title", "")
            url = result.get("url", "")
            
            # Look for hotel-related keywords
            hotel_keywords = ["酒店", "hotel", "住宿", "宾馆", "旅馆", "resort", "boutique", "网红酒店"]
            if any(keyword in content.lower() for keyword in hotel_keywords):
                # Extract hotel names and details
                hotel_info = self._parse_hotel_info(content)
                if hotel_info:
                    hotel_recommendations.append({
                        "hotel_name": hotel_info.get("name", ""),
                        "location": hotel_info.get("location", ""),
                        "price_range": hotel_info.get("price", ""),
                        "rating": hotel_info.get("rating", ""),
                        "highlights": hotel_info.get("highlights", []),
                        "source_title": title,
                        "source_url": url,
                        "platform": self._detect_platform(url)
                    })
        
        return hotel_recommendations

    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL"""
        if "xiaohongshu.com" in url or "xhslink.com" in url:
            return "xiaohongshu"
        elif "instagram.com" in url:
            return "instagram"
        elif "weibo.com" in url:
            return "weibo"
        else:
            return "other"

    def _parse_hotel_info(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse hotel information from content"""
        try:
            import re
            
            hotel_info = {}
            
            # Extract hotel name patterns
            name_patterns = [
                r"酒店名称[：:]\s*([^\n]+)",
                r"Hotel[：:]\s*([^\n]+)",
                r"入住[：:]\s*([^\n]+)",
                r"推荐[：:]\s*([^\n]+)"
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    hotel_info["name"] = match.group(1).strip()
                    break
            
            # Extract price patterns
            price_patterns = [
                r"价格[：:]\s*([^\n]+)",
                r"Price[：:]\s*([^\n]+)",
                r"¥\s*(\d+)",
                r"\$(\d+)"
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    hotel_info["price"] = match.group(1).strip()
                    break
            
            # Extract rating patterns
            rating_patterns = [
                r"评分[：:]\s*([^\n]+)",
                r"Rating[：:]\s*([^\n]+)",
                r"(\d+\.?\d*)\s*星",
                r"(\d+\.?\d*)/10"
            ]
            
            for pattern in rating_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    hotel_info["rating"] = match.group(1).strip()
                    break
            
            # Extract highlights
            highlights = []
            highlight_keywords = ["推荐理由", "亮点", "特色", "优点", "highlights", "features"]
            for keyword in highlight_keywords:
                pattern = f"{keyword}[：:]\s*([^\n]+)"
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    highlights.append(match.group(1).strip())
            
            hotel_info["highlights"] = highlights
            
            return hotel_info if hotel_info else None
            
        except Exception as e:
            logger.error(f"Error parsing hotel info: {e}")
            return None


# Global service instance
firecrawl_service = FirecrawlService()
