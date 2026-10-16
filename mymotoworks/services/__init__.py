"""Use cases: one class per area. A service gets the database connection and the logged-in
user, checks the request with the domain rules, uses the repositories, and commits."""

from mymotoworks.services.auth import AuthService

__all__ = ["AuthService"]
