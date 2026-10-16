"""Shape rows into the JSON the pages use. Never include password hashes."""

from mymotoworks.config import shop_time_text


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


def sale_json(sale, lines, role):
    """A sale with its lines. Cost and profit are only for the admin."""
    admin = role == "admin"
    result_lines = []
    for line in lines:
        item = {
            "item_id": line["item_id"],
            "name": line["item_name"],
            "qty": line["qty"],
            "benta": line["benta"],
            "line_total": line["qty"] * line["benta"],
        }
        if admin:
            item["puhunan"] = line["puhunan"]
            item["tubo"] = (line["benta"] - line["puhunan"]) * line["qty"]
        result_lines.append(item)
    result = {
        "id": sale["id"],
        "sale_date": sale["sale_date"],
        "total": sale["total"],
        "recorded_by": sale["user_name"],
        "recorded_at": shop_time_text(sale["created_at"]),
        "voided": sale["voided_at"] is not None,
        "void_reason": sale["void_reason"],
        "lines": result_lines,
    }
    if admin:
        result["tubo"] = sum(line["tubo"] for line in result_lines)
    return result
