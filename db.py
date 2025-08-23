"""
db.py — слой доступа к данным (SQLite) и импорт/экспорт CSV/JSON.
"""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd

from models import Customer, Product, Order, OrderItem

DB_PATH = "data/ecommerce.sqlite3"


@contextmanager
def connect(db_path: str = DB_PATH):
    """Контекстный менеджер для подключения к SQLite."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(db_path: str = DB_PATH) -> None:
    """Создать таблицы при первом запуске."""
    with connect(db_path) as con:
        cur = con.cursor()
        cur.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                city TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                sku TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS order_items (
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id),
                PRIMARY KEY(order_id, product_id)
            );
            """
        )


# --------- CRUD: Customers ---------
def add_customer(c: Customer, db_path: str = DB_PATH) -> int:
    with connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO customers(name, email, phone, city) VALUES(?,?,?,?)",
            (c.name, c.email, c.phone, c.city),
        )
        return cur.lastrowid


def get_customers(db_path: str = DB_PATH) -> List[Customer]:
    with connect(db_path) as con:
        cur = con.cursor()
        rows = cur.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
        return [
            Customer(id=row["id"], name=row["name"], email=row["email"], phone=row["phone"], city=row["city"])
            for row in rows
        ]


# --------- CRUD: Products ---------
def add_product(p: Product, db_path: str = DB_PATH) -> int:
    with connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO products(name, price, sku) VALUES(?,?,?)",
            (p.name, p.price, p.sku),
        )
        return cur.lastrowid


def get_products(db_path: str = DB_PATH) -> List[Product]:
    with connect(db_path) as con:
        cur = con.cursor()
        rows = cur.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        return [
            Product(id=row["id"], name=row["name"], price=row["price"], sku=row["sku"])
            for row in rows
        ]


# --------- CRUD: Orders ---------
def add_order(o: Order, db_path: str = DB_PATH) -> int:
    with connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO orders(customer_id, created_at, status) VALUES(?,?,?)",
            (o.customer_id, o.created_at.isoformat(), o.status),
        )
        order_id = cur.lastrowid
        for it in o.items:
            cur.execute(
                "INSERT INTO order_items(order_id, product_id, quantity, unit_price) VALUES(?,?,?,?)",
                (order_id, it.product_id, it.quantity, it.unit_price),
            )
        return order_id


def get_orders(db_path: str = DB_PATH) -> List[Order]:
    """Загрузить заказы вместе с позициями."""
    with connect(db_path) as con:
        cur = con.cursor()
        rows = cur.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
        orders: List[Order] = []
        for row in rows:
            order_id = row["id"]
            items_rows = cur.execute(
                "SELECT * FROM order_items WHERE order_id=?", (order_id,)
            ).fetchall()
            items = [
                OrderItem(
                    product_id=ir["product_id"],
                    quantity=ir["quantity"],
                    unit_price=ir["unit_price"],
                )
                for ir in items_rows
            ]
            orders.append(
                Order(
                    id=order_id,
                    customer_id=row["customer_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    status=row["status"],
                    items=items,
                )
            )
        return orders


# --------- Import/Export via pandas ---------
def export_to_csv_json(db_path: str = DB_PATH, prefix: str = "data/export") -> Dict[str, str]:
    """Экспорт всех таблиц в CSV и JSON.

    Returns
    -------
    dict
        Словарь с путями к CSV файлов (для краткости).
    """
    paths: Dict[str, str] = {}
    with connect(db_path) as con:
        for table in ("customers", "products", "orders", "order_items"):
            df = pd.read_sql_query(f"SELECT * FROM {table}", con)
            csv_path = f"{prefix}_{table}.csv"
            json_path = f"{prefix}_{table}.json"
            df.to_csv(csv_path, index=False)
            df.to_json(json_path, orient="records", force_ascii=False)
            paths[table] = csv_path
    return paths


def import_from_csv_json(
    db_path: str = DB_PATH,
    csv_paths: Optional[Dict[str, str]] = None,
    json_paths: Optional[Dict[str, str]] = None,
) -> None:
    """Импорт данных из CSV/JSON (append).
    Для простоты не делаем upsert/merge.
    """
    with connect(db_path) as con:
        if csv_paths:
            for table, path in csv_paths.items():
                df = pd.read_csv(path)
                df.to_sql(table, con, if_exists="append", index=False)
        if json_paths:
            for table, path in json_paths.items():
                df = pd.read_json(path)
                df.to_sql(table, con, if_exists="append", index=False)
