# app/services/overpass_client.py

import httpx
from typing import List, Optional

from app.core.logging_config import logger


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


async def get_places(latitude: float, longitude: float) -> Optional[List[str]]:
    """
    Fetch up to 5 tourist attractions or parks near the given location using Overpass API.
    Returns: list of place names or None on failure.
    """
    # Overpass QL query
    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"](around:2000,{latitude},{longitude});
      way["tourism"](around:2000,{latitude},{longitude});
      relation["tourism"](around:2000,{latitude},{longitude});

      node["leisure"="park"](around:2000,{latitude},{longitude});
      way["leisure"="park"](around:2000,{latitude},{longitude});
      relation["leisure"="park"](around:2000,{latitude},{longitude});
    );
    out center 20;
    """

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                OVERPASS_URL,
                data={"data": query},
                headers={"User-Agent": "inkle-tourism-agent/0.1"},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error(f"Overpass request failed: {exc}")
        return None

    data = response.json()
    elements = data.get("elements", [])

    if not elements:
        logger.info("Overpass: no attractions found for this location")
        return []

    place_names = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")

        if name:
            place_names.append(name)

        if len(place_names) >= 5:
            break

    # Deduplicate
    place_names = list(dict.fromkeys(place_names))

    logger.info(f"Overpass found {len(place_names)} places near ({latitude}, {longitude})")

    return place_names
