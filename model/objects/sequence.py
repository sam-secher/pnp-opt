from typing import Optional

from model.objects.components import Node
from model.utils.constants import EventType


class Arc:
    def __init__(self, x_i: float, y_i: float, x_j: float, y_j: float, distance: float) -> None:
        self.x_i = x_i
        self.y_i = y_i
        self.x_j = x_j
        self.y_j = y_j
        self.distance = distance

class Event:
    def __init__(self, event_type: EventType, detail: str, time: float, arc: Optional[Arc] = None) -> None:
        self.event_type = event_type
        self.detail = detail
        self.time = time
        self.arc = arc

    @staticmethod
    def pick_event(feeder: Node, time: float) -> "Event":
        detail = f"pickup_{feeder.id}_{feeder.part_type}"
        return Event(EventType.PICKUP, detail, time)

    @staticmethod
    def place_event(placement: Node, time: float) -> "Event":
        detail = f"place_{placement.id}_{placement.part_type}"
        return Event(EventType.PLACE, detail, time)

    @staticmethod
    def changeover_event(job_finish_id: str, job_start_id: str, time: float) -> "Event":
        detail = f"changover_{job_finish_id}_{job_start_id}"
        return Event(EventType.CHANGEOVER, detail, time)

    @staticmethod
    def travel_event(component_start: Node, component_finish: Node, time: float, arc: Arc, feeder_feeder: bool = False) -> "Event":
        part_type = "Feeder" if feeder_feeder else component_start.part_type
        detail = f"travel_{component_start.id}-{part_type}-{component_finish.id}-{component_finish.part_type}"
        return Event(EventType.TRAVEL, detail, time, arc)

    def __repr__(self) -> str:
        return f"<{self.detail!r}>"
