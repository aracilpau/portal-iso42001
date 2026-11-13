// Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
// El chat («Preguntar»): el panel.
// La conversación vive en el portal mientras esté abierto; aquí se recuerda en la pestaña (al cambiar de página
// el panel sigue con lo que había) y se pierde al cerrarla.
(() => {
    const panel = document.getElementById("chat");
    if (!panel) return;
    const mensajes = document.getElementById("chat-mensajes");
    const form = document.getElementById("chat-form");
    const caja = form.querySelector("textarea");
    const enviar = form.querySelector("[data-chat-enviar]");
    const parar = form.querySelector("[data-chat-parar]");
    const guardado = { leer(c, d) { try { return JSON.parse(sessionStorage.getItem("chat-" + c)) ?? d; } catch (e) { return d; } },
                       poner(c, v) { try { sessionStorage.setItem("chat-" + c, JSON.stringify(v)); } catch (e) {} } };
    let id = guardado.leer("id", "");
    let historia = guardado.leer("historia", []);   // [{quien: "tu" | "claude" | "error", texto}]
    let hablando = false;

    // Formato sencillo de las respuestas: negritas, listas, saltos de línea y enlaces del propio portal
    function formato(texto) {
        const seguro = texto.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        const enlaces = seguro.replace(/\[([^\]]+)\]\((\/[^)\s]*)\)/g, '<a href="$2">$1</a>');
        const negritas = enlaces.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        const lineas = negritas.split("\n");
        let html = "", lista = false;
        for (const l of lineas) {
            const item = l.match(/^\s*(?:[-*]|\d+\.)\s+(.*)$/);
            if (item) { if (!lista) { html += "<ul>"; lista = true; } html += `<li>${item[1]}</li>`; continue; }
            if (lista) { html += "</ul>"; lista = false; }
            html += l.trim() ? `<p>${l}</p>` : "";
        }
        return html + (lista ? "</ul>" : "");
    }

    function pintar() {
        mensajes.innerHTML = historia.length ? "" :
            '<p class="chat-vacio">Pregunta sobre la norma («¿qué tengo que entregar en la 7.2?») o sobre el portal ' +
            '(«¿qué diferencia hay entre renovar y subir versión nueva?»). Solo consulta: no cambia nada.</p>';
        for (const m of historia) {
            const div = document.createElement("div");
            div.className = "chat-mensaje chat-" + m.quien;
            div.innerHTML = m.quien === "tu" ? formato(m.texto).replace(/<\/?ul>|<\/?li>/g, "") : formato(m.texto);
            mensajes.append(div);
        }
        mensajes.scrollTop = mensajes.scrollHeight;
    }

    function abrir(abierto) {
        panel.hidden = !abierto;
        document.body.classList.toggle("con-chat", abierto);
        guardado.poner("abierto", abierto);
        if (abierto) { pintar(); caja.focus(); }
    }

    function ocupado(si) {
        hablando = si;
        enviar.hidden = si;
        parar.hidden = !si;
        caja.disabled = si;
    }

    async function preguntar(pregunta) {
        historia.push({ quien: "tu", texto: pregunta }, { quien: "claude", texto: "" });
        const respuesta = historia[historia.length - 1];
        pintar();
        const estado = document.createElement("p");
        estado.className = "chat-estado";
        estado.textContent = "Pensando…";
        mensajes.append(estado);
        ocupado(true);
        const datos = new FormData();
        datos.append("id", id);
        datos.append("pregunta", pregunta);
        datos.append("pagina", `${document.title} (${location.pathname})`);
        try {
            const r = await fetch("/chat", { method: "POST", body: datos });
            const lector = r.body.getReader();
            const texto = new TextDecoder();
            let resto = "";
            while (true) {
                const { value, done } = await lector.read();
                if (done) break;
                resto += texto.decode(value, { stream: true });
                const eventos = resto.split("\n\n");
                resto = eventos.pop();
                for (const ev of eventos) {
                    if (!ev.startsWith("data: ")) continue;
                    const d = JSON.parse(ev.slice(6));
                    if (d.id) { id = d.id; guardado.poner("id", id); }
                    if (d.consulta) estado.textContent = d.consulta + "…";
                    if (d.texto) {
                        respuesta.texto += d.texto;
                        const ultimo = [...mensajes.querySelectorAll(".chat-claude")].pop();
                        if (ultimo) ultimo.innerHTML = formato(respuesta.texto);
                        estado.textContent = "";
                        mensajes.scrollTop = mensajes.scrollHeight;
                    }
                    if (d.error) historia.push({ quien: "error", texto: d.error });
                }
            }
        } catch (e) {
            historia.push({ quien: "error", texto: "Se ha cortado la conexión con el portal. Vuelve a probar." });
        }
        if (!respuesta.texto) historia.splice(historia.indexOf(respuesta), 1);
        guardado.poner("historia", historia);
        ocupado(false);
        pintar();
        caja.focus();
    }

    form.addEventListener("submit", e => {
        e.preventDefault();
        const pregunta = caja.value.trim();
        if (!pregunta || hablando) return;
        caja.value = "";
        preguntar(pregunta);
    });
    caja.addEventListener("keydown", e => {   // Intro envía; Mayúsculas + Intro, salto de línea
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
    });
    parar.addEventListener("click", () => { if (id) fetch(`/chat/${id}/parar`, { method: "POST" }); });
    document.querySelectorAll("[data-chat-abrir]").forEach(b => b.addEventListener("click", e => {
        e.preventDefault();
        abrir(panel.hidden);
    }));
    panel.querySelector("[data-chat-cerrar]").addEventListener("click", () => abrir(false));
    panel.querySelector("[data-chat-nueva]").addEventListener("click", () => {
        if (hablando) return;
        if (id) fetch(`/chat/${id}/cerrar`, { method: "POST" });
        id = ""; historia = [];
        guardado.poner("id", id); guardado.poner("historia", historia);
        pintar(); caja.focus();
    });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && !panel.hidden && !hablando) abrir(false); });

    if (guardado.leer("abierto", false)) abrir(true);
})();
