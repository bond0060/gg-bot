# Waypal Flight Selector

A web application for displaying and selecting flight options, deployed on waypal.ai.

## Features

- 🛫 Flight option display with multiple plans (A, B, C)
- 🎯 Interactive flight selection
- 📱 Mobile-responsive design
- 🔗 Integration with Telegram bot
- 💳 Booking form integration

## Tech Stack

- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Render
- **Domain**: waypal.ai

## API Endpoints

- `GET /` - Main page
- `GET /flights/<flight_id>` - Flight options page
- `POST /api/flights` - Store flight data
- `POST /api/flights/<flight_id>/select` - Select flight plan

## Deployment

This application is deployed on Render and accessible at https://waypal.ai

## Usage

The web application is integrated with a Telegram bot that generates flight recommendations and provides links to this web interface for flight selection and booking.