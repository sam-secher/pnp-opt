from enum import Enum


class EventType(Enum):
    PICKUP = "pickup"
    PLACE = "place"
    CHANGEOVER = "changeover"
    TRAVEL = "travel"
