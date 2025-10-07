from enum import Enum


class EventType(Enum):
    PICKUP = "pickup"
    PLACE = "place"
    CHANGEOVER = "changeover"
    TRAVEL_FF = "travel_feeder_feeder"
    TRAVEL_FP = "travel_feeder_placement"
    TRAVEL_PP = "travel_placement_placement"
    TRAVEL_PF = "travel_placement_feeder"
