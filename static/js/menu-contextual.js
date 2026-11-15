document.addEventListener("DOMContentLoaded", function () {
    var menus = Array.from(document.querySelectorAll("[data-menu-contextual]"));
    menus.forEach(function (menu) {
        var disparador = menu.querySelector("summary");
        menu.addEventListener("toggle", function () {
            disparador.setAttribute("aria-expanded", String(menu.open));
            if (menu.open) menus.forEach(function (otro) { if (otro !== menu) otro.open = false; });
        });
        menu.addEventListener("submit", function () { menu.open = false; });
    });
    document.addEventListener("click", function (evento) {
        menus.forEach(function (menu) { if (!menu.contains(evento.target)) menu.open = false; });
    });
    document.addEventListener("keydown", function (evento) {
        if (evento.key !== "Escape") return;
        menus.forEach(function (menu) {
            if (menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
        });
    });
});
