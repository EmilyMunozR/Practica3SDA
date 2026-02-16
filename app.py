
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

        cursor.execute("""
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


######## Fin de Rutas de INICIO

    
# Funcionamiento del Inicio de sesion
@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    
    usuario    = request.form["txtUsuario"]
    contrasena = request.form["txtContrasena"]
        
    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    SELECT IdUsuario, Nombre, Tipo_Usuario
    FROM usuarios
            
    WHERE Nombre = %s 
    AND Contrasena = %s
    """
    val = (usuario, contrasena)
        
    cursor.execute(sql, val)
    registros = cursor.fetchall()
            
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()
            
    session["login"]      = False
    session["login-usr"]  = None
    session["login-tipo"] = 0
            
    if registros:
        usuario = registros[0]
        session["login"]      = True
        session["login-usr"]  = usuario["Nombre"]
        session["login-tipo"] = usuario["Tipo_Usuario"]
        return jsonify({
            "mensaje": "Inicio de sesión exitoso",
            "usuario": usuario
        })
    else:
        return jsonify({
            "error": "Credenciales incorrectas"
        }), 401

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






@app.route("/api/libros")
@login
def api_libros():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)

        sql = "SELECT id_libro, titulo, autor, tipo FROM Libro ORDER BY id_libro DESC"
        cursor.execute(sql)
        libros = cursor.fetchall()
        return jsonify(libros)

    except Exception as e:
        print("Error en /api/libros:", str(e))
        return jsonify({"error": "Error interno al cargar libros"}), 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()



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


"""
CATEGORIAS RUTAS
"""
@app.route("/categorias")
@login
def obtener_categorias():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)

        sql = "SELECT id_categoria AS idCategoria, nombre FROM Categoria ORDER BY nombre ASC"
        cursor.execute(sql)
        categorias = cursor.fetchall()

        return jsonify(categorias)

    except Exception as e:
        print("Error en /categorias:", str(e))
        return jsonify({"error": "Error al obtener categorías"}), 500

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

"""
    CRUD CATEGORIAS
"""

@app.route("/crudCategorias")
@login
def crud_categorias():
    return render_template("crudCategorias.html")

@app.route("/tbodyCrudCategorias")
@login
def tbody_categorias():
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT id_categoria, nombre FROM Categoria ORDER BY id_categoria DESC")
        categorias = cursor.fetchall()
        return render_template("tbodyCrudCategorias.html", categorias=categorias)
    except Exception as e:
        print("Error en /tbodyCrudCategorias:", str(e))
        return jsonify({"error": "Error interno"}), 500
    finally:
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()

@app.route("/categoria", methods=["POST"])
@login
def guardar_categoria():
    try:
        id_categoria = request.form.get("idCategoria")
        nombre = request.form.get("nombre")

        con = con_pool.get_connection()
        cursor = con.cursor()

        if id_categoria:
            cursor.execute("UPDATE Categoria SET nombre = %s WHERE id_categoria = %s", (nombre, id_categoria))
        else:
            cursor.execute("INSERT INTO Categoria (nombre) VALUES (%s)", (nombre,))
        con.commit()

        return jsonify({"mensaje": "Categoría guardada correctamente."})
    except Exception as e:
        print("Error al guardar categoría:", str(e))
        return jsonify({"error": "Error al guardar categoría"}), 500
    finally:
        if cursor: cursor.close()
        if con and con.is_connected(): con.close()

@app.route("/categoria/eliminar", methods=["POST"])
@login
def eliminar_categoria():
    try:
        id_categoria = request.form.get("id")
        con = con_pool.get_connection()
        cursor = con.cursor()
        cursor.execute("DELETE FROM Categoria WHERE id_categoria = %s", (id_categoria,))
        con.commit()
        return jsonify({"mensaje": "Categoría eliminada correctamente."})
    except Exception as e:
        print("Error al eliminar categoría:", str(e))
        return jsonify({"error": "Error al eliminar categoría"}), 500
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



























