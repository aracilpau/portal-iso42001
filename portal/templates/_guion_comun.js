{#- Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE). -#}
        // Tema: se elige en Ajustes → Aspecto. «Automático» borra la elección y sigue al ordenador.
        function marcarTema() {
            const elegido = document.documentElement.dataset.tema || "";
            document.querySelectorAll("input[name=tema]").forEach(r => { r.checked = r.value === elegido; });
        }
        document.addEventListener("change", e => {
            if (e.target.name !== "tema") return;
            const raiz = document.documentElement;
            if (e.target.value) raiz.dataset.tema = e.target.value;
            else delete raiz.dataset.tema;
            try {
                if (e.target.value) localStorage.setItem("tema", e.target.value);
                else localStorage.removeItem("tema");
            } catch (err) {}
        });
        marcarTema();
        document.addEventListener("htmx:afterSwap", marcarTema);  // al guardar otro ajuste se vuelve a pintar

        // Si el navegador saca la página de su memoria (Atrás o Adelante), se recarga para que
        // no enseñe un estado viejo
        addEventListener("pageshow", e => { if (e.persisted) location.reload(); });

        // Los mensajes («se ha movido…», «ficha guardada»…) llegan en la dirección: se quitan de ella
        // para que no vuelvan a salir al recargar
        const dir = new URL(location.href);
        const mensajes = ["movido", "borrado", "guardado", "retirado", "activado", "situacion", "reabiertos", "nota"].filter(m => dir.searchParams.has(m));
        if (mensajes.length) {
            mensajes.forEach(m => dir.searchParams.delete(m));
            history.replaceState(null, "", dir);
        }

        // Arrastrar archivos encima de un punto (o de la línea de un sistema) los sube a ese punto.
        // Fuera de un punto no hacen nada: sin esto, el navegador abriría el archivo y se saldría del portal.
        function zonaSoltar(zona) {
            document.querySelectorAll(".soltando").forEach(z => { if (z !== zona) z.classList.remove("soltando"); });
            if (zona) zona.classList.add("soltando");
        }
        const llevaArchivos = e => e.dataTransfer && Array.from(e.dataTransfer.types).includes("Files");
        document.addEventListener("dragover", e => {
            if (!llevaArchivos(e)) return;
            e.preventDefault();
            const zona = e.target.closest("[data-soltar]");
            zonaSoltar(zona);
            e.dataTransfer.dropEffect = zona ? "copy" : "none";
        });
        document.addEventListener("dragleave", e => { if (!e.relatedTarget) zonaSoltar(null); });  // sale de la ventana
        document.addEventListener("drop", async e => {
            if (!llevaArchivos(e)) return;
            e.preventDefault();
            const zona = e.target.closest("[data-soltar]");
            zonaSoltar(null);
            if (!zona || !e.dataTransfer.files.length) return;
            const datos = new FormData();
            for (const f of e.dataTransfer.files) datos.append("archivos", f);
            zona.classList.add("subiendo");
            try {
                // Se sube como con «+ Archivo» y se pinta la ficha que devuelve, sin recargar la página
                const r = await fetch(zona.dataset.soltar, { method: "POST", body: datos });
                if (!r.ok) throw new Error(r.status);
                const nueva = new DOMParser().parseFromString(await r.text(), "text/html").getElementById("ficha");
                const actual = document.getElementById("ficha");
                if (!nueva || !actual) throw new Error("sin ficha");
                actual.replaceWith(nueva);
                if (window.htmx) htmx.process(nueva);
            } catch (err) {
                zona.classList.remove("subiendo");
                alert("No se ha podido subir el archivo. Prueba con «+ Archivo».");
            }
        });

        // Lo plegado que se quiere recordar abierto (p. ej. «Opciones avanzadas» de Ajustes): al guardar
        // algo se vuelve a pintar la página y se cerraría. Se recuerda mientras dure la pestaña, y se abre
        // si la dirección lleva a algo de dentro.
        function recordarPlegados() {
            document.querySelectorAll("details[data-recordar][id]").forEach(d => {
                let abierto = false;
                try { abierto = sessionStorage.getItem("abierto-" + d.id) === "1"; } catch (e) {}
                const dentro = location.hash && d.querySelector(CSS.escape ? "#" + CSS.escape(location.hash.slice(1)) : location.hash);
                if (abierto || dentro) d.open = true;
            });
        }
        document.addEventListener("toggle", e => {
            const d = e.target;
            if (d.matches && d.matches("details[data-recordar][id]")) {
                try { sessionStorage.setItem("abierto-" + d.id, d.open ? "1" : "0"); } catch (err) {}
            }
        }, true);
        recordarPlegados();
        document.addEventListener("htmx:afterSwap", recordarPlegados);

        // Las casillas de la ficha: cambian en cuanto se pulsan, sin esperar al servidor; la ficha
        // nueva llega después con los porcentajes. Si no se ha podido guardar, la casilla vuelve atrás y lo dice
        function cambiarCasilla(form) {
            const boton = form.querySelector(".casilla");
            const marcada = boton.classList.toggle("casilla-marcada");
            boton.setAttribute("aria-checked", marcada ? "true" : "false");
            // El recuadro del punto (o de la línea del sistema) se pone verde a la vez que el ✓
            const caja = form.closest("li.punto, li.linea");
            if (caja) caja.classList.toggle("hecho", marcada);
        }
        document.addEventListener("htmx:beforeRequest", e => {
            const form = e.detail.elt;
            if (!form.classList || !form.classList.contains("casilla-form")) return;
            form.querySelectorAll(".casilla-error").forEach(m => m.remove());
            cambiarCasilla(form);
        });
        function casillaSinGuardar(e) {
            const form = e.detail.elt;
            if (!form.classList || !form.classList.contains("casilla-form")) return;
            cambiarCasilla(form);
            const aviso = document.createElement("span");
            aviso.className = "casilla-error";
            aviso.setAttribute("role", "alert");
            aviso.textContent = "No se ha podido guardar. Vuelve a probar.";
            form.appendChild(aviso);
        }
        document.addEventListener("htmx:responseError", casillaSinGuardar);
        document.addEventListener("htmx:sendError", casillaSinGuardar);

        // Declaración: se guarda al elegir la opción, al dejar de escribir el porqué y al salir del cuadro.
        // El portal necesita saber cuál de las tres es: en las dos primeras se está a medio camino.
        document.addEventListener("htmx:configRequest", e => {
            const form = e.detail.elt;
            const ev = e.detail.triggeringEvent;
            if (!form.classList || !form.classList.contains("control-form") || !ev) return;
            const campo = ev.target && ev.target.name;
            if (ev.type === "input" && campo !== "porque") { e.preventDefault(); return; }  // la opción ya va por «change»
            e.detail.parameters.origen = ev.type === "input" ? "porque" : (campo === "aplica" ? "aplica" : "");
            if (campo === "aplica" && !form.querySelector("input[name=aplica]:checked")) e.detail.parameters.quitar = "1";
        });

        // Declaración: volver a pulsar la opción marcada la desmarca y el control vuelve a «sin decidir». Una opción
        // marcada no avisa al pulsarla otra vez, así que se mira cómo estaba justo antes del clic
        let estabaMarcada = null;
        document.addEventListener("pointerdown", e => {
            const etiqueta = e.target.closest && e.target.closest("form.control-form label");
            const opcion = etiqueta ? etiqueta.querySelector("input[name=aplica]") : null;
            estabaMarcada = opcion && opcion.checked ? opcion : null;
        });
        document.addEventListener("click", e => {
            const opcion = e.target.closest && e.target.closest("form.control-form input[name=aplica]");
            if (!opcion || opcion !== estabaMarcada) return;
            estabaMarcada = null;
            opcion.checked = false;
            opcion.dispatchEvent(new Event("change", { bubbles: true }));
        });

        // Al empezar a escribir el porqué, el aviso de lo que falta se cambia al momento, sin esperar a guardar
        document.addEventListener("input", e => {
            const form = e.target.closest && e.target.closest("form.control-form");
            if (!form || e.target.name !== "porque") return;
            const estado = form.querySelector(".guardado-estado");
            estado.className = "guardado-estado";
            estado.textContent = "Se guarda en cuanto dejes de escribir…";
        });

        // Propuesta de la IA: «Cambiar» la pasa al formulario del control para retocarla; se guarda
        // sola, como siempre, al dejar de escribir o al salir del cuadro
        document.addEventListener("click", e => {
            const boton = e.target.closest("[data-cambiar-propuesta]");
            if (!boton) return;
            const control = boton.closest("li");
            const form = control.querySelector("form.control-form");
            const opcion = form.querySelector(`input[name=aplica][value=${boton.dataset.cambiarPropuesta}]`);
            if (opcion) opcion.checked = true;
            const porque = form.querySelector("textarea[name=porque]");
            porque.value = boton.dataset.porque;
            porque.focus();
            porque.setSelectionRange(porque.value.length, porque.value.length);
        });

        // Descargas que tardan (la revisión 9.3): se piden sin salir de la página, con «Preparando…» mientras
        // tanto y el motivo si algo falla
        document.addEventListener("submit", async e => {
            const form = e.target.closest("form[data-descargar]");
            if (!form) return;
            e.preventDefault();
            const boton = form.querySelector("button");
            const error = form.querySelector("[data-descargar-error]");
            form.classList.add("htmx-request");
            boton.disabled = true;
            error.hidden = true;
            try {
                const r = await fetch(form.action, { method: "POST", body: new FormData(form) });
                if (!r.ok) throw new Error(await r.text());
                const nombre = decodeURIComponent((r.headers.get("Content-Disposition") || "").split("''")[1] || "documento.docx");
                const enlace = document.createElement("a");
                enlace.href = URL.createObjectURL(await r.blob());
                enlace.download = nombre;
                enlace.click();
                URL.revokeObjectURL(enlace.href);
            } catch (err) {
                error.textContent = err.message || "No se ha podido preparar. Vuelve a probar.";
                error.hidden = false;
            }
            form.classList.remove("htmx-request");
            boton.disabled = false;
        });

        // Declaración: al cambiar entre aplica y no aplica, el porqué anterior ya no vale. Se vacía y se
        // enseña como referencia; si se vuelve a la decisión de antes, se recupera
        document.addEventListener("change", e => {
            const form = e.target.closest("form[data-decidido]");
            if (!form || e.target.name !== "aplica" || !e.target.checked) return;  // desmarcar no toca el porqué
            const porque = form.querySelector("textarea[name=porque]");
            const cambia = e.target.value !== form.dataset.decidido;
            if (cambia && porque.value === form.dataset.porque) porque.value = "";
            if (!cambia && porque.value === "") porque.value = form.dataset.porque;
            form.querySelector(".control-cambio").hidden = !cambia;
            if (cambia) porque.focus();
        });

        // Lo que no tiene vuelta atrás (borrar del historial, retirar un sistema) pide
        // confirmación en una ventana del portal. El botón lleva a dónde va y qué decir.
        document.addEventListener("click", e => {
            // «Ver»: enseña la contraseña que el administrador pone a otro, para pasársela sin errores
            const ver = e.target.closest("[data-ver]");
            if (ver) {
                const campo = document.getElementById(ver.dataset.ver);
                const oculta = campo.type === "password";
                campo.type = oculta ? "text" : "password";
                ver.textContent = oculta ? "Ocultar" : "Ver";
                ver.setAttribute("aria-pressed", String(oculta));
            }
            const boton = e.target.closest("[data-confirmar]");
            if (boton) {
                // Lo que va con el envío: `data-si` (dar o quitar algo) y `data-campo`, un campo de la página (el nombre
                // nuevo de una empresa), que tiene que estar bien antes de preguntar; en el nombre, {valor} es lo escrito
                const campo = boton.dataset.campo ? document.getElementById(boton.dataset.campo) : null;
                if (campo && !campo.reportValidity()) return;
                const d = document.getElementById("confirmar");
                const envio = d.querySelector(".dialogo-campos");
                envio.replaceChildren();
                const oculto = (nombre, valor) => {
                    const i = document.createElement("input");
                    i.type = "hidden"; i.name = nombre; i.value = valor;
                    envio.append(i);
                };
                if ("si" in boton.dataset) oculto("si", boton.dataset.si);
                if (campo) oculto(campo.name, campo.value.trim());
                d.querySelector("form").action = boton.dataset.confirmar;
                d.querySelector(".dialogo-titulo").textContent = boton.dataset.titulo;
                d.querySelector(".dialogo-nombre").textContent =
                    (boton.dataset.nombre || "").replace("{valor}", campo ? campo.value.trim() : "");
                d.querySelector(".dialogo-ayuda").textContent = boton.dataset.ayuda || "";
                const accion = d.querySelector(".dialogo-boton");
                accion.textContent = boton.dataset.accion;
                // Lo que quita algo (una cuenta), en rojo, como el botón que lo abre
                accion.classList.toggle("boton-peligro", "peligro" in boton.dataset);
                accion.classList.toggle("boton-acento", !("peligro" in boton.dataset));
                d.showModal();
            }
            const cerrar = e.target.closest("[data-cerrar]");
            if (cerrar) {
                const d = cerrar.closest("dialog");
                d.close();
            }
        });
    