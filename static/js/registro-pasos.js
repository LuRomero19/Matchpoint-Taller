document.addEventListener("DOMContentLoaded", function () {
    var formulario = document.querySelector("[data-registro-pasos]");
    if (!formulario) return;

    var pasos = Array.from(formulario.querySelectorAll("[data-registro-paso]"));
    var tarjeta = formulario.closest(".registro-formulario");
    var siguiente = formulario.querySelector("[data-registro-siguiente]");
    var atras = formulario.querySelector("[data-registro-atras]");
    var actual = 0;

    function mostrar(indice, enfocar) {
        actual = indice;
        pasos.forEach(function (paso, posicion) {
            paso.hidden = posicion !== actual;
            paso.querySelector("legend").hidden = true;
        });
        tarjeta.style.setProperty("--registro-avance", ((actual + 1) / pasos.length * 100) + "%");
        atras.hidden = actual === 0;
        siguiente.textContent = actual === pasos.length - 1 ? "Crear cuenta" : "Siguiente";
        if (enfocar) {
            var campo = pasos[actual].querySelector("input[aria-invalid='true'], input:not(:disabled)");
            if (campo) campo.focus({preventScroll: true});
        }
    }

    function validar(indice) {
        var campos = pasos[indice].querySelectorAll("input:not(:disabled)");
        for (var campo of campos) {
            if (!campo.reportValidity()) return false;
        }
        return true;
    }

    atras.addEventListener("click", function () { mostrar(actual - 1, true); });
    formulario.addEventListener("submit", function (evento) {
        if (actual < pasos.length - 1) {
            evento.preventDefault();
            if (validar(actual)) mostrar(actual + 1, true);
            return;
        }
        for (var indice = 0; indice < pasos.length; indice++) {
            var invalido = pasos[indice].querySelector("input:invalid:not(:disabled)");
            if (invalido) {
                evento.preventDefault();
                mostrar(indice, false);
                invalido.reportValidity();
                return;
            }
        }
    });

    var primerError = pasos.findIndex(function (paso) {
        return paso.querySelector("[aria-invalid='true'], .error-campo:not([hidden])");
    });
    mostrar(primerError < 0 ? 0 : primerError, primerError >= 0);
});
