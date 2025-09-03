#!/usr/bin/env python3
"""
Test script to verify web link generation
"""

import requests
import json

def test_web_link_generation():
    """Test the web link generation process"""
    
    # Sample flight data
    flight_data = {
        'title': '上海 → 东京 航班选择',
        'route': '上海 → 东京',
        'dates': '10/1 - 10/5',
        'departure': '上海',
        'destination': '东京',
        'departure_code': 'PVG',
        'destination_code': 'NRT',
        'plans': [
            {
                'code': 'A',
                'emoji': '🅰️',
                'airline': '全日空（ANA）',
                'description': '舒适的服务与准时性',
                'segments': [
                    {
                        'date': '10月1日',
                        'flight_number': 'NH 968',
                        'departure_time': '10:20',
                        'departure_airport': '上海浦东国际机场',
                        'departure_code': 'PVG',
                        'arrival_time': '14:00',
                        'arrival_airport': '东京羽田机场',
                        'arrival_code': 'HND',
                        'duration': '3h 40m'
                    }
                ],
                'price': '¥3500-4000',
                'price_note': '近期参考总价（经济舱/成人）'
            }
        ],
        'key_points': [],
        'suggestions': []
    }
    
    try:
        # Send data to web server
        print("Sending flight data to web server...")
        response = requests.post('https://waypal.ai/api/flights',
                               json=flight_data, 
                               timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            web_url = result.get('url')
            if web_url:
                full_url = f"https://waypal.ai{web_url}"
                print(f"✅ Web link generated successfully: {full_url}")
                
                # Test the generated page
                print("Testing the generated page...")
                page_response = requests.get(full_url, timeout=10)
                if page_response.status_code == 200:
                    print("✅ Page loads successfully")
                    
                    # Check if map container is present
                    if 'map-container' in page_response.text:
                        print("✅ Map container found in page")
                    else:
                        print("❌ Map container not found in page")
                        
                    # Check if Leaflet is loaded
                    if 'leaflet' in page_response.text:
                        print("✅ Leaflet map library found in page")
                    else:
                        print("❌ Leaflet map library not found in page")
                        
                else:
                    print(f"❌ Page failed to load: {page_response.status_code}")
            else:
                print("❌ No URL returned from web server")
        else:
            print(f"❌ Failed to create web page: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_web_link_generation()

