from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd

from model.objects.components import Job

if TYPE_CHECKING:
    from collections.abc import Sequence


class Setup:

    def __init__(self, setup_path: Path) -> None:
        self.setup_path = setup_path
        self.machine_inputs = cast("pd.Series[Any]", None)
        self.jobs_df = cast("pd.DataFrame", None)
        self.feeders_df = cast("pd.DataFrame", None)
        self.placements_df = cast("pd.DataFrame", None)
        self.jobs = cast("list[tuple[Job, int]]", [])

    def load_data(self) -> None:
        self.machine_inputs = pd.read_excel(self.setup_path, sheet_name="machine", index_col="property")["value"]
        self.tools_df = pd.read_excel(self.setup_path, sheet_name="tools")
        self.feeders_df = pd.read_excel(self.setup_path, sheet_name="feeders")
        self.jobs_df = pd.read_excel(self.setup_path, sheet_name="jobs")
        self.placements_df = pd.read_excel(self.setup_path, sheet_name="placements")

        self.jobs_df = self.jobs_df.sort_values(by="due_time_s") # greedy heuristic for now, will need to bring scheduling into optimisation
                                                                 # if introduce more complexity (feeder replacement, job margin/revenue etc)

        job_ids = cast("Sequence[str]", self.jobs_df["id"].to_numpy())

        err_msg = ""

        if self.jobs_df["id"].duplicated().any():
            err_msg += "Job IDs are not unique \n"

        if self.tools_df["part_type"].duplicated().any():
            err_msg += "Expected one-to-one mapping between part type and nozzle size"

        if self.feeders_df["id"].duplicated().any():
            err_msg += "Feeder IDs are not unique \n"

        if self.feeders_df["part_type"].duplicated().any():
            err_msg += "Expected one-to-one mapping between feeder and part type \n"

        feeders_pickup_y = self.feeders_df["pickup_y_mm"].to_numpy()
        if not np.all(feeders_pickup_y[0] == feeders_pickup_y):
            err_msg += "Expected consistent feeder pickup y \n" # assume pickup y in-line (important for determining start feeder)

        if self.placements_df.duplicated(subset=["job_id", "id"]).any():
            err_msg += "Placement IDs are not unique \n"

        if err_msg:
            raise ValueError(err_msg.strip())

        for job_id in job_ids:
            job_df = self.jobs_df[self.jobs_df["id"] == job_id]
            job_quantity = job_df["quantity"].to_numpy()[0]
            job_name = job_df["name"].to_numpy()[0]
            job_placements_df = self.placements_df[self.placements_df["job_id"] == job_id]
            self.jobs.append((Job(job_id, job_name, self.machine_inputs, self.tools_df, self.feeders_df, job_placements_df), job_quantity))

    def __repr__(self) -> str:
        return f"<Setup path={self.setup_path!r}>"
