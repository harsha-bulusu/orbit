import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import BUG_TOGGLES, SIM_CONFIG
from app.models import Order



def create_order_buggy(db: Session, user_id: int, product_id: int, quantity: int) -> Order:
    order = Order(user_id=user_id, product_id=product_id, quantity=quantity)
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


# Use DB-assigned ID so concurrent creates cannot collide under load.
def create_order(db: Session, user_id: int, product_id: int, quantity: int) -> Order:
    if BUG_TOGGLES["id_race_condition"]:
        return create_order_buggy(db, user_id, product_id, quantity)
    return create_order_fixed(db, user_id, product_id, quantity)
