from flask import Flask, request, jsonify
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

app=Flask(__name__)
# ____________________________________________________________
# all routes

# health check
@app.route("/health")
def health():
    return {"status": "UP"},200


load_dotenv()

def get_db_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "rootpass"),
        database=os.getenv("DB_NAME", "billdb"),
    )



@app.put("/provider/<int:provider_id>")
def update_provider(provider_id: int):
    """
    Updates provider name by id.
    Assumes SQL DB and a helper get_db_conn() exists in the project.
    Table: Provider(id INT PK, name VARCHAR UNIQUE or treated as unique).
    """
    data = request.get_json(silent=True) or {}
    new_name = (data.get("name") or "").strip()

    if not new_name:
        return jsonify({"error": "name is required"}), 400

    try:
        conn = get_db_conn()              # <-- assumed existing
        cur = conn.cursor(dictionary=True)

        # 1) check provider exists
        cur.execute("SELECT id FROM Provider WHERE id = %s;", (provider_id,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "provider not found"}), 404

        # 2) enforce unique name (no other provider uses it)
        cur.execute(
            "SELECT id FROM Provider WHERE LOWER(name) = LOWER(%s) AND id <> %s;",
            (new_name, provider_id),
        )
        if cur.fetchone() is not None:
            cur.close()
            conn.close()
            return jsonify({"error": "provider name must be unique"}), 409

        # 3) update
        cur.execute(
            "UPDATE Provider SET name = %s WHERE id = %s;",
            (new_name, provider_id),
        )
        conn.commit()

        # 4) return updated record
        cur.execute("SELECT id, name FROM Provider WHERE id = %s;", (provider_id,))
        updated = cur.fetchone()

        cur.close()
        conn.close()
        return jsonify(updated), 200

    except Exception as e:
        return jsonify({"error": "server error", "details": str(e)}), 500



# ____________________________________________________________
# named as __main__
if __name__=="__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)


