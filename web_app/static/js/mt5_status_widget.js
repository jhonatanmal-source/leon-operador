(function () {
  "use strict";

  // Widget de status MT5 no sidebar (Fase C — MISSION-20260825-WEB-RPYC-TIMEOUT).
  //
  // O sidebar e renderizado em TODA pagina via context_processor
  // (inject_current_user -> get_mt5_account_summary). Esse valor inicial
  // ja vem protegido por cache stale-while-revalidate (Fase A+B), mas o
  // objetivo desta fase e tirar a atualizacao periodica do caminho de
  // render do template: o JS faz polling num endpoint proprio
  // (/health/mt5-status), fora do critical path de qualquer pagina.
  //
  // Pausa o polling quando a aba fica oculta (visibilitychange) para nao
  // gastar recursos/chamadas desnecessarias em background.

  var POLL_INTERVAL_MS = 30000; // mesmo TTL do cache do backend (30s)
  var timerId = null;

  function updateSidebar(data) {
    if (!data || typeof data !== "object") return;

    var badge = document.querySelector("[data-mt5-badge]");
    var accountEl = document.querySelector("[data-mt5-account]");
    var serverEl = document.querySelector("[data-mt5-server]");
    var typeEl = document.querySelector("[data-mt5-type]");

    if (badge) {
      var connected = !!data.connected;
      badge.classList.toggle("g", connected);
      badge.classList.toggle("r", !connected);
      badge.textContent = connected ? "Conectado" : "Offline";
    }
    if (accountEl && data.account) accountEl.textContent = data.account;
    if (serverEl && data.server) serverEl.textContent = data.server;
    if (typeEl && data.type) typeEl.textContent = data.type;
  }

  function poll() {
    fetch("/health/mt5-status", { credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) return null;
        return response.json();
      })
      .then(updateSidebar)
      .catch(function () {
        // Falha de rede/timeout no fetch: mantem o valor atual exibido,
        // nao degrada a pagina. O backend ja cuida do fallback via cache.
      });
  }

  function startPolling() {
    if (timerId) return;
    poll();
    timerId = window.setInterval(poll, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (!timerId) return;
    window.clearInterval(timerId);
    timerId = null;
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      stopPolling();
    } else {
      startPolling();
    }
  });

  if (!document.hidden) {
    startPolling();
  }
})();
