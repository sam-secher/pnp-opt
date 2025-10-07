from model.objects.components import Feeder, Job, Placement
from model.utils.constants import EventType


class Event:
    def __init__(self, event_type: EventType, detail: str, time: float) -> None:
        self.event_type = event_type.value
        self.detail = detail
        self.time = time

    @staticmethod
    def pick_event(feeder: Feeder, time: float) -> "Event":
        detail = f"pickup_{feeder.id}_{feeder.part_type}"
        return Event(EventType.PICKUP, detail, time)

    @staticmethod
    def place_event(placement: Placement, time: float) -> "Event":
        detail = f"place_{placement.id}_{placement.part_type}"
        return Event(EventType.PLACE, detail, time)

    @staticmethod
    def changeover_event(job_finish: Job, job_start: Job, time: float) -> "Event":
        detail = f"changover_{job_finish.job_id}_{job_start.job_id}"
        return Event(EventType.CHANGEOVER, detail, time)

    @staticmethod
    def travel_ff_event(feeder_start: Feeder, feeder_finish: Feeder, time: float) -> "Event":
        detail = f"travel_ff_{feeder_start.id}_{feeder_finish.id}"
        return Event(EventType.TRAVEL_FF, detail, time)

    @staticmethod
    def travel_fp_event(feeder: Feeder, placement: Placement, time: float) -> "Event":
        detail = f"travel_fp_{feeder.id}_{placement.id}"
        return Event(EventType.TRAVEL_FP, detail, time)

    @staticmethod
    def travel_pp_event(placement_start: Placement, placement_finish: Placement, time: float) -> "Event":
        detail = f"travel_pp_{placement_start.id}_{placement_finish.id}"
        return Event(EventType.TRAVEL_PP, detail, time)

    @staticmethod
    def travel_pf_event(placement: Placement, feeder: Feeder, time: float) -> "Event":
        detail = f"travel_pf_{placement.id}_{feeder.id}"
        return Event(EventType.TRAVEL_PF, detail, time)
