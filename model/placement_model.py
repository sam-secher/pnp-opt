import logging
from typing import Any, cast

import pandas as pd
from pyomo.environ import Binary, ConcreteModel, Constraint, NonNegativeReals, Objective, Param, RangeSet, Set, SolverFactory, Var, minimize, quicksum, value
from pyomo.opt import SolverResults, TerminationCondition

from model.objects.components import Feeder, Placement
from model.results import OptimisationResults


class PlacementModel(ConcreteModel):

    def __init__(self, feeder: Feeder, placements: list[Placement], feeder_placement_distances: dict[str, float],
                placement_placement_distances: dict[tuple[str, str], float], machine_speed: float,
                machine_align_time: float, machine_place_time: float) -> None:
        super().__init__()

        self.logger = logging.getLogger(__name__)

        self.feeder = feeder
        self.placements = placements

        self.machine_speed = machine_speed
        self.machine_align_time = machine_align_time
        self.machine_place_time = machine_place_time

        self.feeder_idx = 0
        self.n_placements = len(placements)
        self.trips = cast("list[tuple[int, int]]", {})
        self.trip_distances = cast("dict[tuple[int, int], float]", {})

        self._preprocessing(feeder_placement_distances, placement_placement_distances)

        self._set_indices()
        self._set_params()
        self._set_vars()
        self._set_constraints()
        self._set_objective()

    def run(self) -> pd.DataFrame:
        self._run_solver()
        return self._get_results()

    def _preprocessing(self, feeder_placement_distances: dict[str, float], placement_placement_distances: dict[tuple[str, str], float]) -> None:
        trips_feeder_to_placement = {
            (0, p): feeder_placement_distances[self.placements[p - 1].id]
            for p in range(1, self.n_placements + 1)
        } # feeder to initial placement

        trips_placement_to_feeder =  {
            (p, 0) : feeder_placement_distances[self.placements[p - 1].id]
            for p in range(1, self.n_placements + 1)
        } # final placement back to feeder

        trips_placement_to_placement = {
            (p1 + 1, p2 + 1) : placement_placement_distances[(self.placements[p1].id, self.placements[p2].id)]
            for p1 in range(self.n_placements) for p2 in range(self.n_placements)
            if p1 != p2
        } # placement to placement

        self.trip_distances = { **trips_feeder_to_placement, **trips_placement_to_feeder, **trips_placement_to_placement }
        self.trips = list(self.trip_distances.keys())

    def _set_indices(self) -> None:

        self.place_idx = RangeSet(1, self.n_placements)
        self.node_idx = RangeSet(0, self.n_placements) # a node is a placement or a feeder
        self.arc_idx = RangeSet(0,self.n_placements) # a arc is a trip taken, total arcs = 1 (f2p) + (num placements - 1) + 1 (p2f)
        self.arc_idx_1 = RangeSet(1, self.n_placements - 1) # for initial conditions
        self.trip_idx = Set(initialize=self.trips) # set of all possible trips

    def _set_params(self) -> None:
        self.trip_distance = Param(self.trip_idx, initialize={ (i, j): self.trip_distances[i, j] for i, j in self.trip_idx }, within=NonNegativeReals)

    def _set_vars(self) -> None:
        self.p = Var(self.trip_idx, self.arc_idx, within=Binary) # 0/1 indicator determining which trips are taken

    def _set_constraints(self) -> None:

        f = self.feeder_idx

        def c_single_arc(model: ConcreteModel, t: int) -> Constraint:
            """One trip must be taken per time step."""
            return quicksum(model.p[i, j, t] for (i, j) in model.trip_idx) == 1

        def c_start_feeder(model: ConcreteModel) -> Constraint:
            """Start at feeder."""
            return quicksum(model.p[f, j, 0] for j in self.node_idx if j != f) == 1

        def c_feeder_no_arrive_at_start(model: ConcreteModel) -> Constraint:
            """No arrival at feeder at t = 0."""
            return quicksum(model.p[i, f, 0] for i in self.node_idx if i != f) == 0

        def c_end_feeder(model: ConcreteModel) -> Constraint:
            """End at feeder."""
            return quicksum(model.p[i, f, self.n_placements] for i in self.node_idx if i != f) == 1

        def c_feeder_no_departure_at_end(model: ConcreteModel) -> Constraint:
            """No departure from feeder at t = N."""
            return quicksum(model.p[f, j, self.n_placements] for j in self.node_idx if j != f) == 0

        def c_continuity(model: ConcreteModel, v: int, t: int) -> Constraint:
            """Enforce Hamiltonian path."""
            arr = quicksum(model.p[i, v, t - 1] for i in self.node_idx if i != v)
            dep = quicksum(model.p[v, j, t] for j in self.node_idx if j != v)

            return arr == dep

        def c_placement_one_departure(model: ConcreteModel, v: int) -> Constraint:
            """One departure per node."""
            return quicksum(model.p[v, j, t] for j in self.node_idx if j != v for t in self.arc_idx) == 1

        def c_placement_one_arrival(model: ConcreteModel, v: int) -> Constraint:
            """One arrival per node."""
            return quicksum(model.p[i, v, t] for i in self.node_idx if i != v for t in self.arc_idx) == 1


        self.c_single_arc_per_step = Constraint(self.arc_idx, rule=c_single_arc)
        self.c_start_feeder = Constraint(rule=c_start_feeder)
        self.c_feeder_no_arrival_at_start = Constraint(rule=c_feeder_no_arrive_at_start)
        self.c_end_feeder = Constraint(rule=c_end_feeder)
        self.c_feeder_no_departure_at_end = Constraint(rule=c_feeder_no_departure_at_end)

        self.c_continuity = Constraint(self.place_idx, self.arc_idx_1, rule=c_continuity)
        self.c_placement_one_departure = Constraint(self.place_idx, rule=c_placement_one_departure)
        self.c_placement_one_arrival = Constraint(self.place_idx, rule=c_placement_one_arrival)

    def _set_objective(self) -> None:

        def obj_total_margin(model: ConcreteModel) -> Objective:
            """Objective function minimizing total travel distance."""
            return quicksum(
                model.trip_distance[i, j] * model.p[i, j, t]
                for i, j in model.trip_idx for t in model.arc_idx
            )

        self.obj = Objective(rule=obj_total_margin, sense=minimize)

    def _run_solver(self) -> None:
        self.logger.info("Running solver...")

        solver = SolverFactory("appsi_highs")

        solver.options["mip_rel_gap"] = 0.001   # 0.1%
        solver.options["presolve"] = "on"
        solver.options["mip_detect_symmetry"] = "true"
        # solver.options["mip_heuristic_effort"] = 1  # Range: [0, 1]
        solver.options["threads"] = 0           # 0 = auto (use all cores)

        results = cast("SolverResults", solver.solve(self, tee=True))

        if results.solver.termination_condition == TerminationCondition.optimal:
            self.logger.info("Optimal solution found.")
        elif results.solver.termination_condition == TerminationCondition.infeasible:
            self.logger.info("Infeasible model.")
        elif results.solver.termination_condition in [TerminationCondition.maxTimeLimit, TerminationCondition.feasible]:
            self.logger.info("Solver timed out.")
        else:
            err_msg = f"Solver terminated with unknown termination condition: {results.solver.termination_condition}"
            self.logger.info(err_msg)
            raise RuntimeError(err_msg)

    def _get_results(self) -> pd.DataFrame:
        self.logger.info("Saving results...")

        p_results = { (i, j, t) : value(self.p[i, j, t]) for i, j in self.trip_idx for t in self.arc_idx }

        cols = ["id", "x_i", "y_i", "x_j", "y_j", "arc_distance", "arc_time"]

        results_all: list[pd.Series[float]] = []

        for (i, j, _), val in p_results.items():
            if val == 0:
                continue


            name = self.feeder.id if i == 0 else self.placements[i - 1].id
            start_node_x = self.feeder.x if i == 0 else self.placements[i - 1].x
            start_node_y = self.feeder.y if i == 0 else self.placements[i - 1].y
            end_node_x = self.feeder.x if j == 0 else self.placements[j - 1].x
            end_node_y = self.feeder.y if j == 0 else self.placements[j - 1].y

            arc_distance = self.trip_distance[i, j]
            arc_time = arc_distance / self.machine_speed + self.machine_align_time + self.machine_place_time

            arc_result = pd.Series(data=[name,start_node_x, start_node_y, end_node_x, end_node_y, arc_distance, arc_time], index=cols)
            results_all.append(arc_result)

        return pd.concat(results_all, axis=1).T

