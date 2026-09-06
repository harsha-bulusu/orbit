from app.db import SessionLocal
from app.models import Product, Review

SAMPLE_PRODUCTS = [
    {"name": "Aurora Desk Lamp", "description": "Adjustable LED desk lamp with warm/cool modes.", "price": 34.99, "stock": 120},
    {"name": "Nimbus Backpack", "description": "Water-resistant 20L daypack.", "price": 59.00, "stock": 80},
    {"name": "Solace Mechanical Keyboard", "description": "Hot-swappable 75% keyboard.", "price": 129.50, "stock": 45},
    {"name": "Drift Wireless Earbuds", "description": "Active noise cancelling earbuds.", "price": 89.99, "stock": 200},
    {"name": "Basecamp Enamel Mug", "description": "16oz double-wall enamel mug.", "price": 14.00, "stock": 300},
]

SAMPLE_REVIEWS = [
    {"product_index": 0, "rating": 5, "comment": "Bright and sturdy, great for late nights."},
    {"product_index": 0, "rating": 4, "comment": "Good lamp, wish the arm was longer."},
    {"product_index": 1, "rating": 5, "comment": "Survived a rainstorm with no issues."},
    {"product_index": 2, "rating": 5, "comment": "Best keyboard I've owned."},
    {"product_index": 3, "rating": 3, "comment": "Good sound, case battery is mediocre."},
    {"product_index": 4, "rating": 4, "comment": "Keeps coffee hot for hours."},
]


def seed_products():
    db = SessionLocal()
    try:
        products = [Product(**p) for p in SAMPLE_PRODUCTS]
        db.add_all(products)
        db.commit()
        for p in products:
            db.refresh(p)

        reviews = [
            Review(product_id=products[r["product_index"]].id, rating=r["rating"], comment=r["comment"])
            for r in SAMPLE_REVIEWS
        ]
        db.add_all(reviews)
        db.commit()
    finally:
        db.close()
