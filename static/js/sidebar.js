/*
 * Alterna o menu lateral recolhivel no modo barra superior (telas <= 991px).
 * Em telas maiores a sidebar fica sempre visivel e o botao hamburger some (CSS),
 * entao este script nao interfere no desktop.
 */
(function () {
    "use strict";

    function toggle(sidebar, button) {
        var isOpen = sidebar.classList.toggle("is-open");
        button.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }

    document.addEventListener("click", function (event) {
        var button = event.target.closest("[data-sidebar-toggle]");
        if (button) {
            var sidebar = button.closest(".tickets-sidebar");
            if (sidebar) {
                toggle(sidebar, button);
            }
            return;
        }

        // Clicar em um link do menu fecha a barra (melhor navegacao no mobile).
        var link = event.target.closest(".tickets-sidebar .menu-link");
        if (link) {
            var openSidebar = link.closest(".tickets-sidebar.is-open");
            if (openSidebar) {
                openSidebar.classList.remove("is-open");
                var toggleBtn = openSidebar.querySelector("[data-sidebar-toggle]");
                if (toggleBtn) {
                    toggleBtn.setAttribute("aria-expanded", "false");
                }
            }
        }
    });
})();
