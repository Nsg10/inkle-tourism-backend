# app/models/schemas.py

from typing import Optional, List
from pydantic import BaseModel, Field


class PlaceLocation(BaseModel):
    name: str
    latitude: float
    longitude: float


class WeatherInfo(BaseModel):
    temperature_c: float
    is_raining: Optional[bool] = None


class TourismAgentResult(BaseModel):
    reply: str
    place: Optional[PlaceLocation] = None
    weather: Optional[WeatherInfo] = None
    places: List[str] = Field(default_factory=list)
