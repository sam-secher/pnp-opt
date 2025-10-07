from typing import Any

import pandas as pd

from model.utils.math_helpers import calculate_distance


class Placement:
    def __init__(self, placement_id: str, part_type: str, x: float, y: float) -> None:
        self.id = placement_id
        self.part_type = part_type
        self.x = x # in mm
        self.y = y # in mm

    def __repr__(self) -> str:
        return f"<{self.id!r}: {self.part_type!r}>"

class Feeder:
    def __init__(self, feeder_id: str, part_type: str, x: float, y:float) -> None:
        self.id = feeder_id
        self.part_type = part_type
        self.x = x # in mm
        self.y = y # in mm

    def __repr__(self) -> str:
        return f"<{self.id!r}: {self.part_type!r}>"

class Machine:
    def __init__(self, machine_inputs: "pd.Series[Any]") -> None:
        self.head_count: int = machine_inputs["head_count"].astype(int)
        self.head_capacity: int = machine_inputs["head_capacity"].astype(int)
        self.travel_speed: float = machine_inputs["travel_speed_mm_s"] # in mm/s
        self.pick_time: float = machine_inputs["pick_time_s"] # in s
        self.place_time: float = machine_inputs["place_time_s"] # in s
        self.vision_align_time: float = machine_inputs["vision_align_s"] # in s
        self.pcb_changeover_time: float = machine_inputs["pcb_changeover_s"] # in s

class Job:
    def __init__(self, job_id: str, job_name: str, machine_inputs: "pd.Series[Any]", feeders_df: pd.DataFrame, placements_df: pd.DataFrame) -> None:
        self.job_id = job_id
        self.job_name = job_name
        self.machine = Machine(machine_inputs)
        self.part_types = placements_df["part_type"].unique()
        self.feeders = self._get_feeders(feeders_df)
        self.placements = self._get_placements(placements_df)

        self.feeder_by_part = { feeder.part_type: feeder for feeder in self.feeders }

        self.feeder_placement_distances: dict[tuple[str, str], float] = {}
        self.feeder_feeder_distances: dict[tuple[str, str], float] = {}
        self.placement_placement_distances: dict[tuple[str, str], float] = {}

    def _get_feeders(self, feeders_df: pd.DataFrame) -> list[Feeder]:
        return [
            Feeder(feeder_id, part_type, x, y) for feeder_id, part_type, x, y
            in zip(feeders_df["id"], feeders_df["part_type"], feeders_df["pickup_x_mm"], feeders_df["pickup_y_mm"])
        ]

    def _get_placements(self, placements_df: pd.DataFrame) -> list[Placement]:
        return [
            Placement(placement_id, part_type, x, y) for placement_id, part_type, x, y
            in zip(placements_df["id"], placements_df["part_type"], placements_df["x_mm"], placements_df["y_mm"])
        ]

    def calculate_distances(self) -> None:
        for feeder in self.feeders:
            for placement in self.placements:
                distance = calculate_distance((feeder.x, feeder.y), (placement.x, placement.y))
                self.feeder_placement_distances[(feeder.id, placement.id)] = distance
                self.feeder_placement_distances[(placement.id, feeder.id)] = distance
            for feeder2 in self.feeders:
                if feeder.id != feeder2.id:
                    distance = calculate_distance((feeder.x, feeder.y), (feeder2.x, feeder2.y))
                    self.feeder_feeder_distances[(feeder.id, feeder2.id)] = distance
                    self.feeder_feeder_distances[(feeder2.id, feeder.id)] = distance

        for placement in self.placements:
            for placement2 in self.placements:
                if placement.id != placement2.id:
                    distance = calculate_distance((placement.x, placement.y), (placement2.x, placement2.y))
                    self.placement_placement_distances[(placement.id, placement2.id)] = distance
                    self.placement_placement_distances[(placement2.id, placement.id)] = distance

    def cluster_placements(self) -> dict[str, list[list[Placement]]]:
        clusters_by_part_type: dict[str, list[list[Placement]]] = { part_type: [] for part_type in self.part_types }

        clustered_placements: list[str] = [] # by ID
        part_type_by_feeder = { feeder.id: feeder.part_type for feeder in self.feeders }

        for feeder in self.feeders:
            part_type = part_type_by_feeder[feeder.id]
            placements_for_feeder = [placement for placement in self.placements if placement.part_type == part_type and placement.id not in clustered_placements]
            placements_for_feeder.sort(key=lambda x: self.feeder_placement_distances[(feeder.id, x.id)])
            clusters_for_part_type = [placements_for_feeder[i:i+self.machine.head_capacity] for i in range(0, len(placements_for_feeder), self.machine.head_capacity)]
            clusters_by_part_type[part_type] = clusters_for_part_type

        # TODO: Implement pre-solver cluster tidying algorithm (e.g. calc internal distance to centroid and try swaps between clusters)

        return clusters_by_part_type


    def __repr__(self) -> str:
        return f"<{self.job_id!r}: {self.job_name!r}>"


