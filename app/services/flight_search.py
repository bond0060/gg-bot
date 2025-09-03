import logging
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app.config.settings import settings

logger = logging.getLogger(__name__)


class FlightSearchService:
    """Service for searching real-time flight prices using Amadeus API"""
    
    def __init__(self):
        self.api_key = settings.amadeus_api_key
        self.api_secret = settings.amadeus_api_secret
        self.base_url = "https://test.api.amadeus.com/v2"  # Use test API for free tier
        self.access_token = None
        self.token_expiry = None
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "ECONOMY"
    ) -> Dict[str, Any]:
        """
        Search for flights using Amadeus API
        
        Args:
            origin: Origin airport code (e.g., "PVG")
            destination: Destination airport code (e.g., "NRT")
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (optional for one-way)
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            cabin_class: Cabin class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
        
        Returns:
            Dictionary containing flight search results
        """
        try:
            # Get access token
            await self._get_access_token()
            
            if not self.access_token:
                return {"error": "Failed to get access token"}
            
            # Build API endpoint
            endpoint = f"{self.base_url}/shopping/flight-offers"
            
            # Prepare query parameters
            params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date,
                "adults": adults,
                "currencyCode": "CNY",
                "max": 10  # Get top 10 results
            }
            
            # Add return date if specified
            if return_date:
                params["returnDate"] = return_date
            
            # Add cabin class
            if cabin_class != "ECONOMY":
                params["travelClass"] = cabin_class
            
            logger.info(f"Searching flights: {origin} -> {destination} on {departure_date}")
            
            # Make API request
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_amadeus_results(data)
                    else:
                        error_text = await response.text()
                        logger.error(f"Flight search API error: {response.status} - {error_text}")
                        return {"error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error(f"Error searching flights: {e}")
            return {"error": f"Search error: {str(e)}"}
    
    async def _get_access_token(self):
        """Get OAuth access token from Amadeus API"""
        try:
            # Check if we have a valid token
            if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
                return
            
            # Get new token
            token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=token_data) as response:
                    if response.status == 200:
                        token_response = await response.json()
                        self.access_token = token_response.get("access_token")
                        expires_in = token_response.get("expires_in", 1800)  # Default 30 minutes
                        self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)  # Buffer
                        logger.info("Successfully obtained Amadeus access token")
                    else:
                        logger.error(f"Failed to get access token: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
    
    def _parse_amadeus_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Amadeus API flight search results"""
        try:
            if "error" in data:
                return data
            
            flights = data.get("data", [])
            
            formatted_results = {
                "total_count": len(flights),
                "flights": []
            }
            
            # Process top 5 flights
            for i, flight in enumerate(flights[:5]):
                flight_info = self._format_amadeus_flight(flight)
                if flight_info:
                    formatted_results["flights"].append(flight_info)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error parsing Amadeus results: {e}")
            return {"error": f"Parsing error: {str(e)}"}
    
    def _format_amadeus_flight(self, flight: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format a single Amadeus flight result"""
        try:
            # Get pricing
            pricing = flight.get("pricingOptions", [{}])[0]
            price_info = pricing.get("fareDetailsBySegment", [{}])[0]
            
            # Get itinerary
            itineraries = flight.get("itineraries", [])
            if not itineraries:
                return None
            
            itinerary = itineraries[0]
            segments = itinerary.get("segments", [])
            
            # Format segments
            formatted_segments = []
            for segment in segments:
                segment_info = {
                    "carrier": segment.get("carrierCode", "Unknown"),
                    "flight_number": f"{segment.get('carrierCode', '')}{segment.get('number', '')}",
                    "origin": segment.get("departure", {}).get("iataCode"),
                    "destination": segment.get("arrival", {}).get("iataCode"),
                    "departure": segment.get("departure", {}).get("at"),
                    "arrival": segment.get("arrival", {}).get("at"),
                    "duration": segment.get("duration")
                }
                formatted_segments.append(segment_info)
            
            return {
                "price": {
                    "amount": pricing.get("price", {}).get("total"),
                    "currency": pricing.get("price", {}).get("currency", "CNY")
                },
                "airline": formatted_segments[0]["carrier"] if formatted_segments else "Unknown",
                "segments": formatted_segments,
                "total_duration": itinerary.get("duration"),
                "stops": len(segments) - 1
            }
            
        except Exception as e:
            logger.error(f"Error formatting Amadeus flight: {e}")
            return None
    
    def _parse_flight_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and format flight search results"""
        try:
            if "error" in data:
                return data
            
            # Extract relevant information
            itineraries = data.get("itineraries", [])
            legs = data.get("legs", [])
            segments = data.get("segments", [])
            places = data.get("places", [])
            
            # Create place lookup
            place_lookup = {place["id"]: place for place in places}
            
            # Format results
            formatted_results = {
                "search_id": data.get("sessionToken"),
                "total_count": len(itineraries),
                "flights": []
            }
            
            # Process top 5 itineraries
            for i, itinerary in enumerate(itineraries[:5]):
                flight_info = self._format_itinerary(
                    itinerary, legs, segments, place_lookup
                )
                if flight_info:
                    formatted_results["flights"].append(flight_info)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error parsing flight results: {e}")
            return {"error": f"Parsing error: {str(e)}"}
    
    def _format_itinerary(
        self, 
        itinerary: Dict[str, Any], 
        legs: List[Dict[str, Any]], 
        segments: List[Dict[str, Any]], 
        place_lookup: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Format a single itinerary into readable flight information"""
        try:
            # Get pricing
            pricing_options = itinerary.get("pricingOptions", [])
            if not pricing_options:
                return None
            
            # Get best price
            best_price = min(pricing_options, key=lambda x: x.get("price", {}).get("amount", float('inf')))
            price_info = best_price.get("price", {})
            
            # Get leg information
            leg_ids = itinerary.get("legIds", [])
            leg_details = []
            
            for leg_id in leg_ids:
                leg = next((l for l in legs if l["id"] == leg_id), None)
                if leg:
                    leg_detail = self._format_leg(leg, segments, place_lookup)
                    if leg_detail:
                        leg_details.append(leg_detail)
            
            return {
                "price": {
                    "amount": price_info.get("amount"),
                    "currency": price_info.get("currency", "CNY")
                },
                "airline": best_price.get("agents", [{}])[0].get("name", "Unknown"),
                "legs": leg_details,
                "booking_url": best_price.get("items", [{}])[0].get("url")
            }
            
        except Exception as e:
            logger.error(f"Error formatting itinerary: {e}")
            return None
    
    def _format_leg(
        self, 
        leg: Dict[str, Any], 
        segments: List[Dict[str, Any]], 
        place_lookup: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Format a single leg of the journey"""
        try:
            # Get segment information
            segment_ids = leg.get("segmentIds", [])
            segment_details = []
            
            for segment_id in segment_ids:
                segment = next((s for s in segments if s["id"] == segment_id), None)
                if segment:
                    segment_detail = self._format_segment(segment, place_lookup)
                    if segment_detail:
                        segment_details.append(segment_detail)
            
            if not segment_details:
                return None
            
            # Get origin and destination from first and last segments
            origin = segment_details[0]["origin"]
            destination = segment_details[-1]["destination"]
            
            return {
                "origin": origin,
                "destination": destination,
                "departure": leg.get("departure"),
                "arrival": leg.get("arrival"),
                "duration": leg.get("durationInMinutes"),
                "segments": segment_details
            }
            
        except Exception as e:
            logger.error(f"Error formatting leg: {e}")
            return None
    
    def _format_segment(
        self, 
        segment: Dict[str, Any], 
        place_lookup: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Format a single flight segment"""
        try:
            origin_id = segment.get("originPlaceId")
            destination_id = segment.get("destinationPlaceId")
            
            origin = place_lookup.get(origin_id, {}).get("iata", "Unknown")
            destination = place_lookup.get(destination_id, {}).get("iata", "Unknown")
            
            return {
                "origin": origin,
                "destination": destination,
                "departure": segment.get("departure"),
                "arrival": segment.get("arrival"),
                "duration": segment.get("durationInMinutes"),
                "carrier": segment.get("marketingCarrier", {}).get("name", "Unknown"),
                "flight_number": segment.get("marketingCarrier", {}).get("flightNumber", "Unknown")
            }
            
        except Exception as e:
            logger.error(f"Error formatting segment: {e}")
            return None
    
    async def get_airport_code(self, city_name: str) -> Optional[str]:
        """Get airport code for a city name"""
        # Common airport mappings
        airport_mapping = {
            "上海": "PVG",  # Shanghai Pudong
            "东京": "NRT",  # Tokyo Narita
            "北京": "PEK",  # Beijing Capital
            "广州": "CAN",  # Guangzhou Baiyun
            "深圳": "SZX",  # Shenzhen Bao'an
            "成都": "CTU",  # Chengdu Shuangliu
            "杭州": "HGH",  # Hangzhou Xiaoshan
            "南京": "NKG",  # Nanjing Lukou
            "武汉": "WUH",  # Wuhan Tianhe
            "西安": "XIY",  # Xi'an Xianyang
            "大阪": "KIX",  # Osaka Kansai
            "名古屋": "NGO",  # Nagoya Chubu
            "福冈": "FUK",  # Fukuoka
            "札幌": "CTS",  # Sapporo New Chitose
            "冲绳": "OKA",  # Okinawa Naha
        }
        
        return airport_mapping.get(city_name)
    
    def format_flight_summary(self, results: Dict[str, Any]) -> str:
        """Format flight results into a readable summary"""
        if "error" in results:
            return f"❌ 抱歉，查询航班时出现错误: {results['error']}"
        
        if not results.get("flights"):
            return "❌ 没有找到符合条件的航班"
        
        summary = "✈️ **航班查询结果**\n\n"
        
        for i, flight in enumerate(results["flights"][:3], 1):  # Show top 3
            price = flight["price"]
            summary += f"**{i}. {price['amount']} {price['currency']}**\n"
            
            for leg in flight["legs"]:
                summary += f"   {leg['origin']} → {leg['destination']}\n"
                summary += f"   🕐 {leg['departure']} - {leg['arrival']}\n"
                summary += f"   ⏱️ {leg['duration']}分钟\n"
                
                for segment in leg["segments"]:
                    summary += f"   ✈️ {segment['carrier']} {segment['flight_number']}\n"
            
            summary += "\n"
        
        summary += "💡 *价格可能会随时变动，建议尽快预订*"
        return summary


# Global flight search service
flight_search_service = FlightSearchService()
