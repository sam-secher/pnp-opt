from collections.abc import Iterable
from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyArrowPatch, Rectangle

from model.utils.constants import EventType

if TYPE_CHECKING:
    from model.objects.components import Node
    from model.objects.sequence import Event

PART_COLOR = {
    "Resistor": "red",
    "Capacitor": "blue",
    "Microchip": "green",
}


def _generate_shades_rgb(base_color: str, n: int) -> list[tuple[float, float, float]]:
    """Generate progressively lighter shades of a base colour."""
    base_rgb = np.array(to_rgb(base_color))
    shades: list[tuple[float, float, float]] = []
    for i in range(n):
        mix = 0.3 + 0.7 * (i / max(1, n - 1))  # start darker, lighten gradually
        shade = base_rgb * mix + np.ones(3) * (1 - mix)
        shades.append(tuple(shade))
    return shades

def min_rectangle_with_padding(feeders: Iterable["Node"], placements: Iterable["Node"], gap: float = 1.0) -> tuple[float, tuple[float, float, float, float]]:
    # tight bbox from placements
    px = [n.x for n in placements]
    py = [n.y for n in placements]
    x_min, x_max = min(px), max(px)
    y_min, y_max = min(py), max(py)

    # For each feeder, how much could we expand the bbox uniformly
    # before we include that feeder? (distance to nearest bbox side, if feeder is outside)
    limits = []
    for f in feeders:
        dx_left   = max(0.0, x_min - f.x)   # feeder is left of bbox
        dx_right  = max(0.0, f.x - x_max)   # feeder is right of bbox
        dy_bottom = max(0.0, y_min - f.y)   # feeder is below bbox
        dy_top    = max(0.0, f.y - y_max)   # feeder is above bbox

        # distance to the nearest *relevant* side (0 if feeder is inside along that axis)
        # since padding grows all sides uniformly, the limiting pad for this feeder
        # is the minimum positive distance among the four sides
        d = min(d for d in (dx_left, dx_right, dy_bottom, dy_top) if d > 0) \
            if any(d > 0 for d in (dx_left, dx_right, dy_bottom, dy_top)) else float("inf")
        limits.append(d)

    # If all feeders are far away in both axes, limit is inf; otherwise take min
    cap = min(limits) if limits else float("inf")
    cap = max(0.0, cap - gap)  # keep a small breathing space

    return cap, (x_min, x_max, y_min, y_max)

def plot_events_path(feeders: Iterable["Node"], placements: Iterable["Node"], events: Iterable["Event"],
                        title: str, pad_mm: float = 5.0, invert_y: bool = True, annotate_order: bool = False) -> plt.Figure:
    """Plot feeders, placements, and TRAVEL arcs, colouring each trip as a lighter shade of the part colour."""
    fig, ax = plt.subplots(figsize=(8, 6))

    cap, (x_min, x_max, y_min, y_max) = min_rectangle_with_padding(feeders, placements, gap=1.5)
    eff_pad = min(pad_mm, cap)

    # Draw PCB bounding box (looks nice)
    x_min = x_min - eff_pad
    x_max = x_max + eff_pad
    y_min = y_min - eff_pad
    y_max = y_max + eff_pad

    pcb = Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                    fill=False, edgecolor="black", linewidth=1.2, linestyle="--")
    ax.add_patch(pcb)

    label_offset = 1.5
    for f in feeders:
        ax.scatter([f.x], [f.y], marker="s", s=90, color="black")
        ax.text(f.x + label_offset, f.y + label_offset, f.id, fontsize=9, ha="left", va="bottom", color="black")

    for p in placements:
        color = PART_COLOR.get(getattr(p, "part_type", ""), "gray")
        ax.scatter([p.x], [p.y], s=36, color=color)

    # Assume trips are sequences of TRAVEL events between PICKUP events
    trips: list[list[Event]] = []
    current_trip: list[Event] = []

    for event in events:
        if event.event_type == EventType.PICKUP:
            if current_trip:
                trips.append(current_trip)
            current_trip = []
        elif event.event_type == EventType.TRAVEL:
            current_trip.append(event)
    if current_trip:
        trips.append(current_trip)

    step_counter = 1
    for trip in trips:

        part_type = None
        detail = trip[0].detail
        if "Resistor" in detail:
            part_type = "Resistor"
        elif "Capacitor" in detail:
            part_type = "Capacitor"
        elif "Microchip" in detail:
            part_type = "Microchip"
        elif detail.count("Feeder") == 2:
            continue # skip feeder-feeder arcs
        else:
            err_msg = f"Unknown part type in trip: {detail}"
            raise ValueError(err_msg)

        base_color = PART_COLOR.get(part_type, "gray")
        shades = _generate_shades_rgb(base_color, len(trip))

        for idx, event in enumerate(trip):
            if event.arc is None:
                continue

            color = to_rgb("gray") if event.detail.count("Feeder") == 2 else shades[idx] # type: ignore[assignment]

            x0, y0 = event.arc.x_i, event.arc.y_i
            x1, y1 = event.arc.x_j, event.arc.y_j
            arrow = FancyArrowPatch(
                (x0, y0), (x1, y1),
                arrowstyle="->",
                mutation_scale=8,
                linewidth=1.2,
                color=color,
                alpha=0.8,
            )
            ax.add_patch(arrow)

            if annotate_order:
                ax.text(x1, y1, str(step_counter), fontsize=8, ha="center", va="center", color="black")
            step_counter += 1

    handles = [
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="black", markersize=7, label="Feeder"),
        # plt.Line2D([0], [0], color="black", lw=1.2, label="Travel path"),
    ]
    for part, c in PART_COLOR.items():
        handles.append(plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=6, label=part))
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.05, 0.5), borderaxespad=0.0)

    ax.set_title(title)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    if invert_y:
        ax.invert_yaxis()
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.2, linewidth=0.6)

    plt.tight_layout()

    return fig
