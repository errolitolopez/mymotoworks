"""Shape rows into the JSON the pages use. Never include password hashes."""

from mymotoworks.config import shop_time_text
from mymotoworks.domain.stock import REASONS


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


def sale_status(sale):
    """"pending" (waits for approval), "approved", "rejected" (voided before it was approved) or
    "voided" (voided after it was approved)."""
    approved = sale["approved_at"] is not None
    if sale["voided_at"] is not None:
        return "voided" if approved else "rejected"
    return "approved" if approved else "pending"


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
        "status": sale_status(sale),
        "voided": sale["voided_at"] is not None,
        "void_reason": sale["void_reason"],
        "note": sale["note"],
        "replaces": sale["replaces_sale_id"],
        "replaced_by": sale["replaced_by"],
        "lines": result_lines,
    }
    if admin:
        result["tubo"] = sum(line["tubo"] for line in result_lines)
    return result


def restock_json(restock, lines):
    """A restock with its lines. Only the admin can see restocks, so cost is always included."""
    return {
        "id": restock["id"],
        "restock_date": restock["restock_date"],
        "recorded_by": restock["user_name"],
        "recorded_at": shop_time_text(restock["created_at"]),
        "note": restock["note"],
        "total": restock["total"],
        "voided": restock["voided_at"] is not None,
        "void_reason": restock["void_reason"],
        "lines": [{
            "item_id": line["item_id"],
            "name": line["item_name"],
            "qty": line["qty"],
            "puhunan": line["puhunan"],
            "old_puhunan": line["old_puhunan"],
            "line_total": line["qty"] * line["puhunan"],
        } for line in lines],
    }


def adjustment_json(row):
    """One item changed in a batch."""
    return {
        "id": row["id"],
        "item_id": row["item_id"],
        "name": row["item_name"],
        "change": row["change"],
        "stock_before": row["stock_before"],
        "stock_after": row["stock_after"],
    }


def batch_json(batch, adjustments):
    """A save of stock changes with the items it changed."""
    return {
        "id": batch["id"],
        "kind": batch["kind"],
        "reason": batch["reason"],
        "reason_label": REASONS[batch["reason"]],
        "note": batch["note"],
        "recorded_by": batch["user_name"],
        "recorded_at": shop_time_text(batch["created_at"]),
        "adjustments": [adjustment_json(row) for row in adjustments],
    }
