#!/usr/bin/env python3
"""
Flight Selector Web Server - Production Version
Deployed to waypal.ai
"""

import json
import logging
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# In-memory storage for flight data (in production, use a database)
flight_data_storage = {}

@app.route('/')
def index():
    """Main page"""
    return render_template('flight_selector.html')

@app.route('/flights/<flight_id>')
def show_flights(flight_id: str):
    """Display flight options for a specific query"""
    flight_data = flight_data_storage.get(flight_id)
    if not flight_data:
        return "Flight data not found", 404
    
    return render_template('flight_options.html', 
                         flight_data=flight_data, 
                         flight_id=flight_id)

@app.route('/api/flights', methods=['POST'])
def store_flight_data():
    """Store flight data and return a unique ID"""
    try:
        data = request.json
        flight_id = f"flight_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(data)) % 10000}"
        
        flight_data_storage[flight_id] = data
        
        logger.info(f"Stored flight data with ID: {flight_id}")
        return jsonify({"flight_id": flight_id, "url": f"/flights/{flight_id}"})
    
    except Exception as e:
        logger.error(f"Error storing flight data: {e}")
        return jsonify({"error": "Failed to store flight data"}), 500

@app.route('/api/flights/<flight_id>/select', methods=['POST'])
def select_flight(flight_id: str):
    """Handle flight selection"""
    try:
        data = request.json
        selected_plan = data.get('plan')
        
        logger.info(f"User selected plan {selected_plan} for flight {flight_id}")
        
        # Here you would integrate with booking systems
        # For now, just return a confirmation
        return jsonify({
            "status": "success",
            "message": f"Plan {selected_plan} selected successfully",
            "next_steps": "Redirect to booking system or show booking form"
        })
    
    except Exception as e:
        logger.error(f"Error selecting flight: {e}")
        return jsonify({"error": "Failed to select flight"}), 500

if __name__ == '__main__':
    # Production configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
