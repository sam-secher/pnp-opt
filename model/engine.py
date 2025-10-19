
import copy
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from model.objects.components import Job, Node
from model.objects.sequence import Arc, Event
from model.objects.setup import Setup
from model.placement_model import PlacementModel
from model.utils.plot_helpers import plot_events_path


class PNPEngine:
    """Engine for running the PNP model."""

    def __init__(self, setup: Setup, save_figs: bool = False) -> None:
        self.setup = setup
        self.sequence_by_job: dict[str, list[Event]] = {}
        self.fig_by_job: dict[str, plt.Figure] = {}
        self.save_figs = save_figs

    def run(self) -> pd.DataFrame:

        def get_unique_job_id(job_id: str, job_iteration: int) -> str:
            return job_id + "-" + str(job_iteration)

        job_previous: Job | None = None
        job_iteration = 1
        feeder_last: Node | None = None
        for job, quantity in self.setup.jobs:

            sequence_for_job: list[Event] = []

            if job_previous:
                job_previous_id = get_unique_job_id(job_previous.job_id, job_iteration)
                job_iteration = 1
                job_id = get_unique_job_id(job.job_id, job_iteration)
                sequence_for_job.append(Event.changeover_event(job_previous_id, job_id, job.machine.pcb_changeover_time))

            sequence_for_trip, feeder_last = self._run_job(job, feeder_last)
            sequence_for_job.extend(sequence_for_trip)
            self.sequence_by_job[get_unique_job_id(job.job_id, job_iteration)] = sequence_for_job

            while job_iteration < quantity:
                job_iteration += 1
                sequence_for_job_next: list[Event] = []
                sequence_for_job_next.append(Event.changeover_event(get_unique_job_id(job.job_id, job_iteration - 1), get_unique_job_id(job.job_id, job_iteration), job.machine.pcb_changeover_time))
                sequence_for_job_next.extend(copy.deepcopy(sequence_for_trip))
                self.sequence_by_job[get_unique_job_id(job.job_id, job_iteration)] = sequence_for_job_next

            job_previous = job

        unique_jobs = { job.job_id : job for job, _ in self.setup.jobs }

        if self.save_figs:
            for job_id, job in unique_jobs.items():
                self.fig_by_job[job_id] = plot_events_path(job.feeders, job.placements, self.sequence_by_job[get_unique_job_id(job_id, 1)], f"{job.job_id}: {job.job_name}")

        return self.get_sequence_df()

    def get_sequence_df(self) -> pd.DataFrame:

        job_col = [job_id for job_id in self.sequence_by_job for _ in range(len(self.sequence_by_job[job_id]))]
        combined_sequence = [event for sequence in self.sequence_by_job.values() for event in sequence]

        data: dict[str, list[Any]] = {
            "job_id": job_col,
            "event_type": [],
            "detail": [],
            "x1": [],
            "y1": [],
            "x2": [],
            "y2": [],
            "distance": [],
            "time": [],
        }

        x2_prev = np.nan
        y2_prev = np.nan

        for event in combined_sequence:
            data["event_type"].append(event.event_type.value)
            data["detail"].append(event.detail)

            x1 = event.arc.x_i if event.arc else x2_prev
            y1 = event.arc.y_i if event.arc else y2_prev
            x2 = event.arc.x_j if event.arc else x2_prev
            y2 = event.arc.y_j if event.arc else y2_prev

            data["x1"].append(x1)
            data["y1"].append(y1)
            data["x2"].append(x2)
            data["y2"].append(y2)
            data["distance"].append(event.arc.distance if event.arc else 0.0)
            data["time"].append(event.time)

            x2_prev = x2
            y2_prev = y2

        sequence_df = pd.DataFrame(data)
        sequence_df.loc[0, "x1"] = sequence_df.loc[1, "x1"]
        sequence_df.loc[0, "y1"] = sequence_df.loc[1, "y1"]
        sequence_df.loc[0, "x2"] = sequence_df.loc[1, "x1"]
        sequence_df.loc[0, "y2"] = sequence_df.loc[1, "y1"]

        return sequence_df

    def _run_job(self, job: Job, feeder_previous: Node | None) -> tuple[list[Event], Node]:

        sequence_for_trip: list[Event] = []

        job.calculate_distances()
        clusters_by_part_type = job.cluster_placements()

        for feeder in job.feeders: # from left to right
            part_type = feeder.part_type
            clusters = clusters_by_part_type[part_type]

            if feeder_previous and feeder_previous.id != feeder.id:
                feeder_feeder_distance = job.feeder_feeder_distances[feeder_previous.id, feeder.id]
                arc = Arc(feeder_previous.x, feeder_previous.y, feeder.x, feeder.y, feeder_feeder_distance)
                sequence_for_trip.append(Event.travel_event(feeder_previous, feeder, feeder_feeder_distance / job.machine.travel_speed, arc))

            for cluster in clusters:
                sequence_for_trip.append(Event.pick_event(feeder, job.machine.pick_time))
                feeder_placement_distances = { placement.id: job.feeder_placement_distances[feeder.id, placement.id] for placement in cluster }

                model = PlacementModel(feeder, cluster, feeder_placement_distances, job.placement_placement_distances, job.machine.travel_speed)

                cluster_result = model.run()
                sequence_for_trip.extend(self._get_placement_events(job, cluster_result))

            feeder_previous = feeder

        return sequence_for_trip, feeder

    def _get_placement_events(self, job: Job, placement_results: pd.DataFrame) -> list[Event]:

        feeders_by_id = job.feeders_by_id
        placements_by_id = job.placements_by_id

        events: list[Event] = []

        id_i = placement_results["id_i"]
        id_j = placement_results["id_j"]
        x_i = placement_results["x_i"]
        y_i = placement_results["y_i"]
        x_j = placement_results["x_j"]
        y_j = placement_results["y_j"]
        arc_distances = placement_results["arc_distance"]
        arc_times: pd.Series[float] = placement_results["arc_time"]

        for idx in range(len(id_i)):
            arc = Arc(x_i[idx], y_i[idx], x_j[idx], y_j[idx], arc_distances[idx])
            time = arc_times[idx]

            node_start = feeders_by_id.get(id_i[idx], None)
            node_start_is_feeder = node_start is not None
            if not node_start_is_feeder:
                node_start = placements_by_id[id_i[idx]]

            node_finish = feeders_by_id.get(id_j[idx], None)
            node_finish_is_feeder = node_finish is not None
            if not node_finish_is_feeder:
                node_finish = placements_by_id[id_j[idx]]

            if not node_start:
                msg = f"Node ID {id_i[idx]} not found in feeders or placements"
                raise ValueError(msg)
            if not node_finish:
                msg = f"Node ID {id_j[idx]} not found in feeders or placements"
                raise ValueError(msg)

            events.append(Event.travel_event(node_start, node_finish, time, arc))

            if not node_finish_is_feeder:
                events.append(Event.place_event(node_finish, job.machine.place_time))

        return events
