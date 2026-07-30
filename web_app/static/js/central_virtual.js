(function () {
  "use strict";
  var data, sideData, agents, statusColors, gameData;
  try {
    data = JSON.parse(document.getElementById("cv-data").textContent);
    sideData = window.__cvSp || {};
    agents = data.agents || [];
    statusColors = data.status_colors || {};
    gameData = data.game || {};
  } catch (e) { return; }

  function localDateString(date) {
    var year = date.getFullYear();
    var month = String(date.getMonth() + 1).padStart(2, "0");
    var day = String(date.getDate()).padStart(2, "0");
    return year + "-" + month + "-" + day;
  }

  function gameTarget(level) { return 80 + Math.max(1, level) * 30; }
  function gameRank(level) {
    if (level >= 20) return "LENDARIO";
    if (level >= 12) return "ELITE";
    if (level >= 7) return "MESTRE";
    if (level >= 3) return "ESPECIALISTA";
    return "APRENDIZ";
  }
  function dailyGameXp(status) {
    var values = { ACTIVE: 37, ONLINE: 37, RUNNING: 37, ANALYZING: 34, VALIDATING: 34,
      TESTING: 34, REGION_FOUND: 34, SETUP_FORMING: 34, SEARCHING: 32,
      MONITORING: 31, WAITING: 29, STANDBY: 28, BLOCKED: 30, ERROR: 30, OFFLINE: 24 };
    return values[String(status || "").toUpperCase()] || 28;
  }

  function hydrateGameProgress() {
    if (agents.every(function (agent) { return agent.game; })) return;
    var skills = {
      leon_coordinator: "Coordenacao Estrategica", market_context: "Leitura de Contexto",
      smc_analyst: "Estrutura Institucional", elliott_fibonacci: "Projecao de Cenarios",
      interest_zones: "Mapeamento de Zonas", news_shield: "Protecao Operacional",
      risk_guardian: "Disciplina de Risco", mt5_execution: "Execucao Controlada",
      testing_quality: "Validacao de Aprendizado", code_evolution: "Evolucao de Padroes"
    };
    var state = { agents: {} };
    try { state = JSON.parse(localStorage.getItem("leon-agent-game-v1")) || state; } catch (e) { state = { agents: {} }; }
    if (!state.agents) state.agents = {};
    var today = localDateString(new Date());

    agents.forEach(function (agent) {
      var progress = state.agents[agent.id] || { level: 1, xp: 35, total_xp: 35, evolution_days: 1, last_date: today };
      var elapsed = Math.max(0, Math.floor((new Date(today + "T12:00:00") - new Date(progress.last_date + "T12:00:00")) / 86400000));
      if (elapsed) {
        var award = dailyGameXp(agent.status) * elapsed;
        progress.xp += award;
        progress.total_xp += award;
        progress.evolution_days += elapsed;
        progress.last_date = today;
      }
      while (progress.xp >= gameTarget(progress.level)) {
        progress.xp -= gameTarget(progress.level);
        progress.level += 1;
        progress.leveled_up = true;
      }
      var target = gameTarget(progress.level);
      agent.game = {
        level: progress.level, rank: gameRank(progress.level), skill: skills[agent.id] || "Operacao Geral",
        xp: progress.xp, xp_target: target, xp_percent: Math.round(progress.xp / target * 1000) / 10,
        total_xp: progress.total_xp, evolution_days: progress.evolution_days,
        daily_gain: dailyGameXp(agent.status), leveled_up: !!progress.leveled_up
      };
      progress.leveled_up = false;
      state.agents[agent.id] = progress;
    });
    try { localStorage.setItem("leon-agent-game-v1", JSON.stringify(state)); } catch (e) { /* storage is optional */ }
    var levels = agents.map(function (agent) { return agent.game.level; });
    gameData = {
      central_level: Math.max(1, Math.round(levels.reduce(function (sum, level) { return sum + level; }, 0) / (levels.length || 1))),
      total_xp: agents.reduce(function (sum, agent) { return sum + agent.game.total_xp; }, 0),
      evolution_day: Math.max.apply(Math, agents.map(function (agent) { return agent.game.evolution_days; })),
      agent_count: agents.length
    };
  }

  hydrateGameProgress();

  var agentModes = {
    leon_coordinator: { key: "command", label: "COMANDO", badge: "CMD", speed: .92, dwell: 2600, tripInterval: 17000,
      tasks: ["task-command", "task-thinking"], destinations: ["market_context", "risk_guardian", "code_evolution", "mt5_execution"],
      messages: ["STATUS DA EQUIPE?", "VAMOS ALINHAR A MISSAO", "PRIORIDADE CONFIRMADA"] },
    market_context: { key: "context", label: "LEITURA GLOBAL", badge: "CTX", speed: 1.04, dwell: 1700, tripInterval: 12500,
      tasks: ["task-scan", "task-review"], destinations: ["smc_analyst", "interest_zones", "leon_coordinator"],
      messages: ["CONTEXTO ATUALIZADO", "MERCADO EM OBSERVACAO", "CONFIRME A DIRECAO"] },
    smc_analyst: { key: "structure", label: "ESTRUTURA SMC", badge: "SMC", speed: .98, dwell: 2100, tripInterval: 14500,
      tasks: ["task-review", "task-thinking"], destinations: ["elliott_fibonacci", "market_context", "risk_guardian"],
      messages: ["ESTRUTURA MAPEADA", "CHOCH EM REVISAO", "CONFIRA ESTE BLOCO"] },
    elliott_fibonacci: { key: "scenario", label: "CENARIOS", badge: "FIB", speed: .88, dwell: 2500, tripInterval: 18500,
      tasks: ["task-thinking", "task-scan"], destinations: ["smc_analyst", "risk_guardian", "market_context"],
      messages: ["CENARIO PROJETADO", "ONDAS EM REVISAO", "TENHO DUAS ROTAS"] },
    interest_zones: { key: "zones", label: "MAPEAMENTO", badge: "ZON", speed: 1.08, dwell: 1600, tripInterval: 13200,
      tasks: ["task-scan", "task-review"], destinations: ["market_context", "risk_guardian", "mt5_execution"],
      messages: ["NOVA ZONA MARCADA", "LIQUIDEZ LOCALIZADA", "REGIAO VALIDADA"] },
    news_shield: { key: "shield", label: "PROTECAO", badge: "SHD", speed: 1.16, dwell: 1500, tripInterval: 7800,
      tasks: ["task-alert", "task-scan"], destinations: ["risk_guardian", "leon_coordinator", "mt5_execution"],
      messages: ["ALERTA DE PROTECAO", "RISCO EXTERNO DETECTADO", "PRECISO DE COBERTURA"] },
    risk_guardian: { key: "risk", label: "CONTROLE DE RISCO", badge: "RSK", speed: .82, dwell: 2300, tripInterval: 9800,
      tasks: ["task-review", "task-command"], destinations: ["news_shield", "mt5_execution", "leon_coordinator"],
      messages: ["LIMITE DE RISCO OK", "VAMOS REVISAR A EXPOSICAO", "PROTECAO CONFIRMADA"] },
    mt5_execution: { key: "execution", label: "EXECUCAO", badge: "MT5", speed: 1.24, dwell: 1200, tripInterval: 19000,
      tasks: ["task-execute", "task-review"], destinations: ["risk_guardian", "leon_coordinator", "interest_zones"],
      messages: ["EXECUCAO SINCRONIZADA", "TERMINAL CONFERIDO", "ORDEM SOB CONTROLE"] },
    code_evolution: { key: "evolution", label: "APRENDIZADO", badge: "EVO", speed: .9, dwell: 2200, tripInterval: 7600,
      tasks: ["task-learn", "task-thinking"], destinations: ["testing_quality", "leon_coordinator", "smc_analyst"],
      messages: ["NOVO PADRAO ENCONTRADO", "PRECISO VALIDAR O CODIGO", "APRENDIZADO EM REVISAO"] },
    testing_quality: { key: "testing", label: "LABORATORIO", badge: "LAB", speed: 1.02, dwell: 2400, tripInterval: 10400,
      tasks: ["task-test", "task-review"], destinations: ["code_evolution", "leon_coordinator", "smc_analyst"],
      messages: ["TESTE CONCLUIDO", "FALHA REPRODUZIDA", "VOU VALIDAR A MELHORIA"] }
  };

  function agentMode(id) {
    return agentModes[id] || { key: "general", label: "OPERACAO", badge: "OP", speed: 1,
      dwell: 1800, tripInterval: 15000, tasks: ["task-thinking"], destinations: ["leon_coordinator"],
      messages: ["OPERACAO EM ANDAMENTO"] };
  }

  function agentSprite(id, pose) {
    return "/static/agents/v2/" + String(id || "operator").replace(/_/g, "-") + "-" + pose + ".png";
  }

  function statusClass(s) {
    if (!s) return "status-unknown";
    s = s.toUpperCase();
    if (["ACTIVE","ONLINE","RUNNING"].indexOf(s) >= 0) return "status-active";
    if (["ANALYZING","VALIDATING","TESTING","SEARCHING","REGION_FOUND","SETUP_FORMING","FORMING"].indexOf(s) >= 0) return "status-processing";
    if (["WAITING","MONITORING","STALE","NO_DATA","UNKNOWN"].indexOf(s) >= 0) return "status-waiting";
    if (["BLOCKED","ERROR","OFFLINE"].indexOf(s) >= 0) return "status-blocked";
    return "status-unknown";
  }

  function badgeClass(s) {
    if (!s) return "";
    s = s.toUpperCase();
    if (["ACTIVE","ONLINE","RUNNING"].indexOf(s) >= 0) return "active";
    if (["ANALYZING","VALIDATING","TESTING","FORMING"].indexOf(s) >= 0) return "processing";
    if (["WAITING","MONITORING","STALE","NO_DATA","UNKNOWN"].indexOf(s) >= 0) return "waiting";
    if (["BLOCKED","ERROR","OFFLINE"].indexOf(s) >= 0) return "blocked";
    return "";
  }

  function applyAgents() {
    agents.forEach(function (agent) {
      var el = document.querySelector('[data-agent="' + agent.id + '"]');
      if (!el) return;
      var mode = agentMode(agent.id);
      el.className = "station " + statusClass(agent.status) + " mode-" + mode.key;
      el.setAttribute("data-mode", mode.label);
      var st = el.querySelector(".ws-status");
      if (st) st.textContent = agent.status || "UNKNOWN";
    });
  }

  function g(id) { return document.getElementById(id); }

  function setupGameMode() {
    var room = g("room");
    if (!room) return;
    var hud = document.createElement("section");
    hud.className = "game-hud";
    hud.setAttribute("aria-label", "Progresso da Central Virtual");
    var gameLabel = gameData.legacy_visual_only ? "TELEMETRIA VISUAL LEGADA" : "MODO EVOLUCAO";
    var gameRule = gameData.daily_rule || "Evolucao diaria por aprendizado e seguranca";
    hud.innerHTML = '<div class="game-eyebrow">' + gameLabel + '</div>' +
      '<div class="game-main"><strong>Central NV. ' + (gameData.central_level || 1) + '</strong>' +
      '<span>DIA ' + (gameData.evolution_day || 0) + '</span></div>' +
      '<div class="game-meta"><span>' + (gameData.agent_count || agents.length) + ' agentes</span>' +
      '<span>' + (gameData.total_xp || 0) + ' XP total</span></div>' +
      '<div class="game-rule">' + gameRule + '</div>';
    room.appendChild(hud);

    agents.forEach(function (agent) {
      var station = document.querySelector('[data-agent="' + agent.id + '"]');
      if (!station || !agent.game) return;
      var plate = document.createElement("span");
      plate.className = "agent-nameplate" + (agent.game.leveled_up ? " level-up" : "");
      plate.setAttribute("aria-hidden", "true");
      plate.innerHTML = '<span class="agent-name-row"><b>' + (agent.name || agent.station) + '</b>' +
        '<em>NV.' + agent.game.level + '</em></span>' +
        '<span class="agent-mode-label">' + agentMode(agent.id).label + '</span>' +
        '<span class="agent-rank">' + agent.game.rank + ' · ' + liveStatus(agent.status) + '</span>' +
        '<span class="agent-xp"><i style="width:' + agent.game.xp_percent + '%"></i></span>';
      station.appendChild(plate);
    });
    updateAgentGame(agents.find(function (agent) { return agent.id === "leon_coordinator"; }));
  }

  function updateAgentGame(agent) {
    var body = document.querySelector(".insp-body");
    if (!body || !agent || !agent.game) return;
    var card = g("agent-game-card");
    if (!card) {
      card = document.createElement("section");
      card.id = "agent-game-card";
      card.className = "agent-game-card";
      body.insertBefore(card, body.firstChild);
    }
    var legacyLabel = agent.game.legacy_visual_only ? "TELEMETRIA LEGADA" : "MODO EVOLUCAO";
    var dailyLabel = agent.game.legacy_visual_only ? "CONGELADO" : "+" + agent.game.daily_gain + " XP/dia";
    card.innerHTML = '<div class="agc-top"><span>' + legacyLabel + '</span><b>NV. ' + agent.game.level + '</b></div>' +
      '<div class="agc-rank">' + agent.game.rank + '</div>' +
      '<div class="agc-mode">FUNCAO: ' + agentMode(agent.id).label + '</div>' +
      '<div class="agc-skill">' + agent.game.skill + '</div>' +
      '<div class="agc-bar"><i style="width:' + agent.game.xp_percent + '%"></i></div>' +
      '<div class="agc-meta"><span>' + agent.game.xp + ' / ' + agent.game.xp_target + ' XP</span>' +
      '<span>' + dailyLabel + '</span></div>' +
      '<div class="agc-days">' + agent.game.evolution_days + ' dia(s) de evolucao</div>';
  }

  function updateProcess(id, label, evidence) {
    var el = g(id);
    if (!el) return;
    evidence = evidence || {};
    var state = String(evidence.state || "UNKNOWN").toUpperCase();
    var cssState = state === "ONLINE" ? "on" : (state === "OFFLINE" ? "off" : "unknown");
    el.className = "insp-p " + cssState;
    el.textContent = label + " · " + state;
    el.title = [evidence.reason, evidence.updated_at ? "Fonte: " + evidence.updated_at : ""]
      .filter(Boolean)
      .join(" ");
  }

  function updateCoordinator() {
    var sp = sideData;
    if (g("i-status")) {
      var s = sp.stale_data ? "STALE" : (sp.autonomy_active ? "ACTIVE" : "STANDBY");
      g("i-status").textContent = s;
      g("i-status").className = "insp-badge " + badgeClass(s);
    }
    if (g("i-act")) g("i-act").textContent = sp.autonomy_reason || "Consolidando o contexto dos agentes";
    if (g("i-tf")) g("i-tf").textContent = sp.timeframe || "H4 / H1";
    if (g("i-reg")) g("i-reg").textContent = (sp.region_id || "N/D") + " · " + (sp.region_status || "N/D");
    if (g("i-dir")) g("i-dir").textContent = sp.direction || "N/D";
    if (g("i-str")) g("i-str").textContent = (sp.smc || "N/D") + " / " + (sp.elliott || "N/D");
    if (g("i-conf")) g("i-conf").textContent = sp.confidence || "N/D";
    if (g("i-alig")) g("i-alig").textContent = sp.alignment || "N/D";
    if (g("i-ctx")) g("i-ctx").textContent = sp.context_phase || "N/D";
    if (g("i-ctxd")) g("i-ctxd").textContent = "Tendencia: " + (sp.context_trend || "N/D") + " | Vol: " + (sp.context_volatility || "N/D");
    if (g("i-risk")) g("i-risk").textContent = "Metodo: " + (sp.risk_method || 0) + "% | Diario: " + (sp.risk_daily || 0) + "%";
    if (g("i-sh")) g("i-sh").textContent = sp.shadow_total || 0;
    if (g("i-shd")) g("i-shd").textContent = "W: " + (sp.shadow_wins || 0) + " | L: " + (sp.shadow_losses || 0) + " | Abertos: " + (sp.shadow_open || 0);
    if (g("i-lab")) g("i-lab").textContent = sp.lab_learning ? "ATIVO" : "INATIVO";
    if (g("i-labd")) g("i-labd").textContent = sp.lab_learning ? "Modo estudos LAB_LEARNING ativo" : "Modo estudos inativo";
    if (g("i-pre")) g("i-pre").textContent = "Total: " + (sp.pre_op_total || 0) + " | Fechadas: " + (sp.pre_op_closed || 0);
    if (g("i-cycle")) g("i-cycle").textContent = sp.cycle_id || "N/D";
    if (g("i-analysis")) g("i-analysis").textContent = sp.analysis_id || "N/D";
    if (g("i-region-id")) g("i-region-id").textContent = sp.region_id || "N/D";
    if (g("i-preop-id")) g("i-preop-id").textContent = sp.pre_operation_id || "N/D";
    if (g("i-err")) g("i-err").textContent = sp.error_count || 0;
    if (g("i-conc")) g("i-conc").textContent = sp.context_phase || "N/D";
    if (g("i-next")) g("i-next").textContent = sp.next_action || "Aguardar validacao estrutural";
    if (g("i-time")) g("i-time").textContent = sp.generated_at || "Agora";
    if (g("i-source-time")) g("i-source-time").textContent = "Fonte: " + (sp.source_updated_at || "N/D");
    var procs = sp.processes || {};
    updateProcess("p-op", "Operador", procs.operator);
    updateProcess("p-web", "Web", procs.web);
    updateProcess("p-tun", "Tunel", procs.tunnel);
    updateProcess("p-mt5", "MT5", procs.mt5);
  }

  function liveStatus(status) {
    var labels = {
      ACTIVE: "OPERANDO",
      ONLINE: "ONLINE",
      RUNNING: "EM EXECUCAO",
      ANALYZING: "ANALISANDO",
      VALIDATING: "VALIDANDO",
      TESTING: "TESTANDO",
      SEARCHING: "BUSCANDO",
      REGION_FOUND: "REGIAO MAPEADA",
      SETUP_FORMING: "MONTANDO CENARIO",
      FORMING: "MONTANDO CENARIO",
      WAITING: "AGUARDANDO",
      MONITORING: "MONITORANDO",
      STALE: "DADOS ANTIGOS",
      NO_DATA: "SEM DADOS",
      UNKNOWN: "DESCONHECIDO",
      BLOCKED: "BLOQUEADO",
      ERROR: "ATENCAO",
      OFFLINE: "OFFLINE"
    };
    return labels[String(status || "").toUpperCase()] || "OBSERVANDO";
  }

  function addDeskAgent(station, id) {
    var palettes = {
      leon_coordinator: ["#f0c850", "#8f6a16"],
      market_context: ["#00d4f0", "#087285"],
      smc_analyst: ["#e2b94b", "#7c5f18"],
      elliott_fibonacci: ["#a070f0", "#5e3e9f"],
      interest_zones: ["#22c9e6", "#086b7a"],
      news_shield: ["#ff5a6e", "#9b2537"],
      risk_guardian: ["#f0c850", "#8f6a16"],
      mt5_execution: ["#8d9aa7", "#45515d"],
      code_evolution: ["#ff7a62", "#9b3d2e"],
      testing_quality: ["#40e8a0", "#147b50"]
    };
    var mode = agentMode(id);
    var palette = palettes[id] || ["#00d4f0", "#087285"];
    var desk = document.createElement("span");
    desk.className = "desk-agent desk-mode-" + mode.key;
    desk.setAttribute("aria-hidden", "true");
    desk.style.setProperty("--desk-color", palette[0]);
    desk.style.setProperty("--desk-dark", palette[1]);
    desk.innerHTML = '<span class="desk-screen-glow"></span><span class="desk-shadow"></span>' +
      '<span class="agent-role-light"></span>' +
      '<span class="agent-role-badge">' + mode.badge + '</span>' +
      '<img class="desk-agent-sprite" src="' + agentSprite(id, "seated") + '" alt="">';
    station.appendChild(desk);
  }

  function deskActivity(agent) {
    var status = String(agent.status || "").toUpperCase();
    if (["ERROR", "BLOCKED", "OFFLINE"].indexOf(status) >= 0) return liveStatus(status);
    var activities = {
      leon_coordinator: "COORDENANDO A EQUIPE",
      market_context: "OBSERVANDO O MERCADO",
      smc_analyst: "LENDO A ESTRUTURA",
      elliott_fibonacci: "SIMULANDO CENARIOS",
      interest_zones: "MAPEANDO ZONAS",
      news_shield: "VIGIANDO NOTICIAS",
      risk_guardian: "CALCULANDO RISCO",
      mt5_execution: "MONITORANDO EXECUCAO",
      code_evolution: "APRENDENDO PADROES",
      testing_quality: "VALIDANDO APRENDIZADO"
    };
    return activities[agent.id] || liveStatus(status);
  }

  function setupLiveliness() {
    stations.forEach(function (station) {
      var id = station.getAttribute("data-agent");
      var agent = agents.find(function (item) { return item.id === id; }) || {};
      addDeskAgent(station, id);
      var spark = document.createElement("span");
      spark.className = "agent-spark";
      spark.setAttribute("aria-hidden", "true");
      var pop = document.createElement("span");
      pop.className = "activity-pop";
      pop.setAttribute("aria-hidden", "true");
      pop.textContent = deskActivity(agent);
      station.appendChild(spark);
      station.appendChild(pop);
    });

    var room = g("room");
    if (room && !room.querySelector(".core-energy")) {
      var energy = document.createElement("div");
      energy.className = "core-energy";
      energy.setAttribute("aria-hidden", "true");
      var caption = document.createElement("span");
      caption.className = "core-caption";
      caption.textContent = sideData.autonomy_active ? "NUCLEO ATIVO" : "NUCLEO EM OBSERVACAO";
      energy.appendChild(caption);
      room.appendChild(energy);
    }

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var liveStations = Array.prototype.slice.call(stations);
    var liveIndex = 0;
    window.setInterval(function () {
      liveStations.forEach(function (station) { station.classList.remove("is-speaking"); });
      if (!liveStations.length || document.hidden) return;
      var station = liveStations[liveIndex % liveStations.length];
      liveIndex += 1;
      station.classList.add("is-speaking");
      window.setTimeout(function () { station.classList.remove("is-speaking"); }, 1300);
    }, 2300);

    liveStations.forEach(function (station, index) {
      var stationMode = agentMode(station.getAttribute("data-agent"));
      var taskCursor = 0;
      window.setInterval(function () {
        if (document.hidden || station.classList.contains("agent-away")) return;
        var task = stationMode.tasks[taskCursor % stationMode.tasks.length];
        taskCursor += 1;
        station.classList.add(task);
        window.setTimeout(function () { station.classList.remove(task); }, 1400);
      }, 5000 + index * 190);
    });
  }

  function setupRoomLife() {
    var room = g("room");
    if (!room || room.querySelector(".data-network")) return;
    var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var points = {
      leon_coordinator: [50, 12], market_context: [26, 34], smc_analyst: [40, 34],
      elliott_fibonacci: [69, 33], interest_zones: [19.5, 51], news_shield: [29.5, 68],
      risk_guardian: [47, 64], mt5_execution: [77, 52], code_evolution: [61, 75],
      testing_quality: [40, 82]
    };
    var svgNs = "http://www.w3.org/2000/svg";
    var network = document.createElementNS(svgNs, "svg");
    network.setAttribute("class", "data-network");
    network.setAttribute("viewBox", "0 0 100 100");
    network.setAttribute("preserveAspectRatio", "none");
    network.setAttribute("aria-hidden", "true");

    agents.forEach(function (agent, index) {
      var point = points[agent.id];
      if (!point) return;
      var path = document.createElementNS(svgNs, "path");
      var curve = 48 + ((index % 3) - 1) * 6;
      var d = "M " + point[0] + " " + point[1] + " Q " + curve + " 48 50 50";
      path.setAttribute("d", d);
      path.setAttribute("class", "data-link " + statusClass(agent.status));
      network.appendChild(path);
      if (!reducedMotion) {
        var packet = document.createElementNS(svgNs, "circle");
        packet.setAttribute("r", index % 2 ? ".32" : ".42");
        packet.setAttribute("class", "data-packet " + statusClass(agent.status));
        var motion = document.createElementNS(svgNs, "animateMotion");
        motion.setAttribute("path", d);
        motion.setAttribute("dur", (3.8 + (index % 4) * .7) + "s");
        motion.setAttribute("begin", (-index * .43) + "s");
        motion.setAttribute("repeatCount", "indefinite");
        packet.appendChild(motion);
        network.appendChild(packet);
      }
    });
    room.appendChild(network);

    stations.forEach(function (station, index) {
      var fx = document.createElement("span");
      fx.className = "computer-fx";
      fx.setAttribute("aria-hidden", "true");
      fx.style.setProperty("--screen-delay", (-index * .37) + "s");
      fx.innerHTML = '<span class="computer-scan"></span><span class="computer-led"></span>';
      station.appendChild(fx);
    });

    var ambient = document.createElement("div");
    ambient.className = "room-ambient";
    ambient.setAttribute("aria-hidden", "true");
    for (var i = 0; i < 18; i += 1) {
      var mote = document.createElement("i");
      mote.style.setProperty("--mx", (8 + (i * 29) % 84) + "%");
      mote.style.setProperty("--my", (12 + (i * 47) % 78) + "%");
      mote.style.setProperty("--md", (4.2 + (i % 6) * .8) + "s");
      mote.style.setProperty("--ml", (-i * .51) + "s");
      ambient.appendChild(mote);
    }
    room.appendChild(ambient);

    var sceneLife = document.createElement("div");
    sceneLife.className = "scene-life";
    sceneLife.setAttribute("aria-hidden", "true");
    sceneLife.innerHTML = '<span class="holo-sweep"></span>' +
      '<span class="holo-power-wave"></span>' +
      '<span class="map-sweep"></span>' +
      '<span class="server-life server-life-left"></span>' +
      '<span class="server-life server-life-right"></span>' +
      '<span class="maintenance-bot"><i></i><b></b><em></em></span>' +
      '<span class="holo-announcement">SALA SINCRONIZADA</span>';
    var floorSignals = [[50,32],[61,40],[66,52],[60,63],[50,68],[39,63],[34,52],[39,41]];
    floorSignals.forEach(function (point, index) {
      var signal = document.createElement("i");
      signal.className = "floor-signal";
      signal.style.left = point[0] + "%";
      signal.style.top = point[1] + "%";
      signal.style.setProperty("--signal-delay", (-index * .24) + "s");
      sceneLife.appendChild(signal);
    });

    [[29,10],[45,8],[62,9],[82,27],[91,43],[12,71]].forEach(function (point, index) {
      var light = document.createElement("i");
      light.className = "room-light";
      light.style.left = point[0] + "%";
      light.style.top = point[1] + "%";
      light.style.setProperty("--light-delay", (-index * .63) + "s");
      sceneLife.appendChild(light);
    });

    [[13,34,0],[31,29,1],[72,30,2],[81,49,3],[36,76,4]].forEach(function (point) {
      var screen = document.createElement("span");
      screen.className = "scene-monitor";
      screen.style.left = point[0] + "%";
      screen.style.top = point[1] + "%";
      screen.style.setProperty("--monitor-delay", (-point[2] * .71) + "s");
      screen.innerHTML = '<i></i><i></i><i></i>';
      sceneLife.appendChild(screen);
    });
    room.appendChild(sceneLife);

    if (!reducedMotion) {
      var announcement = sceneLife.querySelector(".holo-announcement");
      var roomMessages = ["SALA SINCRONIZADA", "DADOS EM MOVIMENTO", "NUCLEO ESTAVEL", "ENERGIA NORMAL", "SISTEMAS ONLINE"];
      var messageIndex = 0;
      window.setInterval(function () {
        if (document.hidden) return;
        messageIndex = (messageIndex + 1) % roomMessages.length;
        announcement.textContent = roomMessages[messageIndex];
        announcement.classList.add("visible");
        window.setTimeout(function () { announcement.classList.remove("visible"); }, 1800);
      }, 6200);
    }
  }

  function setupRoamingAgents() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var room = g("room");
    if (!room) return;

    var points = {
      leon_coordinator: { x: 50, y: 12 },
      market_context: { x: 26, y: 34 },
      smc_analyst: { x: 40, y: 34 },
      elliott_fibonacci: { x: 69, y: 33 },
      interest_zones: { x: 19.5, y: 51 },
      news_shield: { x: 29.5, y: 68 },
      risk_guardian: { x: 47, y: 64 },
      mt5_execution: { x: 77, y: 52 },
      code_evolution: { x: 61, y: 75 },
      testing_quality: { x: 40, y: 82 }
    };

    /* A walkable ring keeps every trip on the visible floor instead of crossing desks. */
    var floorRing = [
      { x: 50, y: 32 }, { x: 61, y: 40 }, { x: 66, y: 52 }, { x: 60, y: 63 },
      { x: 50, y: 68 }, { x: 39, y: 63 }, { x: 34, y: 52 }, { x: 39, y: 41 }
    ];
    var gates = {
      leon_coordinator: { point: { x: 50, y: 28 }, ring: 0 },
      market_context: { point: { x: 33, y: 40 }, ring: 7 },
      smc_analyst: { point: { x: 42, y: 40 }, ring: 7 },
      elliott_fibonacci: { point: { x: 63, y: 40 }, ring: 1 },
      interest_zones: { point: { x: 30, y: 52 }, ring: 6 },
      news_shield: { point: { x: 36, y: 65 }, ring: 5 },
      risk_guardian: { point: { x: 48, y: 68 }, ring: 4 },
      mt5_execution: { point: { x: 68, y: 53 }, ring: 2 },
      code_evolution: { point: { x: 60, y: 68 }, ring: 3 },
      testing_quality: { point: { x: 43, y: 74 }, ring: 4 }
    };

    var palettes = {
      leon_coordinator: ["#f0c850", "#8f6a16"], market_context: ["#00d4f0", "#087285"],
      smc_analyst: ["#e2b94b", "#7c5f18"], elliott_fibonacci: ["#a070f0", "#5e3e9f"],
      interest_zones: ["#22c9e6", "#086b7a"], news_shield: ["#ff5a6e", "#9b2537"],
      risk_guardian: ["#f0c850", "#8f6a16"], mt5_execution: ["#8d9aa7", "#45515d"],
      code_evolution: ["#ff7a62", "#9b3d2e"], testing_quality: ["#40e8a0", "#147b50"]
    };
    var relationCursor = {};
    var travelers = 0;
    var maxTravelers = 2;
    var schedulerCursor = 0;

    function createRunner(agent) {
      var mode = agentMode(agent.id);
      var palette = palettes[agent.id] || ["#00d4f0", "#087285"];
      var runner = document.createElement("div");
      runner.className = "roaming-agent at-home runner-mode-" + mode.key;
      runner.setAttribute("aria-hidden", "true");
      runner.style.setProperty("--runner-color", palette[0]);
      runner.style.setProperty("--runner-dark", palette[1]);
      runner.innerHTML = '<span class="runner-shadow"></span>' +
        '<span class="runner-role-light"></span>' +
        '<span class="runner-role-badge">' + mode.badge + '</span>' +
        '<img class="runner-agent-sprite" src="' + agentSprite(agent.id, "standing") + '" alt="">' +
        '<span class="runner-bubble"></span>';
      var home = points[agent.id];
      runner.style.left = home.x + "%";
      runner.style.top = home.y + "%";
      runner.style.zIndex = String(30 + Math.round(home.y));
      room.appendChild(runner);
      window.requestAnimationFrame(function () { runner.classList.add("ready"); });
      return runner;
    }

    function samePoint(a, b) {
      return a && b && Math.abs(a.x - b.x) < .1 && Math.abs(a.y - b.y) < .1;
    }

    function ringRoute(fromIndex, toIndex) {
      if (fromIndex === toIndex) return [floorRing[fromIndex]];
      var clockwise = [];
      var counter = [];
      var i = fromIndex;
      while (i !== toIndex) { i = (i + 1) % floorRing.length; clockwise.push(floorRing[i]); }
      i = fromIndex;
      while (i !== toIndex) { i = (i - 1 + floorRing.length) % floorRing.length; counter.push(floorRing[i]); }
      return clockwise.length <= counter.length ? clockwise : counter;
    }

    function buildFloorRoute(fromId, destinationId) {
      var fromGate = gates[fromId];
      var toGate = gates[destinationId];
      if (!fromGate || !toGate) return [points[fromId], points[destinationId]];
      var route = [points[fromId], fromGate.point, floorRing[fromGate.ring]]
        .concat(ringRoute(fromGate.ring, toGate.ring))
        .concat([toGate.point]);
      return route.filter(function (point, index) { return !index || !samePoint(point, route[index - 1]); });
    }

    function moveSegment(runner, from, to, speed, done) {
      var dx = (to.x - from.x) * room.clientWidth / 100;
      var dy = (to.y - from.y) * room.clientHeight / 100;
      var duration = Math.max(520, Math.min(1850, Math.sqrt(dx * dx + dy * dy) * 3.1 / speed));
      runner.style.setProperty("--travel", Math.round(duration) + "ms");
      runner.classList.remove("talking");
      runner.classList.toggle("face-left", to.x < from.x);
      runner.classList.add("moving");
      runner.style.zIndex = String(30 + Math.round(to.y));
      runner.style.left = to.x + "%";
      runner.style.top = to.y + "%";
      window.setTimeout(function () {
        runner.classList.remove("moving");
        done();
      }, duration);
    }

    function walkRoute(runner, route, speed, done) {
      var step = 0;
      function next() {
        if (step >= route.length - 1) { done(); return; }
        var from = route[step];
        var to = route[step + 1];
        step += 1;
        moveSegment(runner, from, to, speed, next);
      }
      next();
    }

    function chooseDestination(agent) {
      var status = String(agent.status || "").toUpperCase();
      if (status === "ERROR" || status === "BLOCKED") {
        if (agent.id === "code_evolution") return "testing_quality";
        if (agent.id === "testing_quality") return "leon_coordinator";
        return agent.id === "news_shield" ? "leon_coordinator" : "news_shield";
      }
      var options = agentMode(agent.id).destinations;
      var cursor = relationCursor[agent.id] || 0;
      relationCursor[agent.id] = cursor + 1;
      return options[cursor % options.length];
    }

    function dispatch(config) {
      var destinationId = chooseDestination(config.agent);
      var from = points[config.agent.id];
      var to = points[destinationId];
      var homeStation = document.querySelector('[data-agent="' + config.agent.id + '"]');
      var receiver = document.querySelector('[data-agent="' + destinationId + '"]');
      if (!from || !to || !homeStation || config.busy) return;

      config.busy = true;
      travelers += 1;
      homeStation.classList.add("agent-away");
      config.runner.style.left = from.x + "%";
      config.runner.style.top = from.y + "%";
      config.runner.classList.remove("at-home");

      var mode = agentMode(config.agent.id);
      var speed = mode.speed;
      var outboundRoute = buildFloorRoute(config.agent.id, destinationId);
      walkRoute(config.runner, outboundRoute, speed, function () {
        config.runner.querySelector(".runner-bubble").textContent = mode.messages[config.messageCursor % mode.messages.length];
        config.messageCursor += 1;
        config.runner.classList.add("talking");
          if (receiver) {
            receiver.classList.add("receiving", "is-speaking");
          window.setTimeout(function () { receiver.classList.remove("receiving", "is-speaking"); }, 1450);
          }

        window.setTimeout(function () {
          config.runner.classList.remove("talking");
          walkRoute(config.runner, outboundRoute.slice().reverse(), speed, function () {
            config.runner.classList.add("at-home");
            homeStation.classList.remove("agent-away");
            homeStation.classList.add("receiving");
            window.setTimeout(function () { homeStation.classList.remove("receiving"); }, 850);
            config.busy = false;
            travelers -= 1;
          });
        }, mode.dwell);
      });
    }

    var configs = agents.filter(function (agent) {
      return points[agent.id] && String(agent.status || "").toUpperCase() !== "OFFLINE";
    }).map(function (agent) {
      var mode = agentMode(agent.id);
      return { agent: agent, runner: createRunner(agent), busy: false, messageCursor: 0,
        nextTrip: Date.now() + 1800 + Math.random() * mode.tripInterval };
    });

    function scheduleLife() {
      if (document.hidden || travelers >= maxTravelers || !configs.length) return;
      for (var attempt = 0; attempt < configs.length; attempt += 1) {
        var config = configs[schedulerCursor % configs.length];
        schedulerCursor += 1;
        if (!config.busy && Date.now() >= config.nextTrip) {
          config.nextTrip = Date.now() + agentMode(config.agent.id).tripInterval;
          dispatch(config);
          break;
        }
      }
    }

    window.setTimeout(scheduleLife, 1200);
    window.setInterval(scheduleLife, 1200);
  }

  function showAgent(agent) {
    if (g("i-title")) g("i-title").textContent = agent.name;
    if (g("i-sub")) g("i-sub").textContent = agentMode(agent.id).label + " - " + (agent.activity || agent.station || "N/D");
    if (g("i-status")) {
      g("i-status").textContent = agent.status || "UNKNOWN";
      g("i-status").className = "insp-badge " + badgeClass(agent.status);
    }
    if (g("i-reg")) g("i-reg").textContent = agent.region || "XAUUSD";
    if (g("i-act")) g("i-act").textContent = agent.activity || "N/D";
    updateAgentGame(agent);
    g("btn-back").style.display = "block";
    if (window.matchMedia("(max-width: 900px)").matches) {
      g("inspector").classList.add("open");
    }
  }

  function showCoordinator() {
    g("btn-back").style.display = "none";
    g("inspector").classList.remove("open");
    if (g("i-title")) g("i-title").textContent = "LEON Coordenador";
    if (g("i-sub")) g("i-sub").textContent = "Coordenacao da Central Operacional";
    updateCoordinator();
    updateAgentGame(agents.find(function (agent) { return agent.id === "leon_coordinator"; }));
  }

  var stations = document.querySelectorAll(".station");
  stations.forEach(function (st) {
    st.addEventListener("click", function () {
      stations.forEach(function (s) { s.classList.remove("selected"); });
      st.classList.add("selected");
      var id = st.getAttribute("data-agent");
      var agent = agents.find(function (a) { return a.id === id; });
      if (agent) showAgent(agent);
    });
  });

  g("btn-back").addEventListener("click", function () {
    stations.forEach(function (s) { s.classList.remove("selected"); });
    showCoordinator();
  });

  var tip = document.createElement("div");
  tip.className = "tip";
  document.body.appendChild(tip);

  stations.forEach(function (st) {
    st.addEventListener("mouseenter", function () {
      var id = st.getAttribute("data-agent");
      var agent = agents.find(function (a) { return a.id === id; });
      if (!agent) return;
      tip.innerHTML = '<b>' + (agent.name || agent.station) + '</b><small style="color:' + (statusColors[agent.status] || '#858d99') + '">' + (agent.status || 'UNKNOWN') + '</small>' +
        (agent.game ? '<span class="tip-game">NV. ' + agent.game.level + ' · ' + agent.game.rank + '<br>' + agent.game.skill + '</span>' : '');
      tip.classList.add("vis");
    });
    st.addEventListener("mousemove", function (e) {
      tip.style.left = (e.clientX + 12) + "px";
      tip.style.top = (e.clientY + 12) + "px";
    });
    st.addEventListener("mouseleave", function () { tip.classList.remove("vis"); });
  });

  g("btn-center").addEventListener("click", function () {
    stations.forEach(function (s) { s.classList.remove("selected"); });
    showCoordinator();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !document.fullscreenElement) {
      stations.forEach(function (s) { s.classList.remove("selected"); });
      showCoordinator();
    }
  });

  g("btn-fs").addEventListener("click", function () {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen();
  });

  applyAgents();
  updateCoordinator();
  setupGameMode();
  setupRoomLife();
  setupLiveliness();
  setupRoamingAgents();
})();
