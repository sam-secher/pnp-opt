import math


def calculate_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Calculate the Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
