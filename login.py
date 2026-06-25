#gibt den jeweiligen Spieler die Rolle und Teamfarbe für das Spiel

import random
from itertools import product

PlayerRoles = ["instructor", "agent"]
TeamColors  = ["Red", "Blue"]

def assign_role_color():
    pairs = list(product(PlayerRoles, TeamColors))
    random.shuffle(pairs)
    assignments = {"server": pairs[0]}
    for i, pair in enumerate(pairs[1:], start=1):
        assignments[f"client_{i}"] = pair
    return assignments

def get_assignment(player_id: str) -> tuple[str, str]:
    """Return (role, team_color) for a given player_id."""
    assignments = assign_role_color()
    return assignments[player_id]