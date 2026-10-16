"""Start mymotoworks: flask --app app run --debug

The app itself is the mymotoworks package (mymotoworks/__init__.py: create_app).
"""

from mymotoworks import create_app

app = create_app()
