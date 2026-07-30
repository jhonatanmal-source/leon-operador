(function () {
  "use strict";

  var data = JSON.parse(document.getElementById("virtual-operations-data").textContent);
  var sideData = window.__virtualSidePanel || {};

  var container = document.getElementById("canvas-wrap");
  var overlay = document.getElementById("loading-overlay");
  var btnCenter = document.getElementById("center-btn");

  var W = container.clientWidth || window.innerWidth;
  var H = container.clientHeight || window.innerHeight;

  // ── RENDERER ──
  var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(W, H);
  renderer.setClearColor(0x070b14, 1);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  // ── CSS2D ──
  var labelRenderer = new THREE.CSS2DRenderer();
  labelRenderer.setSize(W, H);
  labelRenderer.domElement.style.position = "absolute";
  labelRenderer.domElement.style.top = "0";
  labelRenderer.domElement.style.left = "0";
  labelRenderer.domElement.style.pointerEvents = "none";
  container.appendChild(labelRenderer.domElement);

  // ── SCENE ──
  var scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x070b14, 0.025);

  // ── CAMERA ──
  var camera = new THREE.PerspectiveCamera(40, W / H, 0.1, 200);
  camera.position.set(14, 14, 14);
  camera.lookAt(0, 0, 0);

  // ── CONTROLS ──
  var controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(0, 0, 0);
  controls.maxPolarAngle = Math.PI / 2.1;
  controls.minDistance = 8;
  controls.maxDistance = 40;
  controls.enablePan = true;
  controls.update();

  // ── LIGHTS ──
  var ambLight = new THREE.AmbientLight(0x1a2035, 0.6);
  scene.add(ambLight);

  var dirLight = new THREE.DirectionalLight(0xd7b24b, 0.5);
  dirLight.position.set(10, 15, 8);
  dirLight.castShadow = true;
  dirLight.shadow.mapSize.set(2048, 2048);
  dirLight.shadow.camera.left = -20;
  dirLight.shadow.camera.right = 20;
  dirLight.shadow.camera.top = 20;
  dirLight.shadow.camera.bottom = -20;
  scene.add(dirLight);

  var hubLight = new THREE.PointLight(0x22d3ee, 1.2, 20);
  hubLight.position.set(0, 4, 0);
  scene.add(hubLight);

  var goldLight = new THREE.PointLight(0xd7b24b, 0.6, 15);
  goldLight.position.set(0, 2, -5.8);
  scene.add(goldLight);

  // ── MATERIALS ──
  var floorMat = new THREE.MeshStandardMaterial({
    color: 0x0d1117,
    roughness: 0.9,
    metalness: 0.1,
  });

  var deskMat = new THREE.MeshStandardMaterial({
    color: 0x141922,
    roughness: 0.6,
    metalness: 0.3,
  });

  var screenMat = new THREE.MeshStandardMaterial({
    color: 0x111827,
    emissive: 0x0a1628,
    emissiveIntensity: 0.5,
    roughness: 0.3,
    metalness: 0.5,
  });

  var wallMat = new THREE.MeshStandardMaterial({
    color: 0x0f1520,
    roughness: 0.8,
    metalness: 0.2,
  });

  // ── FLOOR ──
  var floorGeo = new THREE.PlaneGeometry(50, 50);
  var floor = new THREE.Mesh(floorGeo, floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.01;
  floor.receiveShadow = true;
  scene.add(floor);

  // Grid lines
  var gridHelper = new THREE.GridHelper(50, 50, 0x1a2540, 0x111a2a);
  gridHelper.position.y = 0.01;
  scene.add(gridHelper);

  // ── WALLS ──
  function addWall(x, z, rotY, w) {
    var geo = new THREE.BoxGeometry(w || 20, 5, 0.3);
    var wall = new THREE.Mesh(geo, wallMat);
    wall.position.set(x, 2.5, z);
    wall.rotation.y = rotY || 0;
    wall.receiveShadow = true;
    scene.add(wall);
    return wall;
  }

  addWall(0, -10, 0);
  addWall(0, 10, 0);
  addWall(-10, 0, Math.PI / 2);
  addWall(10, 0, Math.PI / 2);

  // Wall screen decorations
  function addWallScreen(x, y, z, rotY, color) {
    var geo = new THREE.PlaneGeometry(3, 2);
    var mat = new THREE.MeshStandardMaterial({
      color: color || 0x0a1628,
      emissive: color || 0x0a1628,
      emissiveIntensity: 0.8,
    });
    var mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(x, y, z);
    mesh.rotation.y = rotY || 0;
    scene.add(mesh);
  }

  addWallScreen(-5, 3, -9.8, 0, 0x0a1e3a);
  addWallScreen(0, 3, -9.8, 0, 0x0a1e3a);
  addWallScreen(5, 3, -9.8, 0, 0x0a1e3a);
  addWallScreen(-9.8, 3, -4, Math.PI / 2, 0x0a1e3a);
  addWallScreen(-9.8, 3, 4, Math.PI / 2, 0x1a0a2a);

  // ── CENTRAL HUB ──
  var hubGeo = new THREE.CylinderGeometry(1.8, 2.2, 1.5, 6);
  var hubMat = new THREE.MeshStandardMaterial({
    color: 0x1a2540,
    emissive: 0xd7b24b,
    emissiveIntensity: 0.15,
    roughness: 0.4,
    metalness: 0.6,
  });
  var hub = new THREE.Mesh(hubGeo, hubMat);
  hub.position.set(0, 0.75, 0);
  hub.castShadow = true;
  scene.add(hub);

  // Hub ring
  var ringGeo = new THREE.TorusGeometry(2.2, 0.08, 8, 32);
  var ringMat = new THREE.MeshStandardMaterial({
    color: 0xd7b24b,
    emissive: 0xd7b24b,
    emissiveIntensity: 0.6,
    roughness: 0.2,
    metalness: 0.8,
  });
  var ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 1.55;
  scene.add(ring);

  // Hologram pillar
  var holoGeo = new THREE.CylinderGeometry(0.3, 0.6, 3, 16, 1, true);
  var holoMat = new THREE.MeshStandardMaterial({
    color: 0x22d3ee,
    emissive: 0x22d3ee,
    emissiveIntensity: 1.0,
    transparent: true,
    opacity: 0.2,
    side: THREE.DoubleSide,
  });
  var holo = new THREE.Mesh(holoGeo, holoMat);
  holo.position.set(0, 3, 0);
  scene.add(holo);

  // Hub label
  var hubDiv = document.createElement("div");
  hubDiv.className = "hub-label";
  hubDiv.innerHTML = '<div class="title">LEON</div><div class="subtitle">OPERATIONAL CORE</div>';
  var hubLabel = new THREE.CSS2DObject(hubDiv);
  hubLabel.position.set(0, 1.8, 0);
  scene.add(hubLabel);

  // ── AGENTS ──
  var statusColors = data.status_colors || {};
  var agents = data.agents || [];

  agents.forEach(function (agent) {
    var pos = agent.scene_position || [0, 0, 0];
    var col = agent.color || 0xd7b24b;
    var status = agent.status || "OFFLINE";
    var statusColor = statusColors[status] || "#6b7280";

    // Desk
    var deskGeo = new THREE.BoxGeometry(1.6, 0.6, 1.0);
    var desk = new THREE.Mesh(deskGeo, deskMat);
    desk.position.set(pos[0], 0.3, pos[2]);
    desk.castShadow = true;
    desk.receiveShadow = true;
    scene.add(desk);

    // Screen
    var scrGeo = new THREE.PlaneGeometry(1.2, 0.8);
    var scrMat = new THREE.MeshStandardMaterial({
      color: 0x111827,
      emissive: col,
      emissiveIntensity: 0.3,
      roughness: 0.3,
    });
    var scr = new THREE.Mesh(scrGeo, scrMat);
    scr.position.set(pos[0], 1.2, pos[2] - 0.3);
    scr.rotation.x = -0.1;
    scene.add(scr);

    // Chair (small cylinder)
    var chairGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.5, 8);
    var chairMat = new THREE.MeshStandardMaterial({ color: 0x1a1a2e, roughness: 0.7 });
    var chair = new THREE.Mesh(chairGeo, chairMat);
    chair.position.set(pos[0], 0.25, pos[2] + 0.8);
    scene.add(chair);

    // Agent glow
    var glowGeo = new THREE.SphereGeometry(0.15, 16, 16);
    var glowMat = new THREE.MeshStandardMaterial({
      color: col,
      emissive: col,
      emissiveIntensity: 1.5,
      transparent: true,
      opacity: 0.8,
    });
    var glow = new THREE.Mesh(glowGeo, glowMat);
    glow.position.set(pos[0], 1.0, pos[2]);
    scene.add(glow);

    // Light per agent
    var agentLight = new THREE.PointLight(col, 0.3, 5);
    agentLight.position.set(pos[0], 2, pos[2]);
    scene.add(agentLight);

    // Label
    var labelDiv = document.createElement("div");
    labelDiv.className = "agent-label";
    labelDiv.innerHTML =
      '<div class="name">' + (agent.name || agent.station) + '</div>' +
      '<div class="status" style="color:' + statusColor + '">' + status + '</div>';
    var label = new THREE.CSS2DObject(labelDiv);
    var off = agent.label_offset || [0, 2, 0];
    label.position.set(pos[0] + off[0], pos[1] + off[1], pos[2] + off[2]);
    scene.add(label);
  });

  // ── PLANTS (decorative) ──
  function addPlant(x, z) {
    var potGeo = new THREE.CylinderGeometry(0.25, 0.2, 0.4, 8);
    var potMat = new THREE.MeshStandardMaterial({ color: 0x2a1a0a, roughness: 0.9 });
    var pot = new THREE.Mesh(potGeo, potMat);
    pot.position.set(x, 0.2, z);
    scene.add(pot);

    var leafGeo = new THREE.SphereGeometry(0.4, 8, 8);
    var leafMat = new THREE.MeshStandardMaterial({ color: 0x1a5a2a, roughness: 0.8 });
    var leaf = new THREE.Mesh(leafGeo, leafMat);
    leaf.position.set(x, 0.7, z);
    scene.add(leaf);
  }

  addPlant(-8.5, -8.5);
  addPlant(8.5, -8.5);
  addPlant(-8.5, 8.5);
  addPlant(8.5, 8.5);
  addPlant(-4, -8.5);
  addPlant(4, -8.5);

  // ── SIDE PANEL UPDATE ──
  function updateSidePanel() {
    var el = function (id) { return document.getElementById(id); };
    if (el("sp-status")) {
      var s = sideData.autonomy_active ? "ACTIVE" : "STANDBY";
      el("sp-status").textContent = s;
      el("sp-status").className = "sp-badge " + (s === "ACTIVE" ? "active" : "standby");
    }
    if (el("sp-autonomy")) el("sp-autonomy").textContent = sideData.autonomy_active ? "Ativa" : "Inativa";
    if (el("sp-autonomy-reason")) el("sp-autonomy-reason").textContent = sideData.autonomy_reason || "";
    if (el("sp-direction")) el("sp-direction").textContent = sideData.direction || "N/D";
    if (el("sp-structure")) el("sp-structure").textContent = (sideData.smc || "N/D") + " / " + (sideData.elliott || "N/D");
    if (el("sp-confidence")) el("sp-confidence").textContent = sideData.confidence || "N/D";
    if (el("sp-alignment")) el("sp-alignment").textContent = sideData.alignment || "N/D";
    if (el("sp-context")) el("sp-context").textContent = sideData.context_phase || "N/D";
    if (el("sp-context-detail")) el("sp-context-detail").textContent = "Tendência: " + (sideData.context_trend || "N/D") + " | Vol: " + (sideData.context_volatility || "N/D");
    if (el("sp-risk")) el("sp-risk").textContent = "Método: " + (sideData.risk_method || 0) + "% | Diário: " + (sideData.risk_daily || 0) + "%";
    if (el("sp-shadow")) el("sp-shadow").textContent = sideData.shadow_total || 0;
    if (el("sp-shadow-detail")) el("sp-shadow-detail").textContent = "W: " + (sideData.shadow_wins || 0) + " | L: " + (sideData.shadow_losses || 0) + " | Abertos: " + (sideData.shadow_open || 0);
    if (el("sp-preop")) el("sp-preop").textContent = "Total: " + (sideData.pre_op_total || 0) + " | Fechadas: " + (sideData.pre_op_closed || 0);
    if (el("sp-errors")) el("sp-errors").textContent = sideData.error_count || 0;

    // Processes
    var procs = sideData.processes || {};
    var procMap = { operator: "proc-op", web: "proc-web", tunnel: "proc-tunnel", mt5: "proc-mt5" };
    Object.keys(procMap).forEach(function (k) {
      var el2 = document.getElementById(procMap[k]);
      if (el2) el2.className = "sp-proc " + (procs[k] ? "on" : "off");
    });
  }

  updateSidePanel();

  // ── CENTER BUTTON ──
  btnCenter.addEventListener("click", function () {
    camera.position.set(14, 14, 14);
    controls.target.set(0, 0, 0);
    controls.update();
  });

  // ── RESIZE ──
  window.addEventListener("resize", function () {
    W = container.clientWidth;
    H = container.clientHeight;
    camera.aspect = W / H;
    camera.updateProjectionMatrix();
    renderer.setSize(W, H);
    labelRenderer.setSize(W, H);
  });

  // ── HUB ANIMATION ──
  var clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);
    var t = clock.getElapsedTime();

    ring.rotation.z = t * 0.3;
    holo.rotation.y = t * 0.5;
    holo.material.opacity = 0.15 + Math.sin(t * 2) * 0.08;

    hubLight.intensity = 1.0 + Math.sin(t * 1.5) * 0.3;

    controls.update();
    renderer.render(scene, camera);
    labelRenderer.render(scene, camera);
  }

  // ── START ──
  setTimeout(function () {
    overlay.classList.add("hidden");
    animate();
  }, 800);
})();
