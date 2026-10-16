"""Shape rows into the JSON the pages use. Never include password hashes."""


def account_json(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "username": row["username"],
        "role": row["role"],
        "active": bool(row["active"]),
        "must_change_password": bool(row["must_change_password"]),
    }


def item_json(row, role):
    """An item for the page. Cost and profit (puhunan, tubo) are only for the admin: for staff the
    keys are not in the answer at all."""
    item = {
        "id": row["id"],
        "name": row["name"],
        "model": row["model"],
        "part_no": row["part_no"],
        "benta": row["benta"],
        "stock": row["stock"],
        "reorder_level": row["reorder_level"],
        "track_stock": bool(row["track_stock"]),
        "active": bool(row["active"]),
        # Untracked items have no count, so they are never low.
        "low_stock": bool(row["track_stock"]) and row["stock"] <= row["reorder_level"],
    }
    if role == "admin":
        item["puhunan"] = row["puhunan"]
        item["tubo"] = row["benta"] - row["puhunan"]
    return item
