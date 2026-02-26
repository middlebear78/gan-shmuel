from flask import Flask, render_template, request, Response, jsonify
import mysql.connector
import os
import time



app = Flask(__name__)

def get_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root"),
        database=os.getenv("DB_NAME", "gan-shmuel"),
        port=int(os.getenv("DB_PORT", "3306")),
    )

def with_db_cursor(commit=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            conn = get_conn()
            cur = conn.cursor()
            try:
                result = func(cur, *args, **kwargs)
                if commit:
                    conn.commit()
                return result
            finally:
                cur.close()
                conn.close()
        return wrapper
    return decorator


def init_db(max_tries=30, delay=1):
    for i in range(max_tries):
        try:
            create_messages_table()
            return
        except mysql.connector.Error as e:
            print(f"[db] not ready yet ({i+1}/{max_tries}): {e}")
            time.sleep(delay)
    raise RuntimeError("DB not ready after retries")

init_db()




@app.get("/health/db")
def health():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    ok = (cur.fetchone()[0] == 1)
    cur.close()
    conn.close()
    return jsonify(ok=ok)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
