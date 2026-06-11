"""
Python script to generate unified sales history
Generates 4 months of realistic sales data (Sept-Dec 2024)
"""
import csv
from datetime import datetime, timedelta

# Category specs: (name, min_daily, max_daily)
categories = [
    ("tv", 8, 12),
    ("laptop", 5, 8),
    ("phone", 15, 20),
    ("kitchen_appliances", 30, 40),
    ("fashion", 50, 70),
    ("groceries", 200, 250),
    ("electronics", 100, 130),
]

# Generate data
start_date = datetime(2024, 9, 1)
end_date = datetime(2024, 12, 31)

rows = []
current_date = start_date

while current_date <= end_date:
    for cat_name, min_val, max_val in categories:
        # Alternate between min and max for variation
        day_num = (current_date - start_date).days
        if day_num % 3 == 0:
            sales = min_val
        elif day_num % 3 == 1:
            sales = max_val
        else:
            sales = (min_val + max_val) // 2
        
        rows.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "category": cat_name,
            "sales": sales
        })
    
    current_date += timedelta(days=1)

# Write CSV
with open("sales_history.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["date", "category", "sales"])
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ Generated {len(rows)} rows of sales data")
print(f"   Categories: {len(categories)}")
print(f"   Date range: {start_date.date()} to {end_date.date()}")
print(f"   Total days: {(end_date - start_date).days + 1}")
