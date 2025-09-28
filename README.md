# PFO 2 — API Flask + SQLite (Registro, Login y /tareas HTML)

Este proyecto implementa una **API REST** con **SQLite** para cumplir los requisitos del PFO 2:

- Registro de usuarios (`POST /registro`) guardando **contraseñas hasheadas**.
- Login (`POST /login`) que valida credenciales y entrega **token Bearer**.
- Endpoint protegido `/tareas` (`GET /tareas`) que devuelve **HTML de bienvenida**.

## Requisitos

- Python 3.10+
- Pip/venv
- Flask
- Werkzeug
- itsdangerous

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
Variables opcionales:
•	PFO2_DB → ruta del SQLite (default: pfo2.db)
•	PFO2_SECRET → clave para firmar tokens (¡cambiala en producción!)
•	PFO2_TOKEN_TTL → expiración del token en segundos (default: 3600)
Cómo ejecutar
python servidor.py
La API corre en http://127.0.0.1:5000 (o http://localhost:5000).
Pruebas rápidas con curl
1.	Registro de usuario
curl -s -X POST http://localhost:5000/registro \
  -H "Content-Type: application/json" \
  -d '{"usuario":"manu","contraseña":"1234"}' | jq
Salida esperada (ejemplo):
{"ok": true, "mensaje": "Usuario creado con éxito."}
2.	Login y obtener token
TOKEN=$(curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"manu","contraseña":"1234"}' | jq -r .token)

echo $TOKEN
3.	Acceder a /tareas (HTML) con Bearer
curl -i http://localhost:5000/tareas -H "Authorization: Bearer $TOKEN"
Deberías ver HTTP/1.0 200 OK y un HTML de bienvenida.
Si olvidás el header Authorization, la API responde 401 con mensaje de ayuda.
Estructura técnica
•	Flask como microframework web.
•	SQLite como base de datos embebida.
•	Werkzeug para hashear contraseñas (PBKDF2-SHA256 por defecto).
•	itsdangerous para tokens firmados con expiración.
Extensiones sugeridas (opcional para +puntos)
•	Agregar CRUD real de tareas (/tareas POST/GET/PUT/DELETE) por usuario.
•	Paginación y filtros.
•	Tests automáticos (pytest + requests).
•	Dockerfile + docker-compose.
Respuestas conceptuales
¿Por qué hashear contraseñas?
Porque almacenar contraseñas en texto plano es peligroso. Si la base se filtra, un hash robusto y con sal (salt) dificulta enormemente que un atacante recupere la contraseña original. Además, algoritmos como PBKDF2, bcrypt, scrypt o Argon2 son lentos a propósito, lo que mitiga ataques de fuerza bruta.
Ventajas de usar SQLite en este proyecto
•	Simplicidad y cero configuración: es un archivo .db, ideal para PFO/TP.
•	Portabilidad: el repositorio se mueve con la DB local sin servidor externo.
•	Rendimiento suficiente para baja concurrencia y desarrollo local.
•	Transaccional y con ACID, lo que garantiza consistencia.

Capturas de pantalla 
A continuación, las 7 capturas ubicadas en la carpeta [`img/`](img):

1. **UI mínima**  
   ![01](/img/img1.jpg)  
   UI mínima cargada: formulario de Registro/Login y acción para abrir /tareas.

2. **Login inválido**  
   ![02](/img/img2.jpg)  
   Intento de inicio de sesión con credenciales inválidas (respuesta JSON).

3. **Bloqueo sin login**  
   ![03](/img/img3.jpg)  
   Acceso directo a /tareas sin autenticación: la interfaz solicita iniciar sesión primero.

4. **Login inválido (reintento)**  
   ![04](/img/img4.jpg)  
   Nuevo intento de inicio de sesión con credenciales inválidas.

5. **Registro OK**  
   ![05](/img/img5.jpg)  
   Registro exitoso de usuario (mensaje de confirmación JSON).

6. **Login OK + token**  
   ![06](/img/img6.jpg)  
   Login exitoso: el backend emite token Bearer y TTL en segundos.

7. **/tareas OK**  
   ![07](/img/img7.jpg)  
   Ingreso correcto a /tareas: HTML de bienvenida renderizado y saludo con el usuario.

Deploy en GitHub

________________________________________
© 2025 — PFO 2 Flask + SQLite
