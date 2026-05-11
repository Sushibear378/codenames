from itertools import product

PlayerRoles = ["instruct", "agent"]
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

# Example usage
assignments = assign_role_color()
print(assignments)
# Output: {'server': ('instruct', 'Red'), 'client_1': ('instruct', 'Blue'), 'client_2': ('agent', 'Red'), 'client_3': ('agent', 'Blue')}