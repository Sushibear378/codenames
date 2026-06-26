# login.py – Zufällige Verteilung der 4 Rollen (Spymaster/Agent × Rot/Blau).

import random
from itertools import product

PlayerRoles = ["instructor", "agent"]
TeamColors  = ["Red", "Blue"]


def assign_role_color() -> dict:
    """Mischt alle 4 Rollen-Farb-Kombinationen und verteilt sie auf Server + 3 Clients."""
    pairs = list(product(PlayerRoles, TeamColors))
    random.shuffle(pairs)
    assignments = {"server": pairs[0]}
    for i, pair in enumerate(pairs[1:], start=1):
        assignments[f"client_{i}"] = pair
    return assignments


def get_assignment(player_id: str) -> tuple[str, str]:
    """Nur für Tests; gibt (rolle, teamfarbe) für eine Spieler-ID zurück."""
    return assign_role_color()[player_id]
