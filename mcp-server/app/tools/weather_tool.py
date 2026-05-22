import random

def weather(location: str, units: str = "celsius") -> str:
    """Get current weather information for a location. Units can be 'celsius' or 'fahrenheit'"""
    # Mock weather data for demo
    weather_conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear", "Windy"]

    # Generate consistent "random" data based on location hash
    location_hash = sum(ord(c) for c in location)
    random.seed(location_hash)

    condition = weather_conditions[location_hash % len(weather_conditions)]
    base_temp = 15 + (location_hash % 20)  # 15-35°C

    if units.lower() == "fahrenheit":
        temp = (base_temp * 9/5) + 32
        temp_unit = "°F"
    else:
        temp = base_temp
        temp_unit = "°C"

    humidity = 40 + (location_hash % 50)  # 40-90%
    wind_speed = 5 + (location_hash % 25)  # 5-30 km/h

    # Reset random seed
    random.seed()

    return f"Weather in {location}:\n  Condition: {condition}\n  Temperature: {temp:.1f}{temp_unit}\n  Humidity: {humidity}%\n  Wind Speed: {wind_speed} km/h"
