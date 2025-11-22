# app/services/open_meteo_client.py

from typing import Optional

import httpx

from app.models.schemas import WeatherInfo
from app.core.logging_config import logger

OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"


async def get_current_weather(latitude: float, longitude: float) -> Optional[WeatherInfo]:
    """
    Fetch current weather from Open-Meteo for the given coordinates.

    Returns:
        WeatherInfo if successful, otherwise None.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,precipitation",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPEN_METEO_BASE_URL, params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error(f"Open-Meteo request failed: {exc}")
        return None

    data = response.json()

    current = data.get("current")
    if not isinstance(current, dict):
        logger.error("Open-Meteo response missing 'current' field")
        return None

    try:
        temperature_c = float(current.get("temperature_2m"))
        precipitation = current.get("precipitation")
        is_raining: Optional[bool] = None

        if precipitation is not None:
            # If precipitation > 0, we can say it's raining
            try:
                is_raining = float(precipitation) > 0.0
            except (TypeError, ValueError):
                is_raining = None
    except (TypeError, ValueError) as exc:
        logger.error(f"Error parsing Open-Meteo response: {exc}")
        return None

    weather = WeatherInfo(
        temperature_c=temperature_c,
        is_raining=is_raining,
    )

    logger.info(
        f"Open-Meteo weather @ ({latitude}, {longitude}) -> "
        f"{weather.temperature_c}°C, is_raining={weather.is_raining}"
    )

    return weather
