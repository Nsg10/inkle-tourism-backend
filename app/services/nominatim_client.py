# app/services/nominatim_client.py

from typing import Optional

import httpx

from app.models.schemas import PlaceLocation
from app.core.logging_config import logger

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org/search"


async def geocode_place(query: str) -> Optional[PlaceLocation]:
    """
    Use Nominatim to convert a place name into (lat, lon, human-readable name).

    We prefer a short city/town/village name instead of the full display_name,
    so that replies look like: "In Bangalore it's currently 24°C..."
    """
    query = query.strip()
    if not query:
        logger.warning("geocode_place called with empty query")
        return None

    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        # you could also add "addressdetails": 1 if needed, but Nominatim
        # usually returns an 'address' field by default in the search API
    }

    headers = {
        # Nominatim requires a valid User-Agent identifying your app
        "User-Agent": (
            "inkle-tourism-assignment/0.1 "
            "(contact: niharikasgowdaniharika@gmail.com)"
        ),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                NOMINATIM_BASE_URL, params=params, headers=headers
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error(f"Nominatim request failed: {exc}")
        return None

    data = response.json()

    if not isinstance(data, list) or len(data) == 0:
        logger.info(f"Nominatim found no results for query={query!r}")
        return None

    first = data[0]

    try:
        lat = float(first.get("lat"))
        lon = float(first.get("lon"))
        display_name = first.get("display_name") or query
        address = first.get("address") or {}
    except (TypeError, ValueError) as exc:
        logger.error(f"Error parsing Nominatim response for {query!r}: {exc}")
        return None

    # Prefer a short city-style name (city/town/village/state) over full display_name
    city_name = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("state")
        or display_name
    )

    location = PlaceLocation(
        name=city_name,
        latitude=lat,
        longitude=lon,
    )

    logger.info(
        f"Nominatim geocoded {query!r} -> "
        f"{location.latitude}, {location.longitude} "
        f"(raw={display_name}, chosen_name={location.name})"
    )

    return location
