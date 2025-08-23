"""
gui.py — графический интерфейс на Tkinter.
Содержит вкладки: Клиенты, Заказы, Аналитика. Импорт/экспорт в меню «Файл».
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os

from models import Customer, Order, OrderItem, ValidationError, quicksort_orders
import db
import analysis


class App(tk.Tk):
    """Главное окно приложения."""
    def __init__(self):
        super().__init__()
        self.title("E-commerce Manager (RU)")
        self.geometry("1024x680")
        self._make_menu()

        self.nb = ttk.Notebook(self); self.nb.pack(fill="both", expand=True)
        self.customers_frame = ttk.Frame(self.nb)
        self.orders_frame = ttk.Frame(self.nb)
        self.analysis_frame = ttk.Frame(self.nb)
        self.nb.add(self.customers_frame, text="Клиенты")
        self.nb.add(self.orders_frame, text="Заказы")
        self.nb.add(self.analysis_frame, text="Аналитика")

        self._build_customers_tab()
        self._build_orders_tab()
        self._build_analysis_tab()

        db.init_db()

    # ----- Menu -----
    def _make_menu(self):
        m = tk.Menu(self)
        file_m = tk.Menu(m, tearoff=0)
        file_m.add_command(label="Импорт CSV/JSON", command=self.import_data)
        file_m.add_command(label="Экспорт CSV/JSON", command=self.export_data)
        file_m.add_separator()
        file_m.add_command(label="Выход", command=self.destroy)
        m.add_cascade(label="Файл", menu=file_m)
        self.config(menu=m)

    def import_data(self):
        path = filedialog.askopenfilename(title="Выберите CSV или JSON", filetypes=[("CSV/JSON", "*.csv *.json")])
        if not path:
            return
        try:
            if path.endswith(".csv"):
                db.import_from_csv_json(csv_paths={"customers": path})
            else:
                db.import_from_csv_json(json_paths={"customers": path})
            messagebox.showinfo("Импорт", "Импорт успешно завершён")
            self.refresh_customers()
        except Exception as e:
            messagebox.showerror("Ошибка импорта", str(e))

    def export_data(self):
        try:
            out = db.export_to_csv_json(prefix=os.path.join("data", "export"))
            messagebox.showinfo("Экспорт", f"Экспортировано: {out}")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    # ----- Customers -----
    def _build_customers_tab(self):
        frm = self.customers_frame
        form = ttk.LabelFrame(frm, text="Добавить клиента"); form.pack(side="top", fill="x", padx=8, pady=8)

        self.c_name = tk.StringVar(); self.c_email = tk.StringVar(); self.c_phone = tk.StringVar(); self.c_city = tk.StringVar()
        ttk.Label(form, text="Имя:").grid(row=0, column=0, sticky="e")
        ttk.Entry(form, textvariable=self.c_name, width=30).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Email:").grid(row=0, column=2, sticky="e")
        ttk.Entry(form, textvariable=self.c_email, width=30).grid(row=0, column=3, sticky="w")
        ttk.Label(form, text="Телефон:").grid(row=1, column=0, sticky="e")
        ttk.Entry(form, textvariable=self.c_phone, width=30).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="Город:").grid(row=1, column=2, sticky="e")
        ttk.Entry(form, textvariable=self.c_city, width=30).grid(row=1, column=3, sticky="w")
        ttk.Button(form, text="Добавить", command=self.add_customer).grid(row=2, column=3, sticky="e", pady=6)

        list_frame = ttk.LabelFrame(frm, text="Клиенты"); list_frame.pack(side="top", fill="both", expand=True, padx=8, pady=8)
        self.customer_tree = ttk.Treeview(list_frame, columns=("id","name","email","phone","city"), show="headings")
        for col, text in zip(("id","name","email","phone","city"), ("ID","Имя","Email","Телефон","Город")):
            self.customer_tree.heading(col, text=text); self.customer_tree.column(col, width=140 if col!="name" else 220, stretch=True)
        self.customer_tree.pack(fill="both", expand=True)

        self.refresh_customers()

    def add_customer(self):
        try:
            c = Customer(name=self.c_name.get(), email=self.c_email.get(), phone=self.c_phone.get(), city=self.c_city.get() or "Unknown")
            db.add_customer(c); self.refresh_customers()
            self.c_name.set(""); self.c_email.set(""); self.c_phone.set(""); self.c_city.set("")
            messagebox.showinfo("Успех", "Клиент добавлен")
        except ValidationError as ve:
            messagebox.showerror("Валидация", str(ve))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def refresh_customers(self):
        for row in self.customer_tree.get_children():
            self.customer_tree.delete(row)
        for c in db.get_customers():
            self.customer_tree.insert("", "end", values=(c.id, c.name, c.email, c.phone, c.city))

    # ----- Orders -----
    def _build_orders_tab(self):
        frm = self.orders_frame
        form = ttk.LabelFrame(frm, text="Создать заказ"); form.pack(side="top", fill="x", padx=8, pady=8)

        self.o_customer_id = tk.StringVar(); self.o_product_id = tk.StringVar(); self.o_qty = tk.StringVar(value="1"); self.o_price = tk.StringVar(value="0.0")
        ttk.Label(form, text="ID клиента:").grid(row=0, column=0, sticky="e"); ttk.Entry(form, textvariable=self.o_customer_id, width=15).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="ID товара:").grid(row=0, column=2, sticky="e"); ttk.Entry(form, textvariable=self.o_product_id, width=15).grid(row=0, column=3, sticky="w")
        ttk.Label(form, text="Кол-во:").grid(row=1, column=0, sticky="e"); ttk.Entry(form, textvariable=self.o_qty, width=15).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="Цена за ед.:").grid(row=1, column=2, sticky="e"); ttk.Entry(form, textvariable=self.o_price, width=15).grid(row=1, column=3, sticky="w")
        ttk.Button(form, text="Добавить заказ", command=self.add_order).grid(row=2, column=3, sticky="e", pady=6)

        filter_frame = ttk.LabelFrame(frm, text="Фильтры/сортировка"); filter_frame.pack(side="top", fill="x", padx=8, pady=4)
        self.filter_status = tk.StringVar(value="")
        ttk.Label(filter_frame, text="Статус:").grid(row=0, column=0); ttk.Entry(filter_frame, textvariable=self.filter_status, width=15).grid(row=0, column=1)
        ttk.Button(filter_frame, text="Обновить", command=self.refresh_orders).grid(row=0, column=2, padx=4)
        ttk.Button(filter_frame, text="Сорт. по дате", command=lambda: self.sort_orders("date")).grid(row=0, column=3, padx=4)
        ttk.Button(filter_frame, text="Сорт. по сумме", command=lambda: self.sort_orders("total")).grid(row=0, column=4, padx=4)

        list_frame = ttk.LabelFrame(frm, text="Заказы"); list_frame.pack(side="top", fill="both", expand=True, padx=8, pady=8)
        self.orders_tree = ttk.Treeview(list_frame, columns=("id","customer_id","created_at","status","total"), show="headings")
        for col, text in zip(("id","customer_id","created_at","status","total"), ("ID","Клиент","Дата","Статус","Сумма")):
            self.orders_tree.heading(col, text=text); self.orders_tree.column(col, width=160, stretch=True)
        self.orders_tree.pack(fill="both", expand=True)

        self.refresh_orders()

    def add_order(self):
        try:
            customer_id = int(self.o_customer_id.get())
            product_id = int(self.o_product_id.get())
            qty = int(self.o_qty.get())
            price = float(self.o_price.get())
            order = Order(customer_id=customer_id, created_at=datetime.now(), items=[])
            order.add_item(OrderItem(product_id=product_id, quantity=qty, unit_price=price))
            db.add_order(order); self.refresh_orders()
            messagebox.showinfo("Успех", "Заказ создан")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def refresh_orders(self):
        for row in self.orders_tree.get_children():
            self.orders_tree.delete(row)
        orders = db.get_orders()
        status = self.filter_status.get().strip().lower()
        if status:
            orders = [o for o in orders if o.status.lower() == status]
        for o in orders:
            self.orders_tree.insert("", "end", values=(o.id, o.customer_id, o.created_at.strftime("%Y-%m-%d %H:%M"), o.status, f"{o.total():.2f}"))
        self._cached_orders = orders

    def sort_orders(self, how: str):
        orders = getattr(self, "_cached_orders", db.get_orders())
        if how == "date":
            sorted_orders = quicksort_orders(orders, key=lambda o: o.created_at)
        else:
            sorted_orders = quicksort_orders(orders, key=lambda o: o.total())
        for row in self.orders_tree.get_children():
            self.orders_tree.delete(row)
        for o in sorted_orders:
            self.orders_tree.insert("", "end", values=(o.id, o.customer_id, o.created_at.strftime("%Y-%m-%d %H:%M"), o.status, f"{o.total():.2f}"))

    # ----- Analysis -----
    def _build_analysis_tab(self):
        frm = self.analysis_frame
        ttk.Button(frm, text="Топ‑5 клиентов (заказы)", command=analysis.top5_customers_plot).pack(pady=8)
        ttk.Button(frm, text="Динамика заказов", command=analysis.orders_over_time_plot).pack(pady=8)
        ttk.Button(frm, text="Граф: по городам", command=lambda: analysis.customer_graph(by="city")).pack(pady=8)
        ttk.Button(frm, text="Граф: общие товары", command=lambda: analysis.customer_graph(by="shared_products")).pack(pady=8)


def run():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    run()
