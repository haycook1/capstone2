import os
import sqlite3
from datetime import date, timedelta

DB_PATH = "data/enterprise.db"

def seed_database():
    os.makedirs("data", exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
        DROP TABLE IF EXISTS sales;
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS employees;

        CREATE TABLE sales (
            id INTEGER PRIMARY KEY,
            region TEXT NOT NULL,
            product TEXT NOT NULL,
            revenue REAL NOT NULL,
            date TEXT NOT NULL,
            units_sold INTEGER NOT NULL
        );

        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT NOT NULL,
            churn_date TEXT,
            satisfaction_score REAL NOT NULL
        );

        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            department TEXT NOT NULL,
            satisfaction_score REAL NOT NULL,
            tenure_years REAL NOT NULL
        );
        """)

        regions = ["Northeast", "Southeast", "Midwest", "West"]
        products = ["Analytics Platform", "Cloud Suite", "Security Package"]
        sales_rows = []
        sale_id = 1
        start_date = date(2025, 1, 1)

        for week in range(52):
            sale_date = start_date + timedelta(days=week * 7)

            for region_index, region in enumerate(regions):
                for product_index, product in enumerate(products):
                    units = 20 + (
                        (week + region_index * 4 + product_index * 6) % 25
                    )
                    price = 1200 + product_index * 450
                    revenue = units * price

                    sales_rows.append((
                        sale_id,
                        region,
                        product,
                        revenue,
                        sale_date.isoformat(),
                        units,
                    ))
                    sale_id += 1

        conn.executemany("""
            INSERT INTO sales
            (id, region, product, revenue, date, units_sold)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sales_rows)

        customers = [
            (1, "Northstar Retail", "Retail", None, 4.6),
            (2, "BluePeak Manufacturing", "Manufacturing", None, 4.1),
            (3, "Cedar Health", "Healthcare", "2025-03-18", 2.8),
            (4, "Summit Logistics", "Transportation", None, 4.4),
            (5, "Harbor Financial", "Financial Services", "2025-06-22", 3.1),
            (6, "Maple Education", "Education", None, 4.0),
            (7, "Redwood Media", "Media", "2025-09-10", 2.5),
            (8, "Pioneer Energy", "Energy", None, 4.7),
            (9, "Lakeside Foods", "Consumer Products", None, 3.9),
            (10, "Metro Government", "Public Sector", None, 4.3),
        ]

        conn.executemany("""
            INSERT INTO customers
            (id, name, industry, churn_date, satisfaction_score)
            VALUES (?, ?, ?, ?, ?)
        """, customers)

        employees = [
            (1, "Sales", 4.2, 3.5),
            (2, "Sales", 3.8, 1.8),
            (3, "Operations", 4.4, 5.2),
            (4, "Operations", 4.0, 2.7),
            (5, "Customer Success", 3.6, 2.1),
            (6, "Customer Success", 4.3, 4.8),
            (7, "Engineering", 4.7, 6.1),
            (8, "Engineering", 4.5, 3.9),
            (9, "Finance", 4.1, 7.4),
            (10, "Human Resources", 3.9, 4.0),
        ]

        conn.executemany("""
            INSERT INTO employees
            (id, department, satisfaction_score, tenure_years)
            VALUES (?, ?, ?, ?)
        """, employees)

        conn.commit()

    print(f"Created {DB_PATH}")
    print(f"Inserted {len(sales_rows)} sales rows, 10 customers, and 10 employees.")

if __name__ == "__main__":
    seed_database()

