document.addEventListener("DOMContentLoaded", function () {
    var menu = document.querySelector("[data-reserva-menu]");
    if (!menu) return;
    var disparador = menu.querySelector("summary");
    menu.addEventListener("toggle", function () { disparador.setAttribute("aria-expanded", String(menu.open)); });
    document.addEventListener("click", function (evento) { if (!menu.contains(evento.target)) menu.open = false; });
    document.addEventListener("keydown", function (evento) {
        if (evento.key === "Escape" && menu.open) {
            menu.open = false;
            disparador.focus();
        }
    });
    menu.addEventListener("submit", function () { menu.open = false; });
    var modal = document.querySelector("[data-modal-anulacion]");
    if (!modal) return;
    function abrir() {
        menu.open = false;
        document.documentElement.classList.add("modal-abierto");
        modal.showModal();
        modal.querySelector("[name=motivo]").focus();
    }
    menu.querySelector("[data-abrir-anulacion]").addEventListener("click", abrir);
    modal.querySelector("[data-cerrar-anulacion]").addEventListener("click", function () { modal.close(); });
    modal.addEventListener("close", function () {
        document.documentElement.classList.remove("modal-abierto");
        disparador.focus();
    });
    if (modal.hasAttribute("data-abrir-inicialmente")) abrir();
});
