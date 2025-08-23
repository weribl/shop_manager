"""
main.py — точка входа приложения.
"""
import db
from gui import run

if __name__ == "__main__":
    db.init_db()
    run()
