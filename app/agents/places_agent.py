# app/agents/places_agent.py

from typing import List
import httpx

from app.models.schemas import PlaceLocation
from app.core.logging_config import logger

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# --------- Curated Famous Places ---------

FAMOUS_PLACES = {
    # Bangalore / Bengaluru
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

    # Delhi / New Delhi
    "delhi": [
        "Red Fort",
        "India Gate",
        "Qutub Minar",
        "Lotus Temple",
        "Akshardham Temple",
        "Humayun's Tomb",
        "Jama Masjid",
    ],
    "new delhi": [
        "Red Fort",
        "India Gate",
        "Qutub Minar",
        "Lotus Temple",
        "Akshardham Temple",
        "Humayun's Tomb",
        "Jama Masjid",
    ],

    # Goa
    "goa": [
        "Baga Beach",
        "Calangute Beach",
        "Fort Aguada",
        "Basilica of Bom Jesus",
        "Dudhsagar Falls",
        "Candolim Beach",
        "Anjuna Beach",
    ],

    # Mumbai
    "mumbai": [
        "Gateway of India",
        "Marine Drive",
        "Juhu Beach",
        "Siddhivinayak Temple",
        "Elephanta Caves",
        "Chhatrapati Shivaji Maharaj Terminus",
        "Haji Ali Dargah",
    ],

    # Hyderabad
    "hyderabad": [
        "Charminar",
        "Golconda Fort",
        "Hussain Sagar Lake",
        "Ramoji Film City",
        "Salar Jung Museum",
        "Birla Mandir",
    ],

    # Chennai
    "chennai": [
        "Marina Beach",
        "Kapaleeshwarar Temple",
        "Fort St. George",
        "Valluvar Kottam",
        "Santhome Basilica",
    ],
}


class PlacesAgent:
    """
    Agent that returns tourist places for a given location.

    Strategy:
    1) If the city matches our curated list (Bangalore, Delhi, Goa, Mumbai, etc.)
       -> return that list (most accurate for the assignment).
    2) Otherwise, use Overpass with tourism/historic/park filters and
       remove obviously non-tourist POIs (hotels, hostels, etc.).
    """

    async def get_places_for_location(
        self,
        location: PlaceLocation,
        radius_m: int = 8000,
        max_results: int = 10,
    ) -> List[str]:
        loc_name = (location.name or "").lower()

        # ----- 1) Try curated city match -----
        for city_key, places in FAMOUS_PLACES.items():
            if city_key in loc_name:
                logger.info(f"Using curated places for city match: {city_key!r}")
                return places[:max_results]

        # Also try looser word match (e.g., "South Mumbai", "Goa District")
        for city_key, places in FAMOUS_PLACES.items():
            if any(word in loc_name for word in city_key.split()):
                logger.info(
                    f"Using curated places for loose city match: {city_key!r}"
                )
                return places[:max_results]

        logger.info(
            f"No curated places for '{location.name}', falling back to Overpass."
        )

        # ----- 2) Fallback to Overpass (tourist-ish tags only) -----
        lat = location.latitude
        lon = location.longitude

        overpass_query = f"""
[out:json][timeout:25];
(
  node["tourism"~"attraction|museum|gallery|zoo|theme_park|viewpoint"]["name"](around:{radius_m},{lat},{lon});
  way["tourism"~"attraction|museum|gallery|zoo|theme_park|viewpoint"]["name"](around:{radius_m},{lat},{lon});
  node["historic"]["name"](around:{radius_m},{lat},{lon});
  way["historic"]["name"](around:{radius_m},{lat},{lon});
  node["leisure"~"park|garden"]["name"](around:{radius_m},{lat},{lon});
  way["leisure"~"park|garden"]["name"](around:{radius_m},{lat},{lon});
);
out center {max_results * 3};
"""

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(
                    OVERPASS_URL,
                    data={"data": overpass_query},
                    headers={"User-Agent": "inkle-tourism-assignment/0.1"},
                )
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(f"Overpass request failed: {exc}")
            return []

        data = resp.json()
        elements = data.get("elements", [])
        logger.info(
            f"Overpass returned {len(elements)} raw elements near ({lat}, {lon})."
        )

        names: List[str] = []
        seen = set()

        banned_substrings = [
            "hotel",
            "hostel",
            "guest house",
            "guesthouse",
            "lodge",
            "pg",
            "boys hostel",
            "girls hostel",
            "residency",
            "residence",
            "enterprise",
            "enterprises",
            "hall",
            "mahal",
            "marriage",
        ]

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name:
                continue

            lower = name.lower()
            if any(bad in lower for bad in banned_substrings):
                continue

            if name in seen:
                continue

            seen.add(name)
            names.append(name)

        names.sort()
        if len(names) > max_results:
            names = names[:max_results]

        logger.info(f"Final tourist places near ({lat}, {lon}): {names}")
        return names
