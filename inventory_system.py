"""
Inventory System (Mini - Upgraded)

Features:
- Login (username + password) - L1 simple UI
- Products CRUD: Add / Update / Delete
- Live search (name/category)
- Export to CSV and Excel (.xlsx)
- Dashboard with totals and top-categories chart (Matplotlib embedded)
- SQLite DB auto-created: mini_inventory.db
- Compact UI for small screens (recommended 1366x768)

Run:
    python inventory_system.py

Dependencies:
    pip install PyQt5 pandas matplotlib openpyxl

If you don't want Excel export, openpyxl is optional (CSV will still work).
"""
import sys
import os
import sqlite3
import hashlib
from datetime import datetime
from collections import Counter

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

import pandas as pd

# Matplotlib inside PyQt5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

DB_NAME = "mini_inventory.db"

# -----------------------
# Database utilities
# -----------------------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    """Create products and users tables if not exist and add default admin user."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Products table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            quantity INTEGER DEFAULT 0,
            price REAL DEFAULT 0.0,
            added_on TEXT
        )
    """)
    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()

    # Insert default admin user (username: admin, password: admin123)
    default_username = "admin"
    default_password = "admin123"
    hashed = hashlib.sha256(default_password.encode()).hexdigest()
    try:
        cur.execute("INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (?, ?, ?)",
                    (1, default_username, hashed))
        conn.commit()
    except Exception as e:
        print("User insert error:", e)
    conn.close()

# Product CRUD
def fetch_products(search_text=""):
    conn = get_db_connection()
    cur = conn.cursor()
    if search_text:
        like = f"%{search_text}%"
        cur.execute("""SELECT id, name, category, quantity, price, added_on
                       FROM products
                       WHERE name LIKE ? OR category LIKE ?
                       ORDER BY id DESC""", (like, like))
    else:
        cur.execute("""SELECT id, name, category, quantity, price, added_on
                       FROM products ORDER BY id DESC""")
    rows = cur.fetchall()
    conn.close()
    return rows

def insert_product(name, category, quantity, price):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""INSERT INTO products (name, category, quantity, price, added_on)
                       VALUES (?, ?, ?, ?, ?)""",
                    (name, category, quantity, price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Insert product error:", e)
        return False

def update_product(product_id, name, category, quantity, price):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""UPDATE products SET name=?, category=?, quantity=?, price=?
                       WHERE id=?""", (name, category, quantity, price, product_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Update product error:", e)
        return False

def delete_product(product_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Delete product error:", e)
        return False

# User auth
def check_credentials(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    cur.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (username, hashed))
    row = cur.fetchone()
    conn.close()
    return bool(row)

# -----------------------
# Matplotlib Chart Widget
# -----------------------
class SimpleChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(4, 3), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_top_categories(self, category_counts):
        """category_counts: dict or Counter {category: count}"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if not category_counts:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
        else:
            categories = list(category_counts.keys())
            counts = list(category_counts.values())
            ax.bar(categories, counts)
            ax.set_title("Top Categories (by number of products)")
            ax.set_ylabel("Count")
            ax.set_xticklabels(categories, rotation=45, ha='right')
        self.canvas.draw()

# -----------------------
# Login Dialog (L1)
# -----------------------
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login - Inventory System")
        self.setFixedSize(360, 200)
        self.setup_ui()
        self.accepted_user = None

    def setup_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Inventory System - Login")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:16px; font-weight:bold;")
        layout.addWidget(title)

        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", self.username)
        form.addRow("Password:", self.password)
        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.handle_login)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(login_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # Hint
        hint = QLabel("Default - username: admin | password: admin123")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("font-size:11px; color: gray;")
        layout.addWidget(hint)

        self.setLayout(layout)

    def handle_login(self):
        user = self.username.text().strip()
        pwd = self.password.text().strip()
        if not user or not pwd:
            QMessageBox.warning(self, "Validation", "Enter username and password.")
            return
        if check_credentials(user, pwd):
            self.accepted_user = user
            self.accept()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid credentials.")

# -----------------------
# Main Application Window
# -----------------------
class InventoryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Small-screen friendly geometry
        self.setWindowTitle("Mini Inventory System")
        self.setGeometry(120, 80, 920, 620)  # compact for S
        self._selected_product_id = None
        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout()
        central.setLayout(main_layout)

        # Top toolbar area
        top_layout = QHBoxLayout()
        title = QLabel("Mini Inventory Management System")
        title.setStyleSheet("font-size:16px; font-weight:bold;")
        top_layout.addWidget(title)
        top_layout.addStretch()
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)
        top_layout.addWidget(logout_btn)
        main_layout.addLayout(top_layout)

        # Tabs: Dashboard | Products | Export
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Dashboard Tab
        self.dashboard_tab = QWidget()
        self.setup_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")

        # Products Tab
        self.products_tab = QWidget()
        self.setup_products_tab()
        self.tabs.addTab(self.products_tab, "Products")

        # Export Tab
        self.export_tab = QWidget()
        self.setup_export_tab()
        self.tabs.addTab(self.export_tab, "Export")

        # Status bar
        self.statusBar().showMessage("Ready")

        # Initial load
        self.load_table()
        self.update_dashboard()

    # -----------------------
    # Dashboard
    # -----------------------
    def setup_dashboard_tab(self):
        layout = QVBoxLayout()
        self.dashboard_tab.setLayout(layout)

        stats_layout = QHBoxLayout()
        # Stat boxes
        self.total_products_label = QLabel("Total Products: 0")
        self.total_products_label.setStyleSheet("font-size:14px;")
        stats_layout.addWidget(self.total_products_label)

        self.total_quantity_label = QLabel("Total Quantity: 0")
        self.total_quantity_label.setStyleSheet("font-size:14px;")
        stats_layout.addWidget(self.total_quantity_label)

        self.total_value_label = QLabel("Total Value: $0.00")
        self.total_value_label.setStyleSheet("font-size:14px;")
        stats_layout.addWidget(self.total_value_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Chart
        self.chart_widget = SimpleChart()
        layout.addWidget(self.chart_widget, stretch=1)

    def update_dashboard(self):
        rows = fetch_products()
        total_products = len(rows)
        total_quantity = sum(int(r[3] or 0) for r in rows)
        total_value = sum((int(r[3] or 0) * float(r[4] or 0.0)) for r in rows)

        self.total_products_label.setText(f"Total Products: {total_products}")
        self.total_quantity_label.setText(f"Total Quantity: {total_quantity}")
        self.total_value_label.setText(f"Total Value: ${total_value:.2f}")

        # Top categories chart
        categories = [ (r[2] or "Uncategorized") for r in rows ]
        counts = Counter(categories)
        top_counts = dict(counts.most_common(8))
        self.chart_widget.plot_top_categories(top_counts)

    # -----------------------
    # Products tab
    # -----------------------
    def setup_products_tab(self):
        layout = QVBoxLayout()
        self.products_tab.setLayout(layout)

        # Form area
        form_layout = QHBoxLayout()
        form_left = QFormLayout()
        self.name_input = QLineEdit()
        self.category_input = QLineEdit()
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 1000000)
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 10000000)
        self.price_input.setDecimals(2)

        form_left.addRow("Name:", self.name_input)
        form_left.addRow("Category:", self.category_input)
        form_left.addRow("Quantity:", self.quantity_input)
        form_left.addRow("Price:", self.price_input)

        form_buttons = QVBoxLayout()
        add_btn = QPushButton("Add Product")
        add_btn.clicked.connect(self.handle_add)
        update_btn = QPushButton("Update Product")
        update_btn.clicked.connect(self.handle_update)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_form)

        for b in (add_btn, update_btn, clear_btn):
            b.setFixedHeight(34)
            form_buttons.addWidget(b)
        form_buttons.addStretch()

        form_layout.addLayout(form_left, 70)
        form_layout.addLayout(form_buttons, 30)
        layout.addLayout(form_layout)

        # Search + table
        tool_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or category...")
        self.search_input.textChanged.connect(self.load_table)
        tool_layout.addWidget(QLabel("Search:"))
        tool_layout.addWidget(self.search_input)
        tool_layout.addStretch()
        layout.addLayout(tool_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Category", "Quantity", "Price", "Added On"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellClicked.connect(self.table_row_clicked)
        layout.addWidget(self.table, 1)

        # Delete
        bottom = QHBoxLayout()
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.handle_delete)
        bottom.addStretch()
        bottom.addWidget(self.delete_btn)
        layout.addLayout(bottom)

    def load_table(self):
        s = self.search_input.text().strip()
        rows = fetch_products(s)
        self.table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "")
                if c_idx == 0:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(r_idx, c_idx, item)
        self.table.resizeColumnsToContents()
        self._selected_product_id = None
        # Update dashboard whenever table changes
        self.update_dashboard()

    def table_row_clicked(self, row, column):
        try:
            id_item = self.table.item(row, 0)
            name_item = self.table.item(row, 1)
            cat_item = self.table.item(row, 2)
            qty_item = self.table.item(row, 3)
            price_item = self.table.item(row, 4)
            if id_item:
                self._selected_product_id = int(id_item.text())
                self.name_input.setText(name_item.text() if name_item else "")
                self.category_input.setText(cat_item.text() if cat_item else "")
                self.quantity_input.setValue(int(qty_item.text()) if qty_item and qty_item.text().isdigit() else 0)
                try:
                    self.price_input.setValue(float(price_item.text()))
                except Exception:
                    self.price_input.setValue(0.0)
        except Exception as e:
            print("Row click error:", e)

    def handle_add(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Product name required.")
            return
        category = self.category_input.text().strip()
        qty = self.quantity_input.value()
        price = self.price_input.value()
        ok = insert_product(name, category, qty, price)
        if ok:
            QMessageBox.information(self, "Added", "Product added.")
            self.clear_form()
            self.load_table()
        else:
            QMessageBox.critical(self, "Error", "Failed to add product.")

    def handle_update(self):
        if not self._selected_product_id:
            QMessageBox.warning(self, "Select", "Select a product to update.")
            return
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Product name required.")
            return
        category = self.category_input.text().strip()
        qty = self.quantity_input.value()
        price = self.price_input.value()
        ok = update_product(self._selected_product_id, name, category, qty, price)
        if ok:
            QMessageBox.information(self, "Updated", "Product updated.")
            self.clear_form()
            self.load_table()
        else:
            QMessageBox.critical(self, "Error", "Failed to update product.")

    def handle_delete(self):
        if not self._selected_product_id:
            QMessageBox.warning(self, "Select", "Select a product to delete.")
            return
        reply = QMessageBox.question(self, "Confirm", "Delete selected product?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = delete_product(self._selected_product_id)
            if ok:
                QMessageBox.information(self, "Deleted", "Product deleted.")
                self.clear_form()
                self.load_table()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete product.")

    def clear_form(self):
        self._selected_product_id = None
        self.name_input.clear()
        self.category_input.clear()
        self.quantity_input.setValue(0)
        self.price_input.setValue(0.0)
        self.table.clearSelection()

    # -----------------------
    # Export tab
    # -----------------------
    def setup_export_tab(self):
        layout = QVBoxLayout()
        self.export_tab.setLayout(layout)

        info = QLabel("Export inventory data to CSV or Excel (.xlsx)")
        layout.addWidget(info)

        btn_layout = QHBoxLayout()
        csv_btn = QPushButton("Export CSV")
        csv_btn.clicked.connect(self.export_csv)
        excel_btn = QPushButton("Export Excel (.xlsx)")
        excel_btn.clicked.connect(self.export_excel)
        btn_layout.addWidget(csv_btn)
        btn_layout.addWidget(excel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

    def export_csv(self):
        rows = fetch_products(self.search_input.text().strip())
        if not rows:
            QMessageBox.warning(self, "No data", "No products to export.")
            return
        df = pd.DataFrame(rows, columns=["ID", "Name", "Category", "Quantity", "Price", "Added On"])
        default = f"inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", default, "CSV Files (*.csv)")
        if path:
            try:
                df.to_csv(path, index=False)
                QMessageBox.information(self, "Exported", f"CSV saved: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")

    def export_excel(self):
        rows = fetch_products(self.search_input.text().strip())
        if not rows:
            QMessageBox.warning(self, "No data", "No products to export.")
            return
        df = pd.DataFrame(rows, columns=["ID", "Name", "Category", "Quantity", "Price", "Added On"])
        default = f"inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", default, "Excel Files (*.xlsx)")
        if path:
            try:
                # This requires openpyxl installed
                df.to_excel(path, index=False)
                QMessageBox.information(self, "Exported", f"Excel saved: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Excel export failed: {e}\nMake sure 'openpyxl' is installed.")

    # -----------------------
    # Logout
    # -----------------------
    def logout(self):
        reply = QMessageBox.question(self, "Logout", "Do you want to logout?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
            main()  # restart app (shows login again)

# -----------------------
# App entry point
# -----------------------
def main():
    init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("Mini Inventory")
    # Show login first
    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        window = InventoryApp()
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
