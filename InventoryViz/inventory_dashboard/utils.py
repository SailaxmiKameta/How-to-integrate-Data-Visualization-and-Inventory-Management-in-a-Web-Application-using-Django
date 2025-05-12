# inventory_dashboard/utils.py

def get_dummy_category_split(store):
    """
    Dynamically generates category splits for the store.
    """

    split = {
        "Groceries": 0.5,
        "Electronics": 0.3,
        "Clothing": 0.2,
    }

    # Adjust based on store_type (A, B, C, D)
    if store.store_type == 'A':
        # A - Regular stores - focus more on groceries
        split["Groceries"] += 0.1
        split["Electronics"] -= 0.05
        split["Clothing"] -= 0.05

    elif store.store_type == 'B':
        # B - Superstores - balanced
        pass  # No change

    elif store.store_type == 'C':
        # C - Specialized electronics stores
        split["Electronics"] += 0.15
        split["Groceries"] -= 0.1
        split["Clothing"] -= 0.05

    elif store.store_type == 'D':
        # D - Luxury clothing focus
        split["Clothing"] += 0.2
        split["Groceries"] -= 0.1
        split["Electronics"] -= 0.1

    # Adjust for assortment
    if store.assortment == 'c':  # Extended assortment
        split["Clothing"] += 0.05

    if store.assortment == 'a':  # Basic assortment
        split["Electronics"] -= 0.05

    # Adjust if nearby competition
    if store.competition_distance and store.competition_distance < 500:
        split["Electronics"] += 0.05

    # Normalize (ensure total = 1)
    total = sum(split.values())
    split = {k: v / total for k, v in split.items()}

    return split
