# app/api/chat.py

from typing import Optional, List

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.agents.parent_agent import TourismParentAgent
from app.models.schemas import (
    PlaceLocation,
    WeatherInfo,
    TourismAgentResult,
)
from app.services.nominatim_client import geocode_place
from app.services.open_meteo_client import get_current_weather
from app.services.overpass_client import get_places

router = APIRouter()

parent_agent = TourismParentAgent()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    place: Optional[PlaceLocation] = None
    weather: Optional[WeatherInfo] = None
    places: List[str] = []


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    """
    Main chat endpoint: delegates to TourismParentAgent.
    """
    result: TourismAgentResult = await parent_agent.handle_message(payload.message)

    return ChatResponse(
        reply=result.reply,
        place=result.place,
        weather=result.weather,
        places=result.places,
    )


@router.get("/debug/geocode", response_model=Optional[PlaceLocation])
async def debug_geocode(
    place: str = Query(..., description="Place name to geocode"),
):
    """
    Temporary debug endpoint to verify Nominatim client.
    Example: /api/debug/geocode?place=Bangalore
    """
    return await geocode_place(place)


@router.get("/debug/weather", response_model=Optional[WeatherInfo])
async def debug_weather(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"),
):
    """
    Temporary debug endpoint to verify Open-Meteo weather client.
    Example: /api/debug/weather?latitude=12.97&longitude=77.59
    """
    return await get_current_weather(latitude, longitude)


@router.get("/debug/places", response_model=Optional[List[str]])
async def debug_places(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"),
):
    """
    Temporary debug endpoint to verify Overpass client.
    Example: /api/debug/places?latitude=12.97&longitude=77.59
    """
    return await get_places(latitude, longitude)
