# app/agents/parent_agent.py

import re
from typing import Tuple, List, Optional

import httpx

from app.core.config import settings
from app.core.logging_config import logger
from app.models.schemas import (
    PlaceLocation,
    WeatherInfo,
    TourismAgentResult,
)
from app.services.nominatim_client import geocode_place
from app.agents.weather_agent import WeatherAgent
from app.agents.places_agent import PlacesAgent


class TourismParentAgent:
    """
    Parent agent that:
      - parses user intent (place + need_weather + need_places)
      - delegates to child agents (weather, places)
      - composes a final natural-language reply (local LLM or template)
    """

    def __init__(self) -> None:
        self.weather_agent = WeatherAgent()
        self.places_agent = PlacesAgent()

        # Local LLM (Ollama) config
        self.llm_url = settings.LOCAL_LLM_URL       # e.g. http://localhost:11434/api/generate
        self.llm_model = settings.LOCAL_LLM_MODEL   # e.g. deepseek-r1:1.5b

    # ---------------- Handle Message ----------------

    async def handle_message(self, message: str) -> TourismAgentResult:
        message = message.strip()
        if not message:
            return TourismAgentResult(
                reply=(
                    "Please tell me where you're going and whether you want "
                    "weather details, places to visit, or both."
                )
            )

        place_query, need_weather, need_places = self._parse_intent(message)
        if not place_query:
            return TourismAgentResult(
                reply=(
                    "I couldn't identify the place. Please mention the city "
                    "name clearly, for example: 'I'm going to Bangalore'."
                )
            )

        logger.info(
            f"ParentAgent: intent parsed -> place={place_query!r}, "
            f"need_weather={need_weather}, need_places={need_places}"
        )

        location = await geocode_place(place_query)
        if location is None:
            return TourismAgentResult(
                reply=(
                    "It doesn’t know this place exists. Please check the spelling or try another location."
                )
            )

        weather: Optional[WeatherInfo] = None
        places: List[str] = []

        if need_weather:
            weather = await self.weather_agent.get_weather_for_location(location)

        if need_places:
            places = await self.places_agent.get_places_for_location(location)

        reply_text = await self._compose_reply(
            original_message=message,
            location=location,
            weather=weather,
            places=places,
            need_weather=need_weather,
            need_places=need_places,
        )

        return TourismAgentResult(
            reply=reply_text,
            place=location,
            weather=weather,
            places=places,
        )

    # ---------------- Intent Parsing ----------------

    def _parse_intent(
        self, message: str
    ) -> Tuple[Optional[str], bool, bool]:
        lower = message.lower()

        need_weather = any(
            w in lower for w in ["weather", "temperature", "hot", "cold", "rain"]
        )
        need_places = any(
            w in lower
            for w in [
                "visit",
                "attractions",
                "places to visit",
                "place to visit",
                "tourist",
                "sightseeing",
                "things to do",
            ]
        )

        if not (need_weather or need_places):
            need_weather = True
            need_places = True

        place_query = self._extract_place_name(message)
        return place_query, need_weather, need_places

    def _extract_place_name(self, message: str) -> Optional[str]:
        text = message.strip()

        patterns = [
            r"\bgoing to\s+([A-Za-z\s]+?)(?:[.,!?]|$)",
            r"\bgo to\s+([A-Za-z\s]+?)(?:[.,!?]|$)",
            r"\bin\s+([A-Za-z\s]+?)(?:[.,!?]|$)",
        ]

        for p in patterns:
            m = re.search(p, text, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()

        tokens = text.split()
        caps = [t for t in tokens if t and t[0].isupper()]
        if caps:
            return caps[-1]

        return tokens[-1] if tokens else None

    # ---------------- Reply Composition ----------------

        # ---------------- Reply Composition ----------------

    async def _compose_reply(
        self,
        original_message: str,
        location: PlaceLocation,
        weather: Optional[WeatherInfo],
        places: List[str],
        need_weather: bool,
        need_places: bool,
    ) -> str:
        """
        Compose reply in the simple, example-based format from the assignment
        document. We do NOT use the LLM text here to keep the output predictable.
        """

        city = location.name

        lines: List[str] = []

        # 1) Weather-only or part of combined reply
        if need_weather and weather:
            # We don't have exact rain probability, only boolean.
            # So we keep the sentence simple.
            if weather.is_raining is True:
                rain_part = "and it is currently raining."
            elif weather.is_raining is False:
                rain_part = "and it is not raining right now."
            else:
                rain_part = ""

            lines.append(
                f"In {city} it's currently {weather.temperature_c:.0f}°C {rain_part}".strip()
            )

        # 2) Places-only or part of combined reply
        if need_places:
            if need_weather and weather:
                # Combined weather + places -> use "And these..."
                lines.append("And these are the places you can go: - - - - -")
            else:
                # Only places
                lines.append(f"In {city} these are the places you can go: - - - - -")

            if places:
                # One place per line, like the examples
                for p in places:
                    lines.append(p)
            else:
                lines.append("I couldn't find clear tourist attractions nearby.")

        # 3) If somehow neither flag is set, fall back to a generic message
        if not lines:
            lines.append(
                f"You asked about {city}, but I couldn't determine whether you want "
                "weather info, places to visit, or both. Please ask again with more details."
            )

        # Join with newlines to match the examples' style
        return "\n".join(lines)


    # ---------------- Local LLM via Ollama ----------------

    async def _compose_reply_with_local_llm(
        self,
        original_message: str,
        location: PlaceLocation,
        weather: Optional[WeatherInfo],
        places: List[str],
        need_weather: bool,
        need_places: bool,
    ) -> str:
        """
        Use a local LLM (via Ollama HTTP API) to craft a clear, formatted reply
        that ALWAYS follows the expected output structure.
        """

        if not self.llm_url or not self.llm_model:
            raise RuntimeError("Local LLM URL or model not configured")

        # Prepare weather info
        temperature = (
            f"{weather.temperature_c:.1f}"
            if weather and weather.temperature_c is not None
            else None
        )

        rain_chance = "100" if (weather and weather.is_raining) else "0"

        # Prepare places list
        place_lines = "\n".join([f"- {p}" for p in places]) if places else ""

        # Context for LLM
        context = {
            "original_message": original_message,
            "city": location.name,
            "temperature_c": temperature,
            "rain_probability_percent": rain_chance,
            "places": places,
            "need_weather": need_weather,
            "need_places": need_places,
        }

        system_prompt = """
You are a tourism assistant. You must ALWAYS follow EXACTLY the following output rules:

1. NEVER write more than 2 short lines before the places list.
2. NEVER write additional sentences before or after the response.
3. NEVER add emojis.
4. NEVER summarize. NEVER explain. NEVER talk about weather sources or tools.
5. ONLY output in this exact format:

### If ONLY weather is requested:
In <CITY> it's currently <TEMP>°C with a chance of <RAIN>% to rain.

### If ONLY places are requested:
In <CITY> these are the places you can go:
- Place 1
- Place 2
- Place 3

### If BOTH weather & places are requested:
In <CITY> it's currently <TEMP>°C with a chance of <RAIN>% to rain.
And these are the places you can go:
- Place 1
- Place 2
- Place 3

###Important:
If the place is not found (location is None), reply with:
"It doesn’t know this place exists."
Do not write anything else.


Absolutely NO other text is allowed.
"""

        user_prompt = f"""
Context JSON:
{context}

Generate the reply STRICTLY following the formatting rules above.
"""

        payload = {
            "model": self.llm_model,
            "prompt": system_prompt + "\n" + user_prompt,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=40.0) as client:
            resp = await client.post(self.llm_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Ollama /api/generate response format
        output = (
            data.get("response")
            or data.get("message", {}).get("content", "")
        )

        if not output:
            raise RuntimeError("Local LLM returned empty output")

        return output.strip()
