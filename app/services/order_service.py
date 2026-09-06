import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import BUG_TOGGLES, SIM_CONFIG
from app.models import Order


def create_order_buggy(db: Session, user_id: int, product_id: int, quantity: int) -> Order:
    max_id = db.execute(text("SELECT MAX(id) FROM orders")).scalar() or 0
    # Widens the read-then-write window so concurrent requests reliably
    # compute the same "next id" from the same stale MAX(id) read.
    time.sleep(SIM_CONFIG["order_race_window_ms"] / 1000)
    new_id = max_id + 1
    order = Order(id=new_id, user_id=user_id, product_id=product_id, quantity=quantity)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def create_order_fixed(db: Session, user_id: int, product_id: int, quantity: int) -> Order:
    order = Order(user_id=user_id, product_id=product_id, quantity=quantity)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def create_order(db: Session, user_id: int, product_id: int, quantity: int) -> Order:
    if BUG_TOGGLES["id_race_condition"]:
        return create_order_buggy(db, user_id, product_id, quantity)
    return create_order_fixed(db, user_id, product_id, quantity)
