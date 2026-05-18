from itertools import product

PlayerRoles = ["instructor", "agent"]
TeamColors = ["Red", "Blue"]

# Generate all unique (role, color) pairs
role_color_pairs = list(product(PlayerRoles, TeamColors))  # [('instruct', 'Red'), ('instruct', 'Blue'), ('agent', 'Red'), ('agent', 'Blue')]

def assign_role_color():
    assignments = {}
    for i, pair in enumerate(role_color_pairs):
        if i == 0:
            assignments['server'] = pair
        else:
            assignments[f'client_{i}'] = pair
    return assignments

def get_assignment(player_id: str) -> tuple[str, str]:
    """Return (role, team_color) for a given player_id."""
    assignments = assign_role_color()
    return assignments[player_id]