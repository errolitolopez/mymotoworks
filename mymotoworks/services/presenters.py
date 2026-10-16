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
