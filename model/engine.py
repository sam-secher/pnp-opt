import pandas as pd

from model.objects.components import Feeder, Job
from model.objects.sequence import Event
from model.objects.setup import Setup
from model.placement_model import PlacementModel


class PNPEngine:
    """Engine for running the PNP model."""

    def __init__(self, setup: Setup) -> None:
        self.setup = setup
        self.sequence: list[Event] = []

    def run(self) -> None:
        self.setup.load_data()

        # results_all: list[pd.DataFrame] = []
        job_previous: Job | None = None
        for job in self.setup.jobs:

            if job_previous:
                self.sequence.append(Event.changeover_event(job_previous, job, job.machine.pcb_changeover_time))

            self._run_job(job)

            # results_all.append(results_job)

            job_previous = job

    def get_sequence_df(self) -> pd.DataFrame:
        return pd.DataFrame()

    def _run_job(self, job: Job) -> None:


        job.calculate_distances()
        clusters_by_part_type = job.cluster_placements()

        feeder_previous: Feeder | None = None
        for part_type, clusters in clusters_by_part_type.items():
            feeder = job.feeder_by_part[part_type]

            if feeder_previous:
                self.sequence.append(Event.travel_ff_event(feeder_previous, feeder, job.machine.travel_speed))

            for cluster in clusters:
                self.sequence.append(Event.pick_event(feeder, job.machine.pick_time))
                feeder_placement_distances = { placement.id: job.feeder_placement_distances[feeder.id, placement.id] for placement in cluster }

                model = PlacementModel(
                    feeder, cluster, feeder_placement_distances, job.placement_placement_distances,
                    job.machine.travel_speed, job.machine.vision_align_time, job.machine.place_time
                )

                results_cluster = model.run()
                self.sequence.extend(self._get_placement_events(results_cluster))

            feeder_previous = feeder

        # return results_cluster

    def _get_placement_events(self, placement_results: pd.DataFrame) -> list[Event]:
        return []


