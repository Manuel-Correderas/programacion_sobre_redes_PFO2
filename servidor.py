#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PFO 2 — API Flask + SQLite
- POST /registro
- POST /login
- GET  /tareas (HTML protegido)
- UI mínima en /ui
- CRUD opcional de tareas en /tareas (POST), /tareas/json (GET), /tareas/<id> (PUT/DELETE)
"""
from __future__ import annotations
import os, sqlite3
from contextlib import closing
from typing import Optional, Tuple
from flask import Flask, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# ---------------- Config ----------------
DB_PATH = os.environ.get("PFO2_DB", "pfo2.db")
SECRET_KEY = os.environ.get("PFO2_SECRET", "cambia-esto-en-produccion")
TOKEN_EXPIRATION_SECONDS = int(os.environ.get("PFO2_TOKEN_TTL", 3600))

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
serializer = URLSafeTimedSerializer(SECRET_KEY)

# ---------------- DB schema ----------------
DDL_USERS = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""
DDL_TASKS = """
CREATE TABLE IF NOT EXISTS tareas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo TEXT NOT NULL,
  hecha INTEGER NOT NULL DEFAULT 0,
  usuario_id INTEGER NOT NULL,
  creada_en DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);
"""

def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(DDL_USERS)
        conn.execute(DDL_TASKS)
        conn.commit()

# ---------------- Utils ----------------
def get_user_by_username(username: str) -> Optional[Tuple[int, str, str]]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT id, usuario, password_hash FROM usuarios WHERE usuario = ?",
            (username,),
        )
        row = cur.fetchone()
        return row if row else None

def create_user(username: str, password: str) -> Tuple[bool, str]:
    if not username or not password:
        return False, "Usuario y contraseña son obligatorios."
    if get_user_by_username(username):
        return False, "El usuario ya existe."
    password_hash = generate_password_hash(password)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        try:
            conn.execute(
                "INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            conn.commit()
            return True, "Usuario creado con éxito."
        except sqlite3.IntegrityError:
            return False, "El usuario ya existe."

def generate_token(username: str) -> str:
    return serializer.dumps({"sub": username})

def verify_token(token: str) -> Optional[str]:
    try:
        data = serializer.loads(token, max_age=TOKEN_EXPIRATION_SECONDS)
        return data.get("sub")
    except (SignatureExpired, BadSignature):
        return None

def require_user() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return verify_token(parts[1])
    return None

def get_user_id(username: str) -> Optional[int]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute("SELECT id FROM usuarios WHERE usuario = ?", (username,))
        row = cur.fetchone()
        return row[0] if row else None

# ---------------- Endpoints ----------------
@app.get("/")
def home():
    html = """
    <!doctype html><html lang="es"><meta charset="utf-8">
    <title>PFO2 — API Flask + SQLite</title>
    <body style="font-family:system-ui; margin:2rem">
      <h1>PFO2 — API Flask + SQLite</h1>
      <p>Probá la UI: <a href="/ui">/ui</a></p>
      <p>Endpoints: <code>/registro</code>, <code>/login</code>, <code>/tareas</code> (HTML protegido)</p>
    </body></html>
    """
    resp = make_response(html, 200)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp

@app.post("/registro")
def registro():
    if not request.is_json:
        return jsonify({"error": "Se requiere JSON"}), 400
    payload = request.get_json(silent=True) or {}
    username = (payload.get("usuario") or "").strip()
    password = (payload.get("contraseña") or payload.get("contrasena") or "").strip()
    ok, msg = create_user(username, password)
    return jsonify({"ok": ok, "mensaje": msg}), (201 if ok else 400)

@app.post("/login")
def login():
    if not request.is_json:
        return jsonify({"error": "Se requiere JSON"}), 400
    payload = request.get_json(silent=True) or {}
    username = (payload.get("usuario") or "").strip()
    password = (payload.get("contraseña") or payload.get("contrasena") or "").strip()
    user = get_user_by_username(username)
    if not user:
        return jsonify({"ok": False, "error": "Credenciales inválidas"}), 401
    _id, _usuario, password_hash = user
    if not check_password_hash(password_hash, password):
        return jsonify({"ok": False, "error": "Credenciales inválidas"}), 401
    token = generate_token(username)
    return jsonify({"ok": True, "token": token, "expira_en": TOKEN_EXPIRATION_SECONDS})

@app.get("/tareas")
def tareas():
    username = require_user()
    if not username:
        return jsonify({"ok": False, "error": "No autorizado. Enviá 'Authorization: Bearer <token>'"}), 401
    html = f"""
    <!doctype html><html lang=es><meta charset="utf-8"><title>Bienvenido</title>
    <body style="font-family:system-ui; margin:2rem">
      <h1>¡Hola, {username}!</h1>
      <p>Accediste correctamente a <strong>/tareas</strong>.</p>
    </body></html>
    """
    resp = make_response(html, 200)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp

# --- CRUD opcional de tareas (JSON) ---
@app.post("/tareas")
def crear_tarea():
    username = require_user()
    if not username:
        return jsonify({"ok": False, "error": "No autorizado"}), 401
    if not request.is_json:
        return jsonify({"ok": False, "error": "Se requiere JSON"}), 400
    titulo = (request.json.get("titulo") or "").strip()
    if not titulo:
        return jsonify({"ok": False, "error": "titulo es obligatorio"}), 400
    uid = get_user_id(username)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "INSERT INTO tareas (titulo, usuario_id) VALUES (?, ?)", (titulo, uid)
        )
        conn.commit()
        tid = cur.lastrowid
    return jsonify({"ok": True, "id": tid, "titulo": titulo, "hecha": 0}), 201

@app.get("/tareas/json")
def listar_tareas():
    username = require_user()
    if not username:
        return jsonify({"ok": False, "error": "No autorizado"}), 401
    uid = get_user_id(username)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT id, titulo, hecha, creada_en FROM tareas WHERE usuario_id=? ORDER BY id DESC",
            (uid,),
        )
        rows = [
            {"id": r[0], "titulo": r[1], "hecha": int(r[2]), "creada_en": r[3]}
            for r in cur.fetchall()
        ]
    return jsonify({"ok": True, "items": rows})

@app.put("/tareas/<int:tid>")
def actualizar_tarea(tid: int):
    username = require_user()
    if not username:
        return jsonify({"ok": False, "error": "No autorizado"}), 401
    if not request.is_json:
        return jsonify({"ok": False, "error": "Se requiere JSON"}), 400
    uid = get_user_id(username)
    titulo = request.json.get("titulo")
    hecha = request.json.get("hecha")
    sets, params = [], []
    if titulo is not None:
        sets.append("titulo = ?"); params.append(str(titulo).strip())
    if hecha is not None:
        sets.append("hecha = ?"); params.append(1 if int(hecha) else 0)
    if not sets:
        return jsonify({"ok": False, "error": "Nada para actualizar"}), 400
    params += [tid, uid]
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(f"UPDATE tareas SET {', '.join(sets)} WHERE id = ? AND usuario_id = ?", params)
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"ok": False, "error": "No encontrada"}), 404
    return jsonify({"ok": True})

@app.delete("/tareas/<int:tid>")
def borrar_tarea(tid: int):
    username = require_user()
    if not username:
        return jsonify({"ok": False, "error": "No autorizado"}), 401
    uid = get_user_id(username)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute("DELETE FROM tareas WHERE id = ? AND usuario_id = ?", (tid, uid))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"ok": False, "error": "No encontrada"}), 404
    return jsonify({"ok": True})

# --- UI mínima ---
@app.get("/ui")
def ui():
    html = """
    <!doctype html><html lang="es"><meta charset="utf-8"><title>PFO2 — UI mínima</title>
    <body style="font-family:system-ui; margin:2rem">
      <h1>PFO2 — UI mínima</h1>
      <label>Usuario</label><input id="user" value="manu">
      <label>Contraseña</label><input id="pass" type="password" value="1234"><br><br>
      <button onclick="registrar()">Registrar</button>
      <button onclick="login()">Iniciar sesión</button>
      <button onclick="verTareas()">Abrir /tareas</button>
      <pre id="log">Listo.</pre>
      <div id="vista" style="margin-top:1rem"></div>
      <script>
        let TOKEN=null; const log=t=>document.getElementById('log').textContent=String(t);
        function v(id){return document.getElementById(id).value;}
        async function registrar(){
          const r=await fetch('/registro',{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({usuario:v('user'),contrasena:v('pass')})});
          log(await r.text());
        }
        async function login(){
          const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({usuario:v('user'),contrasena:v('pass')})});
          const j=await r.json(); TOKEN=j.token; log(JSON.stringify(j,null,2));
        }
        async function verTareas(){
          if(!TOKEN){ log('Primero hacé login.'); return; }
          const r=await fetch('/tareas',{headers:{Authorization:'Bearer '+TOKEN}});
          if(!r.ok){ log('Error '+r.status); return; }
          const h=await r.text(); document.getElementById('vista').innerHTML=h; log('OK: /tareas renderizado.');
        }
      </script>
    </body></html>
    """
    resp = make_response(html, 200)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp

# ---------------- Main ----------------
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
