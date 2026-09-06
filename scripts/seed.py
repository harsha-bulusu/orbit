"""Seed the database with baseline products/reviews. Run: python -m scripts.seed"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base, engine  # noqa: E402
from app.seed_data import seed_products  # noqa: E402


def main():
    Base.metadata.create_all(bind=engine)
    seed_products()
    print("Seeded products and reviews.")


if __name__ == "__main__":
    main()
