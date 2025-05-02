import sqlite3
import os
from datetime import datetime

# Use the same DB as auth
from src.auth.auth_db import DB_PATH, get_db_connection

def init_file_db():
    """Initialize the file storage tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create files table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_type TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        file_size INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    conn.commit()
    conn.close()

def save_file_info(filename, file_path, file_type, user_id, file_size):
    """Save file information to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO files (filename, file_path, file_type, user_id, file_size) VALUES (?, ?, ?, ?, ?)",
        (filename, file_path, file_type, user_id, file_size)
    )
    
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return file_id

def get_file_by_id(file_id):
    """Get file information by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
    file = cursor.fetchone()
    
    conn.close()
    
    return dict(file) if file else None

def get_files_by_user(user_id):
    """Get all files uploaded by a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM files WHERE user_id = ? ORDER BY upload_date DESC", (user_id,))
    files = cursor.fetchall()
    
    conn.close()
    
    return [dict(file) for file in files]

def delete_file(file_id, user_id):
    """Delete a file record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First check if the file belongs to the user
    cursor.execute("SELECT file_path FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
    file = cursor.fetchone()
    
    if not file:
        conn.close()
        return False
    
    # Delete the file record
    cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()
    
    # Delete the actual file if it exists
    file_path = file['file_path']
    if os.path.exists(file_path):
        os.remove(file_path)
    
    return True

# Initialize the file database when the module is imported
init_file_db()