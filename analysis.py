"""
analysis.py — аналитика и визуализация данных с использованием pandas, matplotlib, seaborn и networkx.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
import seaborn as sns  # для оформления
from db import connect


def df_orders() -> pd.DataFrame:
    """Вернуть агрегированный датафрейм заказов с суммой по позициям."""
    with connect() as con:
        q = """
        SELECT o.id, o.customer_id, o.created_at, o.status,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        GROUP BY o.id, o.customer_id, o.created_at, o.status
        ORDER BY o.created_at
        """
        return pd.read_sql_query(q, con, parse_dates=["created_at"])


def df_customers() -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query("SELECT * FROM customers", con)


def top5_customers_plot(show: bool = True) -> pd.DataFrame:
    """Столбчатая диаграмма: топ‑5 клиентов по числу заказов."""
    orders = df_orders()
    top = orders.groupby("customer_id")["id"].count().nlargest(5).reset_index(name="num_orders")
    ax = top.plot(kind="bar", x="customer_id", y="num_orders", title="Топ‑5 клиентов по числу заказов")
    ax.set_xlabel("ID клиента")
    ax.set_ylabel("Число заказов")
    if show:
        plt.tight_layout(); plt.show()
    return top


def orders_over_time_plot(show: bool = True) -> pd.Series:
    """Линейный график количества заказов по дням."""
    orders = df_orders()
    series = orders.set_index("created_at").resample("D").size()
    ax = series.plot(kind="line", title="Динамика количества заказов по датам")
    ax.set_xlabel("Дата"); ax.set_ylabel("Число заказов")
    if show:
        plt.tight_layout(); plt.show()
    return series


def customer_graph(by: str = "city", show: bool = True) -> nx.Graph:
    """Построить граф связей клиентов.

    Parameters
    ----------
    by : {'city', 'shared_products'}
        Способ связи узлов.
    """
    customers = df_customers()
    G = nx.Graph()
    for _, row in customers.iterrows():
        G.add_node(int(row["id"]), name=row["name"], city=row["city"])

    if by == "city":
        groups = customers.groupby("city")["id"].apply(list)
        for ids in groups:
            for i in range(len(ids)):
                for j in range(i+1, len(ids)):
                    G.add_edge(int(ids[i]), int(ids[j]), reason="city")
    elif by == "shared_products":
        with connect() as con:
            df = pd.read_sql_query("""                SELECT o.customer_id, oi.product_id
                FROM orders o JOIN order_items oi ON oi.order_id = o.id
            """, con)
        packs = df.groupby("product_id")["customer_id"].apply(list)
        for ids in packs:
            for i in range(len(ids)):
                for j in range(i+1, len(ids)):
                    a, b = int(ids[i]), int(ids[j])
                    if a != b:
                        G.add_edge(a, b, reason="product")
    else:
        raise ValueError("by должен быть 'city' или 'shared_products'")

    if show:
        pos = nx.spring_layout(G, seed=42)
        nx.draw(G, pos, with_labels=True, node_size=600)
        plt.title("Граф связей клиентов"); plt.tight_layout(); plt.show()
    return G
