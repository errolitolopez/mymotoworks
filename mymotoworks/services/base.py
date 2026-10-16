"""The base class of the services."""

from mymotoworks.repositories import UserRepository


class Service:
    """A use case runs inside one service method: it checks the request, changes data through
    the repositories, and commits only when everything worked. On an error (mymotoworks.errors)
    it stops, and nothing it changed is saved."""

    def __init__(self, db, user=None):
        self.db = db
        self.user = user  # the logged-in user's row
        self.users = UserRepository(db)

    def commit(self):
        self.db.commit()
