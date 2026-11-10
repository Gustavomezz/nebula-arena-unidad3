"""Tabla de líderes. Firestore en Cloud Run y SQLite para la prueba local."""
import os
import re
import sqlite3

from flask import Flask, jsonify, request


class SqliteScores:
    def __init__(self, path):
        self.path = path
        with self.connection() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS scores (jugador TEXT PRIMARY KEY, puntos INTEGER, partidas INTEGER);
                CREATE TABLE IF NOT EXISTS resultados (evento TEXT PRIMARY KEY);
            """)

    def connection(self):
        return sqlite3.connect(self.path, timeout=30)

    def add(self, player, points, event):
        with self.connection() as con:
            result = con.execute("INSERT OR IGNORE INTO resultados VALUES (?)", (event,))
            if not result.rowcount:
                return False
            con.execute("""INSERT INTO scores VALUES (?, ?, 1)
                ON CONFLICT(jugador) DO UPDATE SET puntos=puntos+excluded.puntos, partidas=partidas+1""",
                        (player, points))
        return True

    def top(self):
        with self.connection() as con:
            rows = con.execute("SELECT jugador,puntos,partidas FROM scores ORDER BY puntos DESC,jugador LIMIT 10")
            return [dict(zip(("jugador", "puntos", "partidas"), row)) for row in rows]


class FirestoreScores:
    def __init__(self):
        from google.cloud import firestore
        self.firestore = firestore
        self.db = firestore.Client()

    def add(self, player, points, event):
        fs = self.firestore
        result_ref = self.db.collection("resultados").document(event)
        score_ref = self.db.collection("scores").document(player)

        @fs.transactional
        def update(transaction):
            if result_ref.get(transaction=transaction).exists:
                return False
            transaction.set(result_ref, {"jugador": player, "puntos": points, "fecha": fs.SERVER_TIMESTAMP})
            transaction.set(score_ref, {"puntos": fs.Increment(points), "partidas": fs.Increment(1)}, merge=True)
            return True

        return update(self.db.transaction())

    def top(self):
        query = self.db.collection("scores").order_by("puntos", direction=self.firestore.Query.DESCENDING).limit(10)
        return [{"jugador": item.id, **item.to_dict()} for item in query.stream()]


def create_app(store=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4096
    # SQLite es solo para desarrollo; el despliegue obliga a usar Firestore.
    backend = store

    def scores():
        nonlocal backend
        if backend is None:
            backend = (SqliteScores(os.getenv("SQLITE_PATH", "scores.sqlite"))
                       if os.getenv("SCORES_BACKEND") == "sqlite" else FirestoreScores())
        return backend

    @app.get("/healthz")
    def health():
        return {"estado": "ok"}

    @app.post("/score")
    def save():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {"error": "se requiere JSON"}, 400
        player, points, event = data.get("jugador"), data.get("puntos"), data.get("evento")
        if not isinstance(player, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", player):
            return {"error": "jugador inválido"}, 400
        if isinstance(points, bool) or not isinstance(points, int) or not 0 <= points <= 100000:
            return {"error": "puntos inválidos"}, 400
        if not isinstance(event, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", event):
            return {"error": "evento inválido"}, 400
        created = scores().add(player, points, event)
        return {"guardado": created}, 201 if created else 200

    @app.get("/top")
    def top():
        return jsonify(scores().top())

    return app


app = create_app()
