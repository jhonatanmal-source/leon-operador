from .db import create_default_admin, init_db


def initialize_database():
    init_db()
    create_default_admin()
