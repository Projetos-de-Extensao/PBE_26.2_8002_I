/*
 * Interações visuais da interface (sem regras de negócio).
 * Tudo aqui é melhoria progressiva: sem JavaScript, as páginas continuam
 * funcionando com os formulários e links normais do Django.
 */
(function () {
  "use strict";

  function icone(nome) {
    return '<svg class="icon" aria-hidden="true"><use href="#i-' + nome + '"></use></svg>';
  }

  /* Menu lateral no celular ------------------------------------------------ */
  function iniciarMenu() {
    var app = document.querySelector("[data-app]");
    var botao = document.querySelector("[data-nav-toggle]");
    if (!app || !botao) return;

    var overlay = document.createElement("div");
    overlay.className = "nav-overlay";
    overlay.hidden = true;
    app.appendChild(overlay);

    function definir(aberto) {
      app.classList.toggle("is-nav-open", aberto);
      overlay.hidden = !aberto;
      botao.setAttribute("aria-expanded", aberto ? "true" : "false");
    }

    botao.addEventListener("click", function () {
      definir(!app.classList.contains("is-nav-open"));
    });
    overlay.addEventListener("click", function () { definir(false); });
    document.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape") definir(false);
    });
  }

  /* Fechar mensagens -------------------------------------------------------- */
  function iniciarAlertas() {
    document.querySelectorAll("[data-dismiss]").forEach(function (botao) {
      botao.addEventListener("click", function () {
        var alvo = botao.closest(".alert");
        if (alvo) alvo.remove();
      });
    });
  }

  /* Mostrar/ocultar senha --------------------------------------------------- */
  function iniciarCamposDeSenha() {
    document.querySelectorAll('input[type="password"]').forEach(function (campo) {
      if (campo.closest(".password-field")) return;
      var envoltorio = document.createElement("div");
      envoltorio.className = "password-field";
      campo.parentNode.insertBefore(envoltorio, campo);
      envoltorio.appendChild(campo);

      var botao = document.createElement("button");
      botao.type = "button";
      botao.className = "password-toggle";
      botao.setAttribute("aria-label", "Mostrar senha");
      botao.innerHTML = icone("eye");
      botao.addEventListener("click", function () {
        var visivel = campo.type === "text";
        campo.type = visivel ? "password" : "text";
        botao.setAttribute("aria-label", visivel ? "Mostrar senha" : "Ocultar senha");
      });
      envoltorio.appendChild(botao);
    });
  }

  /* Confirmação antes de enviar (ex.: cancelar agendamento) ----------------- */
  function iniciarConfirmacoes() {
    var formularios = document.querySelectorAll("form[data-confirm]");
    if (!formularios.length) return;

    var modal = document.createElement("dialog");
    if (typeof modal.showModal !== "function") return;
    modal.setAttribute("aria-labelledby", "confirmacao-titulo");
    modal.innerHTML =
      '<div class="modal__icon modal__icon--danger">' + icone("alert") + "</div>" +
      '<h2 id="confirmacao-titulo"></h2>' +
      '<p class="muted" data-texto></p>' +
      '<div class="btn-row btn-row--end">' +
      '<button type="button" class="btn btn--secondary" data-voltar>Voltar</button>' +
      '<button type="button" class="btn btn--danger" data-confirmar></button>' +
      "</div>";
    document.body.appendChild(modal);

    var formularioAtual = null;
    var botaoAtual = null;
    modal.querySelector("[data-voltar]").addEventListener("click", function () {
      modal.close();
    });
    modal.querySelector("[data-confirmar]").addEventListener("click", function () {
      if (formularioAtual) {
        formularioAtual.dataset.confirmado = "1";
        modal.close();
        // requestSubmit mantém o botão clicado (name/value) nos dados enviados.
        if (typeof formularioAtual.requestSubmit === "function") {
          formularioAtual.requestSubmit(botaoAtual || undefined);
        } else {
          formularioAtual.submit();
        }
      }
    });

    formularios.forEach(function (formulario) {
      formulario.addEventListener("submit", function (evento) {
        if (formulario.dataset.confirmado === "1") return;
        evento.preventDefault();
        formularioAtual = formulario;
        botaoAtual = evento.submitter || null;
        modal.querySelector("h2").textContent = formulario.dataset.confirm;
        modal.querySelector("[data-texto]").textContent = formulario.dataset.confirmText || "";
        modal.querySelector("[data-confirmar]").textContent =
          formulario.dataset.confirmButton || "Confirmar";
        modal.showModal();
      });
    });
  }

  /* Seletor visual de horários ---------------------------------------------- */
  /* Transforma <select data-slot-picker> em botões agrupados por data.
   * O <select> continua sendo o campo enviado ao servidor. */
  function iniciarSeletorDeHorarios() {
    document.querySelectorAll("select[data-slot-picker]").forEach(function (select) {
      var opcoes = Array.prototype.filter.call(select.options, function (opcao) {
        return opcao.value;
      });
      if (!opcoes.length) return;

      var grupos = {};
      var ordem = [];
      opcoes.forEach(function (opcao) {
        var partes = opcao.text.split(" às ");
        var dia = partes.length === 2 ? partes[0] : "Horários";
        if (!grupos[dia]) {
          grupos[dia] = [];
          ordem.push(dia);
        }
        grupos[dia].push({ opcao: opcao, hora: partes.length === 2 ? partes[1] : opcao.text });
      });

      var container = document.createElement("div");
      container.className = "slot-picker";
      container.setAttribute("role", "group");
      container.setAttribute("aria-label", "Horários disponíveis");

      var botoes = [];
      ordem.forEach(function (dia) {
        var grupo = document.createElement("div");
        grupo.className = "slot-group";
        var titulo = document.createElement("p");
        titulo.className = "slot-group__title";
        titulo.textContent = dia;
        grupo.appendChild(titulo);
        var lista = document.createElement("div");
        lista.className = "slot-grid";
        grupos[dia].forEach(function (item) {
          var botao = document.createElement("button");
          botao.type = "button";
          botao.className = "slot";
          botao.textContent = item.hora;
          botao.setAttribute("aria-label", item.opcao.text);
          botao.setAttribute("aria-pressed", item.opcao.selected && select.value ? "true" : "false");
          botao.addEventListener("click", function () {
            select.value = item.opcao.value;
            botoes.forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
            botao.setAttribute("aria-pressed", "true");
            select.dispatchEvent(new Event("change", { bubbles: true }));
          });
          botoes.push(botao);
          lista.appendChild(botao);
        });
        grupo.appendChild(lista);
        container.appendChild(grupo);
      });

      select.insertAdjacentElement("afterend", container);
      select.classList.add("sr-only");
      select.setAttribute("tabindex", "-1");
      select.setAttribute("aria-hidden", "true");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    iniciarMenu();
    iniciarAlertas();
    iniciarCamposDeSenha();
    iniciarConfirmacoes();
    iniciarSeletorDeHorarios();
  });
})();
