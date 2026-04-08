import sqlite3

def get_db():
    return sqlite3.connect('tapcy.db')

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Table 1: Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            phone TEXT
        )
    ''')
    
    # Table 2: Bookings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            pickup TEXT,
            destination TEXT,
            date TEXT
        )
    ''')
    
    # Table 3: Feedback
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            rating INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database ready!")

if __name__ == '__main__':
    init_db()
