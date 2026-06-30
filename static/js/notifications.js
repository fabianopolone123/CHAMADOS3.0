(function () {
    const TOAST_SELECTOR = "[data-toast]";
    const CLOSE_SELECTOR = "[data-toast-close]";
    const EXIT_DELAY_MS = 240;

    function closeToast(toast) {
        if (!toast || toast.classList.contains("is-closing")) {
            return;
        }

        toast.classList.add("is-closing");
        window.setTimeout(() => {
            toast.remove();
        }, EXIT_DELAY_MS);
    }

    function initializeToast(toast) {
        const timeout = Number(toast.dataset.timeout || 2800);
        toast.style.setProperty("--toast-duration", `${timeout}ms`);

        const closeButton = toast.querySelector(CLOSE_SELECTOR);
        if (closeButton) {
            closeButton.addEventListener("click", () => closeToast(toast));
        }

        let autoClose = window.setTimeout(() => closeToast(toast), timeout);

        toast.addEventListener("mouseenter", () => {
            window.clearTimeout(autoClose);
            const progressBar = toast.querySelector(".app-toast__progress");
            if (progressBar) {
                progressBar.style.animationPlayState = "paused";
            }
        });

        toast.addEventListener("mouseleave", () => {
            const progressBar = toast.querySelector(".app-toast__progress");
            if (progressBar) {
                progressBar.style.animationPlayState = "running";
            }
            autoClose = window.setTimeout(() => closeToast(toast), 1400);
        });
    }

    function initializeToasts(root = document) {
        root.querySelectorAll(TOAST_SELECTOR).forEach(initializeToast);
    }

    function ensureToastStack() {
        let stack = document.querySelector(".toast-stack");
        if (!stack) {
            stack = document.createElement("div");
            stack.className = "toast-stack";
            stack.setAttribute("aria-live", "polite");
            stack.setAttribute("aria-atomic", "true");
            document.body.appendChild(stack);
        }
        return stack;
    }

    function getToastTitle(type) {
        if (type === "success") {
            return "Sucesso";
        }
        if (type === "error") {
            return "Erro";
        }
        if (type === "warning") {
            return "Aviso";
        }
        return "Informacao";
    }

    function getToastIcon(type) {
        if (type === "success") {
            return "OK";
        }
        if (type === "error") {
            return "!";
        }
        if (type === "warning") {
            return "!";
        }
        return "i";
    }

    function createToastElement({ type = "info", title, message, timeout = 2800 }) {
        const toast = document.createElement("div");
        toast.className = `app-toast app-toast--${type}`;
        toast.dataset.toast = "";
        toast.dataset.timeout = String(timeout);
        toast.setAttribute("role", "status");

        const safeTitle = title || getToastTitle(type);
        const safeMessage = message || "";
        const iconText = getToastIcon(type);

        toast.innerHTML = `
            <div class="app-toast__icon" aria-hidden="true">
                <span>${iconText}</span>
            </div>
            <div class="app-toast__body">
                <div class="app-toast__title">${safeTitle}</div>
                <div class="app-toast__message"></div>
                <div class="app-toast__progress" aria-hidden="true"></div>
            </div>
            <button type="button" class="app-toast__close" data-toast-close aria-label="Fechar notificacao">x</button>
        `;

        const messageElement = toast.querySelector(".app-toast__message");
        if (messageElement) {
            messageElement.textContent = safeMessage;
        }

        return toast;
    }

    function showAppToast(message, type = "info", options = {}) {
        const stack = ensureToastStack();
        const toast = createToastElement({
            type,
            title: options.title,
            message,
            timeout: options.timeout || 2800,
        });

        stack.appendChild(toast);
        initializeToast(toast);
        return toast;
    }

    window.showAppToast = showAppToast;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => initializeToasts());
    } else {
        initializeToasts();
    }
})();
