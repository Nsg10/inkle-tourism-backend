# app/agents/places_agent.py

import httpx
from app.core.logging_config import logger
from app.models.schemas import PlaceLocation


# 🔥 Curated famous places
FAMOUS_PLACES = {
    "bangalore": [
        "Lalbagh Botanical Garden",
        "Cubbon Park",
        "Bangalore Palace",
        "Bannerghatta Biological Park",
        "Jawaharlal Nehru Planetarium",
        "ISKCON Temple",
        "Vidhana Soudha",
    ],
    "bengaluru": [
        "Lalbagh Botanical Garden",
        "Cubbon Park",
        "Bangalore Palace",
        "Bannerghatta Biological Park",
        "Jawaharlal Nehru Planetarium",
        "ISKCON Temple",
        "Vidhana Soudha",
    ],
    "delhi": [
        "Red Fort",
        "India Gate",
        "Qutub Minar",
        "Lotus Temple",
        "Akshardham Temple",
        "Jama Masjid",
        "Humayun's Tomb",
    ],
    "new delhi": [
        "Red Fort",
        "India Gate",
        "Qutub Minar",
        "Lotus Temple",
        "Akshardham Temple",
        "Jama Masjid",
        "Humayun's Tomb",
    ],
}


# Overpass fallback
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class PlacesAgent:
    async def get_places_for_location(self, location: PlaceLocation):

        # Convert to lowercase for matching
        loc_name = location.name.lower()

        # 🔥 Step 1: Fuzzy check curated cities
        for city in FAMOUS_PLACES:
            if city in loc_name:
                logger.info(f"Matched curated city: {city}")
                return FAMOUS_PLACES[city]

        # 🔥 Step 2: Try partial matches like "Bengaluru Urban", "Delhi District"
        for city in FAMOUS_PLACES:
            if any(word in loc_name for word in city.split()):
                logger.info(f"Matched curated city via loose match: {city}")
                return FAMOUS_PLACES[city]

        # 🔥 Step 3: If still not matched → fallback to Overpass
        logger.warning(f"No curated match for location={location.name}. Using Overpass instead.")

        query = f"""
        [out:json];
        (
          node["tourism"](around:3000,{location.latitude},{location.longitude});
          way["tourism"](around:3000,{location.latitude},{location.longitude});
        );
        out center;
        """

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(OVERPASS_URL, data=query)
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"Overpass request failed: {e}")
            return []

        data = resp.json()
        results = []

        for element in data.get("elements", []):
            name = element.get("tags", {}).get("name")
            if name:
                results.append(name)

        return results[:10]
