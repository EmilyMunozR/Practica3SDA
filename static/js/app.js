
function activeMenuOption(href) {
    $(".app-menu .nav-link")
        .removeClass("active")
        .removeAttr("aria-current");

    $(`[href="${(href ? href : "#/")}"]`)
        .addClass("active")
        .attr("aria-current", "page");
}

function disableAll() {
    const elements = document.querySelectorAll(".while-waiting")
    elements.forEach(function (el, index) {
        el.setAttribute("disabled", "true")
        el.classList.add("disabled")
    })
}
function enableAll() {
    const elements = document.querySelectorAll(".while-waiting")
    elements.forEach(function (el, index) {
        el.removeAttribute("disabled")
        el.classList.remove("disabled")
    })
}

function modal(msg, titulo, opciones) {
  const html = `
    <div class="modal fade" id="modalMsg" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">${titulo}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">${msg}</div>
          <div class="modal-footer">
            <button type="button" class="${opciones.class}" data-bs-dismiss="modal">${opciones.html}</button>
          </div>
        </div>
      </div>
    </div>
  `;
  $("body").append(html);
  const modalInstance = new bootstrap.Modal(document.getElementById("modalMsg"));
  modalInstance.show();
  $("#modalMsg").on("hidden.bs.modal", function () {
    $(this).remove();
  });
}

function pop(selector, msg, tipo) {
  $(selector).html(`<div class="alert alert-${tipo}">${msg}</div>`);
}

function toast(msg, tiempo) {
  alert(msg);
}

const app = angular.module("angularjsApp", ["ngRoute"]);
app.config(function ($routeProvider, $locationProvider, $provide) {
    $locationProvider.hashPrefix("");

    $routeProvider
        .when("/", {
            templateUrl: "/login",
            controller: "loginCtrl"
        })
        .when("/inicio", {
            templateUrl: "/inicio",
            controller: "inicioCtrl"
        })
        .when("/crudLibros", {
            templateUrl: "/crudLibros",
            controller: "crudLibrosCtrl"
        })
        .otherwise({
            redirectTo: "/"
        });


    $provide.decorator("MensajesService", function ($delegate, $log) {
        const originalModal = $delegate.modal;
        const originalPop   = $delegate.pop;
        const originalToast = $delegate.toast;
    
        $delegate.modal = function (msg) {
          originalModal(msg, "Libro", {
            html: "Aceptar",
            class: "btn btn-lg btn-secondary",
            defaultButton: true,
            dismiss: true
          });
        };
    
        $delegate.pop = function (msg) {
          $(".div-temporal").remove();
          $("body").prepend($("<div />", {
            class: "div-temporal bg-info text-white p-2 rounded shadow-sm",
            html: msg
          }));
          originalPop(".div-temporal", msg, "info");
        };
    
        $delegate.toast = function (msg) {
          originalToast(msg, 2);
        };
    
        return $delegate;
      });
    });

// Servicio Singleton para sesión
app.service("SessionService", function () {
    this.tipo = null;
    this.usr = null;

    this.setTipo = function (tipo) {
        this.tipo = tipo;
    };
    this.getTipo = function () {
        return this.tipo;
    };

    this.setUsr = function (usr) {
        this.usr = usr;
    };
    this.getUsr = function () {
        return this.usr;
    };
});

app.service("MensajesService", function () {
  this.modal = modal;
  this.pop   = pop;
  this.toast = toast;
});

//
//    API DE LIBROS
//
app.service("LibroAPI", function ($q) {
  this.libro = function (id) {
    const deferred = $q.defer()

    $.get(`/libro/${id}`)
    .done(function (libro){
        deferred.resolve(libro)
    })
    .fail(function (error){
        deferred.reject(error)
    })
    return deferred.promise;
  }
})


app.run(["$rootScope", "$location", "$timeout", "SessionService", function($rootScope, $location, $timeout, SessionService) {
    
        $rootScope.slide        = "";
        $rootScope.spinnerGrow  = false
        $rootScope.login        = false
    
    function actualizarFechaHora() {
        // DateTime debe existir (luxon). lxFechaHora es global en este scope.
        lxFechaHora = DateTime.now().setLocale("es");
        $rootScope.angularjsHora = lxFechaHora.toFormat("hh:mm:ss a");
        $timeout(actualizarFechaHora, 1000);
    }
    actualizarFechaHora();

    let preferencias = localStorage.getItem("preferencias")
    try {
        preferencias = (preferencias ? JSON.parse(preferencias) : {})
    } catch (error) {
        preferencias = {}
    }
    
    $rootScope.preferencias = preferencias;
    $rootScope.user = preferencias.usr || "";
    $rootScope.tipo = preferencias.tipo || "";
    
    SessionService.setTipo(preferencias.tipo)
    SessionService.setUsr(preferencias.usr)
    
    $rootScope.$on("$routeChangeSuccess", function (event, current, previous) {
        $("html").css("overflow-x", "hidden");
    console.log("Preferencias cargadas:", preferencias);
    console.log("Usuario en rootScope:", $rootScope.user);

        const path = current && current.$$route ? current.$$route.originalPath : "/";

        if (path.indexOf("splash") === -1) {
            const active = $(".app-menu .nav-link.active").parent().index();
            const click  = $(`[href^="#${path}"]`).parent().index();

            if (active !== click) {
                $rootScope.slide = "animate__animated animate__faster animate__slideIn";
                $rootScope.slide += ((active > click) ? "Left" : "Right");
            }

            $timeout(function () {
                $("html").css("overflow-x", "auto");
                $rootScope.slide = "";
            }, 1000);

            activeMenuOption(`#${path}`);
        }
    });
}]);

///
///    DECORADOR DE INFO COMPLETA DE LIBROS
///
const LibroDecorator = {
  decorar: function (libro) {
    libro.mostrarCompleto = function () {
      return `
        <b>Título:</b> ${libro.titulo}<br>
        <b>Autor:</b> ${libro.autor}<br>
        <b>Tipo:</b> ${libro.tipo}<br>
        <b>Categoría:</b> ${libro.categoria || "Sin categoría"}<br>
        <b>Popularidad:</b> ${libro.popularidad || "N/A"}<br>
        <b>Disponible:</b> ${libro.disponible ? "Sí" : "No"}<br>
        <b>Sinopsis:</b> ${libro.sinopsis || "Sin sinopsis"}<br>
        <b>Editorial:</b> ${libro.editorial || "N/A"}<br>
        <b>Páginas:</b> ${libro.paginas || "N/A"}<br>
        <b>Idioma:</b> ${libro.idioma || "N/A"}<br>
        <img src="${libro.portada}" class="img-fluid mt-2" alt="Portada del libro">
      `;
    };

    return libro;
  }
};

const LibroFactory = {
    getFiltro: function (tipo) {
        switch (tipo) {
            case "fisico":
                return {
                    filtrar: function (libros) {
                        return libros.filter(l => l.tipo === "fisico");
                    }
                };
            case "digital":
                return {
                    filtrar: function (libros) {
                        return libros.filter(l => l.tipo === "digital");
                    }
                };
            case "mixto":
                return {
                    filtrar: function (libros) {
                        return libros.filter(l => l.tipo === "mixto");
                    }
                };
            default:
                return {
                    filtrar: function (libros) {
                        return libros;
                    }
                };
        }
    }
};

app.factory("LibroCategoriaFactory", function () {
    function Categoria(titulo, libros) {
        this.titulo = titulo;
        this.libros = libros;
    }

    Categoria.prototype.getInfo = function () {
        return {
            titulo: this.titulo,
            libros: this.libros
        };
    };

    return {
        create: function (titulo, libros) {
            return new Categoria(titulo, libros);
        }
    };
});
//
//    Factory FACADE donde junto las categorias con libros
//
app.factory("LibroFormularioFacade", function (LibroAPI, CategoriaAPI, $q) {
  return {
    obtenerLibroFormulario: function (idLibro) {
      return $q.all({
        libro: LibroAPI.libro(idLibro),
        categorias: CategoriaAPI.categorias()
      });
    }
  };
});

// Inicio de Sesion Controller
app.controller("loginCtrl", function ($scope, $http, $rootScope, $location, SessionService) {
    $rootScope.login = false;
    $("#frmInicioSesion").submit(function (event) {
        event.preventDefault();

        $.post("/iniciarSesion", $(this).serialize(), function (respuesta) {
            enableAll();

            if (respuesta.mensaje) {
                $rootScope.login = true;
            
                // Guardar en Singleton
                SessionService.setUsr(respuesta.usuario.Nombre);
                SessionService.setTipo(respuesta.usuario.Tipo_Usuario);
            
                // Guardar en localStorage para que app.run() lo lea
                localStorage.setItem("preferencias", JSON.stringify({
                    usr: respuesta.usuario.Nombre,
                    tipo: respuesta.usuario.Tipo_Usuario
                }));
            
                window.location.href = "#/inicio";
                return;
            }
            pop(".div-inicio-sesion", "Usuario y/o contrase&ntilde;a incorrecto(s)", "danger");
        });

        disableAll();
    });
});


// Inicio Controller 
app.controller("inicioCtrl", ["$scope", "$http", "SessionService", function ($scope, $http, SessionService) {
  $scope.SesionService = SessionService;

  $http.get("/api/libros").then(function (respuesta) {
      
    const todos = respuesta.data;
      
    $scope.librosFisicos = todos.filter(l => l.tipo === "fisico");
    $scope.librosDigitales = todos.filter(l => l.tipo === "digital");
    $scope.librosMixtos = todos.filter(l => l.tipo === "mixto");
  });
}]);



$(document).ready(function () {
  $("#frmLibro")
    .off("submit")
    .submit(function (event) {
      event.preventDefault();

      disableAll();

      $.post("/libro", {
        idLibro: $("#idLibro").val(),
        titulo: $("#txtTitulo").val(),
        autor: $("#txtAutor").val(),
        tipo: $("#txtTipo").val(),
        idCategoria: $("#txtCategoria").val()
      }, function (respuesta) {
        if (respuesta.mensaje) {
          $("#frmLibro")[0].reset();
          $("#idLibro").val("");
          $("#tbodyCrudLibros").load("/tbodyCrudLibros");
          MensajesService.pop("📚 Libro guardado correctamente.");
        } else {
          MensajesService.toast(respuesta.error || "Error al guardar");
        }

        enableAll();
      });
    });
});

console.log("Facade:", typeof LibroFormularioFacade); // Debe decir "object"

///
///    GUARDAR LIBRO
///
const LibroGuardarMediator = {
  guardar: function (libro, $scope, $http, MensajesService) {
    const datos = {
      idLibro: libro.idLibro || "",
      titulo: libro.titulo,
      autor: libro.autor,
      tipo: libro.tipo,
      idCategoria: libro.idCategoria,
      sinopsis: libro.sinopsis || ""
    };

    // Validacion baisca
    if (!libro.titulo || !libro.autor || !libro.tipo || !libro.idCategoria) {
      MensajesService.toast("llena todos los campos Correctamente");
      return;
    }

    // Guardar en backend
    $http.post("/libro", $.param(datos), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" }
    }).then(function (res) {
      if (res.data.mensaje) {
        $scope.libro = {};
        $scope.isModificando = false;
        $scope.cargarLibros();
        MensajesService.pop("Libro guardado correctamente");
      } else {
        MensajesService.toast(res.data.error || "Error al guardar el Libro");
      }
    });
  }
};



//
//    CONTROLADOR DE LIBROS
//
app.controller("crudLibrosCtrl", function ($scope, $http, MensajesService, LibroFormularioFacade) {
  $scope.libros = [];
  $scope.libro = {};
  $scope.isModificando = false;

  $scope.cargarLibros = function () {
    $("#tbodyCrudLibros").load("/tbodyCrudLibros");
  };

  $scope.cargarLibros();
    
    LibroFormularioFacade.obtenerLibroFormulario("").then(function (respuesta) {
        $scope.libro = {}; 
        $scope.categorias = respuesta.categorias;
        $scope.$apply();
    });

/// GUARDAR LIBRO CON MEDIATOR
   $(document).off("click", "#btnGuardarLibro").on("click", "#btnGuardarLibro", function () {
    LibroGuardarMediator.guardar($scope.libro, $scope, $http, MensajesService);
  });

  // MODIFICAR
  $(document).off("click", ".btnModificarLibro").on("click", ".btnModificarLibro", function () {
    const id = $(this).data("id");

    $http.get("/libro/" + id).then(function (res) {
      $scope.libro = res.data;       
      $scope.isModificando = true;      
      $scope.$apply();
    });
  });


  $(document).on("click", ".btnEliminarLibro", function () {
    const id = $(this).data("id");

    if (confirm("¿Seguro que deseas eliminar este libro?")) {
      $http.post("/libro/eliminar", $.param({ id: id }), {
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
      }).then(function () {
        $scope.cargarLibros();
        MensajesService.pop("Se elimno el Libro");
      });
    }
  });

 $(document).on("click", ".btnVerLibro", function () {
    const id = $(this).data("id");

    $http.get("/libro/" + id).then(function (res) {
        const libroO = res.data;
        
        $.post("/app/log", {
            actividad: "Visualización de libro",
            descripcion: `Se interactuo con el libro "${libroO.titulo}"`
        });
        
        $.post("/libro/popularidad", { idLibro: id });
        
        console.log(`El Libro ${libroO.titulo} fue visto`);
        
        /// DECORADOR
        const libro = LibroDecorator.decorar(libroO);
        MensajesService.modal(libro.mostrarCompleto());
    });
  });
    
});


const DateTime = luxon.DateTime;
let lxFechaHora = null;

document.addEventListener("DOMContentLoaded", function (event) {
    const configFechaHora = {
        locale: "es",
        weekNumbers: true,
        minuteIncrement: 15,
        altInput: true,
        altFormat: "d/F/Y",
        dateFormat: "Y-m-d"
    };

    activeMenuOption(location.hash);
});

/*
///////////////////////////////////////////////////////////////////////// Integrantes controller
app.controller("integrantesCtrl", function ($scope, $http) {
    function buscarIntegrantes() {
        $.get("/tbodyIntegrantes", function (trsHTML) {
            $("#tbodyIntegrantes").html(trsHTML);
        }).fail(function () {
            console.log("Error al cargar integrantes");
        });
    }

    buscarIntegrantes();

    Pusher.logToConsole = true;

    var pusher = new Pusher('85576a197a0fb5c211de', { cluster: 'us2' });
    var channel = pusher.subscribe("integranteschannel");
    
    channel.bind("integrantesevent", function(data) {
        console.log("Evento recibido de Pusher");
        buscarIntegrantes();
    });
//////////////////////////////////////////////////////////////////////////// Insertar Integrantes
    $(document).on("submit", "#frmIntegrante", function (event) {
        event.preventDefault();
        
        const id = $("#idIntegrante").val().trim()
        const nombreIntegrante = $("#txtNombreIntegrante").val().trim()

         if (!nombreIntegrante) {
            alert("Por favor ingresa un integrante.")
            return
        }
        $.post("/integrante", {
            idIntegrante: id,
            nombreIntegrante: nombreIntegrante
        }).done(function () {
            alert("Integrante Añadido correctamente");
            $("#frmIntegrante")[0].reset();
            $("#btnGuardarIntegrante").text("Guardar")
            buscarIntegrantes();
        }).fail(function () {
            alert("Error al guardar integrante");
        });
    });
});
///////////////////////////////////////////////////////////////////////////// Modificar Integraantes
$(document).on("click", ".btnModificarIntegrante", function () {
    const id = $(this).data("id");

    $.get(`/integrante/${id}`, function (data) {
        $("#idIntegrante").val(data.idIntegrante);
        $("#txtNombreIntegrante").val(data.nombreIntegrante);
        $(".btn-primary").text("Actualizar"); 
    }).fail(function () {
        alert("Error al traer integrante");
    });
});
////////////////////////////////////////////////////////////////////////////// Eliminar Integrantes 
$(document).on("click", ".btnEliminarIntegrante", function () {
    const id = $(this).data("id");

    if (confirm("¿Seguro que quieres eliminar este integrante?")) {
        $.post("/integrante/eliminar", { id: id }, function () {
            $(`button[data-id='${id}']`).closest("tr").remove();
        }).fail(function () {
            alert("Error al eliminar el integrante");
        });
    }
});
*/
