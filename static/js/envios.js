document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-entrega]").forEach(function (boton) {
        boton.addEventListener("click", function () {
            var panel = document.getElementById(boton.getAttribute("aria-controls"));
            var abrir = boton.getAttribute("aria-expanded") !== "true";
            panel.hidden = !abrir;
            boton.setAttribute("aria-expanded", String(abrir));
            boton.textContent = abrir ? "Ocultar entrega" : "Ver entrega";
        });
    });
});
