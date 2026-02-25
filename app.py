# python.exe -m venv .venv
# cd .venv/Scripts
# activate.bat
# py -m ensurepip --upgrade
# pip install -r requirements.txt

from functools import wraps
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS, cross_origin

import mysql.connector.pooling
import pusher
import pytz
import datetime
import time

app = Flask(__name__)
app.secret_key = "clave_secreta"  
app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CORS(app)

con_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=5,
    host="46.28.42.226",
    database="u760464709_23005014_bd",
    user="u760464709_23005014_usr",
    password="B|7k3UPs3&P"
)

def pusherBase(channel, event, message="hello"):
    pusher_client = pusher.Pusher(
        app_id='2048639',
        key='85576a197a0fb5c211de',
        secret='bbd4afc18e15b3760912',
        cluster='us2',
        ssl=True
    )
    pusher_client.trigger(channel, event, {'message': message})
    return make_response(jsonify({}))

def pusherIntegrantes():
    return pusherBase("integranteschannel", "integrantesevent", "hello Integrantes")


def login(fun):
    @wraps(fun)
    def decorador(*args, **kwargs):
        if not session.get("login"):
            return jsonify({
                "estado": "error",
                "respuesta": "No has iniciado sesión"
            }), 401
        return fun(*args, **kwargs)
    return decorador



# ---------------------------------------------------------
# DECORADOR PARA ADMINS
# ---------------------------------------------------------
def admin_required(fun):
    @wraps(fun)
    def decorador(*args, **kwargs):
        # Primero validamos que haya sesión
        if not session.get("login"):
            return jsonify({"estado": "error", "respuesta": "No has iniciado sesión"}), 401
        
        # Luego validamos que el tipo de usuario sea 1 (Admin)
        if str(session.get("login-tipo")) != "1":
            return "Acceso denegado. Solo administradores pueden ver esta sección.", 403
            
        return fun(*args, **kwargs)
    return decorador



# Ruta de Inicio (Index)
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def appLogin():
    return render_template("login.html")


# Rutas del Inicio
@app.route("/inicio")
@login
def inicio():
    return render_template("inicio.html")

@app.route("/tbodyInicio")
@login
def tbodyInicio():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT idLibro, titulo, autor, tipo, precio, portada
            FROM libros
            ORDER BY idLibro DESC
            LIMIT 50
            """)
        libros = cursor.fetchall()

        return render_template("tbodyInicio.html", libros=libros)

    except Exception as e:
        print("Error en /tbodyInicio:", str(e))
        return jsonify({"error": "Error interno al cargar libros"}), 500

    finally:
        cursor.close()
        con.close()
        
###########################################################################
#   Fin Rutas de el Inicio (Pagina Principal)  ############################
###########################################################################
    
# Funcionamiento del Inicio de sesion

# ---------------------------------------------------------
# SE MODIFICO PARA CONTAR INTENTOS FALLIDOS
# ---------------------------------------------------------
# Asegúrate de importar esto al inicio si no lo tienes
import time 

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    # 1. VERIFICAR BLOQUEO EXISTENTE
    bloqueo_timestamp = session.get("bloqueo_hasta")
    if bloqueo_timestamp:
        ahora = datetime.datetime.now().timestamp()
        if ahora < bloqueo_timestamp:
            restante = int(bloqueo_timestamp - ahora)
            return jsonify({
                "error": f"Sistema bloqueado por seguridad. Espera {restante}s",
                "bloqueo": True,
                "tiempo": restante
            }), 429  # Código HTTP 429: Too Many Requests
        else:
            # El tiempo ya pasó, limpiamos el bloqueo y el contador
            session.pop("bloqueo_hasta", None)
            session["intentos_fallidos"] = 0

    # 2. PROCESO NORMAL DE LOGIN
    usuario    = request.form["txtUsuario"]
    contrasena = request.form["txtContrasena"]
        
    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    
    # Validamos credenciales
    sql = "SELECT IdUsuario, Nombre, Tipo_Usuario FROM usuarios WHERE Nombre = %s AND Contrasena = %s"
    cursor.execute(sql, (usuario, contrasena))
    registros = cursor.fetchall()
            
    # Limpiamos sesión previa por seguridad
    session["login"] = False
    session["login-usr"] = None
    session["login-tipo"] = 0
            
    if registros:
        # ---- ÉXITO ----
        usuario_db = registros[0]
        session["login"] = True
        session["login-usr"] = usuario_db["Nombre"]
        session["login-tipo"] = usuario_db["Tipo_Usuario"]
        session["intentos_fallidos"] = 0 # Reiniciar contador
        
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()
            
        return jsonify({
            "mensaje": "Inicio de sesión exitoso",
            "usuario": usuario_db
        })
    else:
        # ---- FALLO ----
        intentos = session.get("intentos_fallidos", 0) + 1
        session["intentos_fallidos"] = intentos
        
        mensaje_error = f"Credenciales incorrectas. Intento {intentos} de 3."
        codigo_estado = 401
        extra_data = {"intentos": intentos}

        if intentos >= 3:
            # 3. APLICAR BLOQUEO Y GUARDAR LOG
            try:
                tz = pytz.timezone("America/Matamoros")
                ahora_log = datetime.datetime.now(tz)
                
                # Guardamos el LOG DE PELIGRO
                cursor.execute("""
                    INSERT INTO LogActividad (actividad, descripcion, fechaHora)
                    VALUES (%s, %s, %s)
                """, ("PELIGRO", f"Se intento iniciar sesion con el usuario '{usuario}' 3 veces. Sistema bloqueado temporalmente.", ahora_log))
                con.commit()
                
                # ACTIVAMOS EL BLOQUEO (Hora actual + 15 segundos)
                session["bloqueo_hasta"] = datetime.datetime.now().timestamp() + 15
                
                mensaje_error = "Has excedido los intentos. Bloqueando sistema por 15s."
                codigo_estado = 429
                extra_data = {"bloqueo": True, "tiempo": 15}
                
                # NO reiniciamos 'intentos_fallidos' a 0 aquí, lo haremos cuando expire el tiempo
                
            except Exception as e:
                print("Error al guardar log:", str(e))
                
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()
        
        respuesta = {"error": mensaje_error}
        respuesta.update(extra_data)
        return jsonify(respuesta), codigo_estado    



@app.route("/cerrarSesion", methods=["POST"])
@login
def cerrarSesion():
    session["login"]      = False
    session["login-usr"]  = None
    session["login-tipo"] = 0
    return make_response(jsonify({}))

@app.route("/preferencias")
@login
def preferencias():
    return make_response(jsonify({
        "usr": session.get("login-usr"),
        "tipo": session.get("login-tipo", 2)
    }))


#############################################################
# Rutas de CRUD Libros ######################################
#############################################################

@app.route("/api/categorias")
def api_categorias():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT idCategoria, nombre FROM Categoria")
        categorias = cursor.fetchall()
        return jsonify(categorias)
    except Exception as e:
        print("Error en /api/categorias:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()



@app.route("/libro/<int:id>")
def api_libro(id):
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Libro WHERE id_libro = %s", (id,))
        libro = cursor.fetchone()
        if libro:
            return jsonify(libro)
        return jsonify({"error": "Libro no encontrado"}), 404
    except Exception as e:
        print("Error en /libro/<id>:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()



@app.route("/libro/<int:id>", methods=["GET"])
@login
def obtener_libro(id):
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql = """
        SELECT 
            l.id_libro   AS idLibro,
            l.titulo     AS titulo,
            l.autor      AS autor,
            l.tipo       AS tipo,
            l.id_categoria AS idCategoria,
            l.sinopsis   AS sinopsis
        FROM Libro l
        WHERE l.id_libro = %s
        """
        cursor.execute(sql, (id,))
        registros = cursor.fetchall()
        if not registros:
            return jsonify({"error": "Libro no encontrado"}), 404
        return jsonify(registros[0])
    except Exception as e:
        print("Error en /libro/<id>:", str(e))
        return jsonify({"error": "Error interno"}), 500
    finally:
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()



"""
CRUD DE LIBROS
"""
@app.route("/crudLibros")
@login
def crud_libros():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)

        cursor.execute("SELECT id_categoria AS idCategoria, nombre FROM Categoria ORDER BY nombre ASC")
        categorias = cursor.fetchall()

        return render_template("crudLibros.html", categorias=categorias)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return "Error al cargar la vista", 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

"""
TBODY LIBROS
"""
@app.route("/tbodyCrudLibros")
@login
def tbodyCrudLibros():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)

        sql = """
        SELECT l.id_libro, l.titulo, l.autor, l.tipo, c.nombre AS categoria
        FROM Libro l
        INNER JOIN Categoria c ON l.id_categoria = c.id_categoria
        ORDER BY l.id_libro DESC
        LIMIT 10 OFFSET 0
        """

        cursor.execute(sql)
        registros = cursor.fetchall()

        return render_template("tbodyCrudLibros.html", libros=registros)

    except Exception as e:
        print("Error en /tbodyCrudLibros:", str(e))
        return jsonify({"error": "Error interno al cargar libros"}), 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

"""
FILTRAR LIBROS POR AUTOR
"""
@app.route("/libros/buscar", methods=["GET"])
@login
def buscarLibros():
    busqueda = request.args.get("busqueda", "").strip()
    busqueda = f"%{busqueda}%"

    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)

        sql = """
        SELECT l.id_libro, l.titulo, l.autor, l.tipo, c.nombre AS categoria
        FROM Libro l
        INNER JOIN Categoria c ON l.id_categoria = c.id_categoria
        WHERE l.titulo LIKE %s OR l.autor LIKE %s
        ORDER BY l.id_libro DESC
        LIMIT 10 OFFSET 0
        """

        val = (busqueda, busqueda)
        cursor.execute(sql, val)
        registros = cursor.fetchall()

    except Exception as e:
        print("Error en /libros/buscar:", str(e))
        registros = []

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

    return make_response(jsonify(registros))

"""
GUARDAR o MODIFICAR LIBROS
"""
@app.route("/libro", methods=["POST"])
@login
def guardarLibro():
    try:
        idLibro     = request.form.get("idLibro", "").strip()
        titulo      = request.form.get("titulo", "").strip()
        autor       = request.form.get("autor", "").strip()
        tipo        = request.form.get("tipo", "").strip()
        idCategoria = request.form.get("idCategoria", "").strip()
        sinopsis    = request.form.get("sinopsis", "").strip()

        if not titulo or not autor or not tipo or not idCategoria:
            return jsonify({"error": "Todos los campos son requeridos"}), 400

        con = con_pool.get_connection()
        cursor = con.cursor()

        if idLibro and idLibro.isdigit():
            sql = """
            UPDATE Libro
            SET titulo = %s, autor = %s, tipo = %s, id_categoria = %s, sinopsis = %s
            WHERE id_libro = %s
            """
            val = (titulo, autor, tipo, idCategoria, sinopsis, idLibro)
            cursor.execute(sql, val)
            con.commit()
        else:
            sql = """
            INSERT INTO Libro (titulo, autor, tipo, id_categoria, sinopsis)
            VALUES (%s, %s, %s, %s, %s)
            """
            val = (titulo, autor, tipo, idCategoria, sinopsis)
            cursor.execute(sql, val)
            con.commit()

        return jsonify({"mensaje": "Libro guardado correctamente"})
    except Exception as e:
        print("Error al guardar libro:", str(e))
        return jsonify({"error": "Error interno al guardar"}), 500
    finally:
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()

"""
    ELIMINAR los LIBROS
"""
@app.route("/libro/eliminar", methods=["POST"])
@login
def eliminar_libro():
    try:
        id_libro = request.form.get("id")
        if not id_libro:
            return jsonify({"error": "ID requerido"}), 400

        con = con_pool.get_connection()
        cursor = con.cursor()
        cursor.execute("DELETE FROM Libro WHERE id_libro = %s", (id_libro,))
        con.commit()

        return jsonify({"mensaje": "Libro eliminado correctamente"})
    except Exception as e:
        print("Error al eliminar libro:", str(e))
        return jsonify({"error": "Error interno al eliminar"}), 500
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


"""
    Guarda los LOGS de la INTERACCION CON EL LIBRO EL OBSERVADR
"""
@app.route("/app/log", methods=["POST"])
def logProductos():
    actividad   = request.form.get("actividad")
    descripcion = request.form.get("descripcion")
    tz          = pytz.timezone("America/Matamoros")
    ahora       = datetime.datetime.now(tz)

    try:
        con = con_pool.get_connection()
        cursor = con.cursor()
        cursor.execute("""
            INSERT INTO LogActividad (actividad, descripcion, fechaHora)
            VALUES (%s, %s, %s)
        """, (actividad, descripcion, ahora))
        con.commit()
        return jsonify({"mensaje": "Log guardado en base de datos"})
    except Exception as e:
        print("Error al guardar log:", str(e))
        return jsonify({"error": "Error al guardar log"}), 500
    finally:
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()


"""
    AUMENTAR POPULARIDAD CON CADA INTERACCION
"""
@app.route("/libro/popularidad", methods=["POST"])
def aumentar_popularidad():
    id_libro = request.form.get("idLibro")

    try:
        con = con_pool.get_connection()
        cursor = con.cursor()
        cursor.execute("""
            UPDATE Libro 
            SET popularidad = COALESCE(popularidad, 0) + 1 
            WHERE id_libro = %s
        """, (id_libro,))
        con.commit()
        return jsonify({"mensaje": "Popularidad actualizada"})
    except Exception as e:
        print("Error al actualizar popularidad:", str(e))
        return jsonify({"error": "Error interno"}), 500
    finally:
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()






# ---------------------------------------------------------
# RUTA PARA LA VISTA DE LOGS
# ---------------------------------------------------------
@app.route("/logs")
@admin_required
def logs_view():
    return render_template("logs.html")
# ---------------------------------------------------------
# RUTA PARA OBTENER LOS DATOS
# ---------------------------------------------------------
@app.route("/tbodyLogs")
@admin_required
def tbodyLogs():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)

        # Seleccionamos los últimos 50 logs ordenados por fecha
        sql = """
            SELECT idLog, actividad, descripcion, fechaHora
            FROM LogActividad
            ORDER BY fechaHora DESC
            LIMIT 50
        """
        cursor.execute(sql)
        logs = cursor.fetchall()
        
        # Formateamos la fecha para que se vea bien
        return render_template("tbodyLogs.html", logs=logs)

    except Exception as e:
        print("Error en /tbodyLogs:", str(e))
        return "Error al cargar logs", 500
    finally:
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()


if __name__ == "__main__":
    app.run(debug=True, port=5000)



"""
#
#///////////////////////////// INTEGRANTES ///////////
#   Rutas  De  Integrantes    
@app.route("/integrantes")
@login
def integrantes():
    return render_template("integrantes.html")

# Traer los registros de integrantes en el tbody
@app.route("/tbodyIntegrantes")
@login
def tbodyProductos():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)

        sql = 
        SELECT idIntegrante, nombreIntegrante
        FROM integrantes
        ORDER BY idIntegrante DESC
        LIMIT 10 OFFSET 0
        
        cursor.execute(sql)
        registros = cursor.fetchall()

        return render_template("tbodyIntegrantes.html", integrantes=registros)

    except Exception as e:
        print("Error en /tbodyIntegrantes:", str(e))
        return jsonify({"error": "Error interno al cargar integrantes"}), 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()


# Funcionamiento de la busuqeda de integrantes
@app.route("/integrantes/buscar", methods=["GET"])
@login
def buscarIntegrantes():
    args     = request.args
    busqueda = args["busqueda"]
    busqueda = f"%{busqueda}%"
    
    try:
        con    = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql    = 
        
        SELECT idIntegrante,
               nombreIntegrante
    
        FROM integrantes
    
        WHERE nombreIntegrante LIKE %s
    
        ORDER BY idIntegrante DESC
        LIMIT 10 OFFSET 0
        
        val = (busqueda,)

        cursor.execute(sql, val)
        registros = cursor.fetchall()

    except mysql.connector.errors.ProgrammingError as error:
        registros = []

    finally:
        if cursor:
            con.close()
        if con and con.is_connected():
            con.close()

    return make_response(jsonify(registros))

# Funionamiento de insertar integrantes
@app.route("/integrante", methods=["POST"])
@login
def guardarIntegrante():
    try:
        idIntegrante = request.form.get("idIntegrante", "").strip()
        nombreIntegrante = request.form.get("nombreIntegrante", "").strip()

        if not nombreIntegrante:
            return jsonify({"error": "Nombre del integrante requerido"}), 400

        con = con_pool.get_connection()
        cursor = con.cursor()

        if idIntegrante:
            sql = 
            UPDATE integrantes
            SET nombreIntegrante = %s
            WHERE idIntegrante = %s
            
            val = (nombreIntegrante, idIntegrante)
        else:
            sql = 
            INSERT INTO integrantes (nombreIntegrante)
            VALUES (%s)
            
            val = (nombreIntegrante,)

        cursor.execute(sql, val)
        con.commit()

        pusherIntegrantes()
        return jsonify({"mensaje": "Integrante guardado correctamente"})

    except Exception as e:
        print("Error al guardar integrante:", str(e))
        return jsonify({"error": "Error interno al guardar"}), 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

# Funcionamiento de modificar integrantes
@app.route("/integrante/<int:id>")
@login
def editarIntegrante(id):
    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = 
    
    SELECT idIntegrante, nombreIntegrante
    
    FROM integrantes
    
    WHERE idIntegrante = %s
    
    val = (id,)

    cursor.execute(sql, val)
    registros = cursor.fetchall()
    
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    if registros:
        return make_response(jsonify(registros[0]))
    else:
        return jsonify({"error": "Integrante no encontrado"}), 404


# Funcionamiento de eliminar integrantes
@app.route("/integrante/eliminar", methods=["POST"])
@login
def eliminarIntegrante():
    try:
        id = request.form["id"]

        con = con_pool.get_connection()
        cursor = con.cursor()
        sql = "DELETE FROM integrantes WHERE idIntegrante = %s"
        val = (id,)

        cursor.execute(sql, val)
        con.commit()

        pusherIntegrantes()
        return make_response(jsonify({"mensaje": "Integrante Eliminado"}))

    except Exception as e:
        print("Error al eliminar integrante:", str(e))
        return jsonify({"error": "Error interno al eliminar"}), 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()
"""







