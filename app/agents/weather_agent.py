# app/agents/weather_agent.py

from typing import Optional

from app.models.schemas import PlaceLocation, WeatherInfo
from app.services.open_meteo_client import get_current_weather
from app.core.logging_config import logger


class WeatherAgent:
    async def get_weather_for_location(
        self, location: PlaceLocation
    ) -> Optional[WeatherInfo]:
        """
        Child agent responsible for fetching weather for a given location.
        """
        weather = await get_current_weather(location.latitude, location.longitude)
        if weather is None:
            logger.warning(
                f"WeatherAgent: no weather data for {location.name} "
                f"({location.latitude}, {location.longitude})"
            )
        return weather
