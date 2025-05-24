import sqlite3

def update_db():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()

    # Add invoice_id and invoice_link columns to income table
    try:
        c.execute("ALTER TABLE income ADD COLUMN invoice_id TEXT")
    except sqlite3.OperationalError as e:
        print("Column probably already exists in income table: ", e)

    try:
        c.execute("ALTER TABLE income ADD COLUMN invoice_link TEXT")
    except sqlite3.OperationalError as e:
        print("Column probably already exists in income table: ", e)

    # Add invoice_id and invoice_link columns to expenses table
    try:
        c.execute("ALTER TABLE expenses ADD COLUMN invoice_id TEXT")
    except sqlite3.OperationalError as e:
        print("Column probably already exists in expenses table: ", e)

    try:
        c.execute("ALTER TABLE expenses ADD COLUMN invoice_link TEXT")
    except sqlite3.OperationalError as e:
        print("Column probably already exists in expenses table: ", e)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    update_db()
    print("Database updated successfully!")
