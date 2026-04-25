const canvas = document.getElementById("game-canvas");
const ctx = canvas.getContext("2d");

const startButton = document.getElementById("start-btn");
const restartButton = document.getElementById("restart-btn");
const statusChip = document.getElementById("status-chip");
const shellTitle = document.getElementById("shell-title");
const shellSubtitle = document.getElementById("shell-subtitle");
const pluginBadge = document.getElementById("plugin-badge");
const platformPill = document.getElementById("platform-pill");
const rendererPill = document.getElementById("renderer-pill");
const queueList = document.getElementById("queue-list");
const controlList = document.getElementById("control-list");
const assemblyPlugin = document.getElementById("assembly-plugin");
const assemblyRenderer = document.getElementById("assembly-renderer");
const assemblyMcpTools = document.getElementById("assembly-mcp-tools");
const assemblyRoute = document.getElementById("assembly-route");

const statNodes = {
  score: document.getElementById("stat-score"),
  level: document.getElementById("stat-level"),
  lines: document.getElementById("stat-lines"),
  moves: document.getElementById("stat-moves"),
  gravity: document.getElementById("stat-gravity"),
  piece: document.getElementById("stat-piece"),
};

const BOARD_ROWS = 20;
const BOARD_COLS = 10;
const BOARD_FRAME = { x: 60, y: 16, width: 300, height: 600 };
const CELL_SIZE = BOARD_FRAME.width / BOARD_COLS;

const pieceColors = {
  I: "#49dbe6",
  O: "#f4d35e",
  T: "#c084fc",
  S: "#7ddf64",
  Z: "#ff6b6b",
  J: "#60a5fa",
  L: "#fb923c",
};

const defaultManifest = {
  plugin_id: "tetris",
  name: "Tetris",
  description: "Python-backed Tetris wrapped in a responsive web shell with MCP control hooks.",
  platforms: ["desktop", "mobile"],
  controls: [
    { action: "MOVE_LEFT", label: "Move left", desktop: "Arrow Left", mobile: "Tap Left" },
    { action: "MOVE_RIGHT", label: "Move right", desktop: "Arrow Right", mobile: "Tap Right" },
    { action: "MOVE_DOWN", label: "Soft drop", desktop: "Arrow Down", mobile: "Tap Down" },
    { action: "ROTATE_CW", label: "Rotate", desktop: "Arrow Up / X", mobile: "Tap Rotate" },
    { action: "ROTATE_CCW", label: "Rotate back", desktop: "Z", mobile: "Tap Back" },
    { action: "HARD_DROP", label: "Hard drop", desktop: "Space", mobile: "Tap Drop" },
  ],
  frontend_shell: {
    route: "/",
    renderer: "html-canvas-shell",
    canvas_width: 420,
    canvas_height: 620,
    responsive: true,
    touch_controls: true,
  },
  mcp_server: {
    tools: [],
  },
  assembly: {
    launch_endpoint: "/api/sdk/plugins/tetris/launch",
    action_endpoint: "/api/game/action",
    advance_endpoint: "/api/game/advance",
    restart_endpoint: "/api/game/restart",
    entry_route: "/",
  },
};

let gameId = null;
let state = null;
let shellConfig = defaultManifest;
let statusMessage = "Loading Game Design Agent assembly...";
let requestInFlight = false;
let accumulatorMs = 0;
let lastFrameAt = performance.now();

function setStatus(message, tone = "neutral") {
  statusMessage = message;
  statusChip.textContent = message;
  statusChip.dataset.tone = tone;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

async function apiRequest(url, payload) {
  return fetchJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function randomPlayerId() {
  return `player-${Math.random().toString(36).slice(2, 9)}`;
}

function getAssemblyConfig() {
  return shellConfig?.assembly || defaultManifest.assembly;
}

function syncState(nextState) {
  state = nextState;
  if (nextState?.game_id) {
    gameId = nextState.game_id;
    restartButton.disabled = false;
  }

  setStatus(
    nextState?.message || "Run synced.",
    nextState?.game_over ? "danger" : "ready",
  );
  renderHud();
}

function renderControls(controls) {
  controlList.innerHTML = "";
  for (const control of controls) {
    const item = document.createElement("li");

    const action = document.createElement("span");
    action.className = "control-action";
    action.textContent = control.label;

    const binding = document.createElement("span");
    binding.className = "control-binding";
    binding.textContent = `${control.desktop} · ${control.mobile}`;

    item.append(action, binding);
    controlList.appendChild(item);
  }
}

function renderQueue(nextQueue) {
  queueList.innerHTML = "";

  for (const piece of nextQueue.slice(0, 3)) {
    const card = document.createElement("article");
    card.className = "queue-card";

    const swatch = document.createElement("span");
    swatch.className = "queue-swatch";
    swatch.style.setProperty("--swatch", pieceColors[piece] || "#94a3b8");

    const label = document.createElement("span");
    label.className = "queue-label";
    label.textContent = piece;

    card.append(swatch, label);
    queueList.appendChild(card);
  }

  if (queueList.childElementCount === 0) {
    const emptyCard = document.createElement("article");
    emptyCard.className = "queue-card";
    emptyCard.textContent = "Waiting";
    queueList.appendChild(emptyCard);
  }
}

function renderHud() {
  const stats = state || {
    score: 0,
    level: 1,
    lines_cleared: 0,
    move_count: 0,
    gravity_ms: 800,
    current_piece: null,
    next_queue: [],
  };

  statNodes.score.textContent = String(stats.score);
  statNodes.level.textContent = String(stats.level);
  statNodes.lines.textContent = String(stats.lines_cleared);
  statNodes.moves.textContent = String(stats.move_count);
  statNodes.gravity.textContent = `${stats.gravity_ms} ms`;
  statNodes.piece.textContent = stats.current_piece || "-";
  renderQueue(stats.next_queue || []);
}

function applyShellMetadata(manifest) {
  shellConfig = manifest || defaultManifest;
  const shell = shellConfig.frontend_shell || defaultManifest.frontend_shell;

  canvas.width = shell.canvas_width || defaultManifest.frontend_shell.canvas_width;
  canvas.height = shell.canvas_height || defaultManifest.frontend_shell.canvas_height;

  pluginBadge.textContent = `${(shellConfig.plugin_id || "tetris").toUpperCase()} plug-in · Game Design Agent API`;
  shellTitle.textContent = shellConfig.name || "Tetris";
  shellSubtitle.textContent = shellConfig.description || defaultManifest.description;
  platformPill.textContent = (shellConfig.platforms || defaultManifest.platforms).join(" + ");
  rendererPill.textContent = shell.renderer || defaultManifest.frontend_shell.renderer;
  assemblyPlugin.textContent = shellConfig.plugin_id || "tetris";
  assemblyRenderer.textContent = shell.renderer || "html-canvas-shell";
  assemblyMcpTools.textContent = String((shellConfig.mcp_server?.tools || []).length);
  assemblyRoute.textContent = shellConfig.assembly?.entry_route || shell.route || "/";

  renderControls(shellConfig.controls || defaultManifest.controls);
  renderHud();
}

async function loadShellAssembly() {
  try {
    const manifest = await fetchJson("/api/sdk/plugins/tetris/assembly");
    applyShellMetadata(manifest);
    setStatus("Assembly loaded. Start a run on desktop or mobile.", "ready");
  } catch (error) {
    applyShellMetadata(defaultManifest);
    setStatus(error.message, "danger");
  }
}

async function guardedRequest(task) {
  if (requestInFlight) {
    return;
  }

  requestInFlight = true;
  try {
    const nextState = await task();
    syncState(nextState);
  } catch (error) {
    setStatus(error.message, "danger");
  } finally {
    requestInFlight = false;
  }
}

async function startGame() {
  accumulatorMs = 0;
  await guardedRequest(() =>
    apiRequest(getAssemblyConfig().launch_endpoint, {
      player_id: randomPlayerId(),
    }),
  );
}

async function restartGame() {
  if (!gameId) {
    await startGame();
    return;
  }

  accumulatorMs = 0;
  await guardedRequest(() =>
    apiRequest(getAssemblyConfig().restart_endpoint, {
      game_id: gameId,
    }),
  );
}

async function sendAction(action) {
  if (!gameId || !state || state.game_over) {
    return;
  }

  await guardedRequest(() =>
    apiRequest(getAssemblyConfig().action_endpoint, {
      game_id: gameId,
      action,
    }),
  );
}

async function maybeAdvanceGame() {
  if (!gameId || !state || state.game_over || requestInFlight) {
    return;
  }

  const gravityMs = state.gravity_ms || 800;
  const steps = Math.floor(accumulatorMs / gravityMs);
  if (steps < 1) {
    return;
  }

  accumulatorMs -= steps * gravityMs;
  await guardedRequest(() =>
    apiRequest(getAssemblyConfig().advance_endpoint, {
      game_id: gameId,
      steps,
    }),
  );
}

function drawRoundedRect(x, y, width, height, radius, fillStyle, strokeStyle = null) {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
  ctx.fillStyle = fillStyle;
  ctx.fill();
  if (strokeStyle) {
    ctx.strokeStyle = strokeStyle;
    ctx.stroke();
  }
  ctx.restore();
}

function drawBoard(board) {
  drawRoundedRect(
    BOARD_FRAME.x - 18,
    BOARD_FRAME.y - 12,
    BOARD_FRAME.width + 36,
    BOARD_FRAME.height + 24,
    26,
    "#091120",
    "rgba(255, 184, 77, 0.24)",
  );

  for (let row = 0; row < BOARD_ROWS; row += 1) {
    for (let col = 0; col < BOARD_COLS; col += 1) {
      const x = BOARD_FRAME.x + col * CELL_SIZE;
      const y = BOARD_FRAME.y + row * CELL_SIZE;
      const cell = board?.[row]?.[col] || null;

      ctx.fillStyle = cell ? pieceColors[cell] || "#f8f5ec" : "#132139";
      ctx.fillRect(x, y, CELL_SIZE - 2, CELL_SIZE - 2);

      ctx.fillStyle = cell ? "rgba(255,255,255,0.16)" : "rgba(255,255,255,0.04)";
      ctx.fillRect(x + 3, y + 3, CELL_SIZE - 8, 6);
    }
  }
}

function drawShellBackdrop() {
  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  gradient.addColorStop(0, "#101828");
  gradient.addColorStop(0.55, "#0d1525");
  gradient.addColorStop(1, "#050912");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "rgba(255, 184, 77, 0.09)";
  ctx.beginPath();
  ctx.arc(canvas.width - 54, 56, 78, 0, Math.PI * 2);
  ctx.fill();
}

function drawIntroOverlay() {
  drawRoundedRect(34, 176, canvas.width - 68, 230, 28, "rgba(8, 13, 24, 0.86)");

  ctx.fillStyle = "#fff6e8";
  ctx.font = '700 34px "Trebuchet MS"';
  ctx.fillText("Tetris SDK Shell", 64, 226);

  ctx.fillStyle = "#ffc875";
  ctx.font = '20px "Trebuchet MS"';
  ctx.fillText("Canvas playfield, DOM HUD, MCP controls, mobile-ready shell.", 64, 262);

  ctx.fillStyle = "#d6ddea";
  ctx.font = '18px "Trebuchet MS"';
  const hints = [
    "Arrow keys move and drop.",
    "X or Up rotates clockwise. Z rotates back.",
    "Use the touch deck below the playfield on mobile.",
  ];

  hints.forEach((hint, index) => {
    ctx.fillText(hint, 64, 314 + index * 36);
  });
}

function drawGameOverOverlay() {
  if (!state?.game_over) {
    return;
  }

  drawRoundedRect(48, 224, canvas.width - 96, 148, 26, "rgba(7, 11, 20, 0.88)");
  ctx.fillStyle = "#fff2dc";
  ctx.font = '700 36px "Trebuchet MS"';
  ctx.fillText("Run Complete", 112, 274);

  ctx.fillStyle = "#f6d8a7";
  ctx.font = '22px "Trebuchet MS"';
  ctx.fillText(`Score ${state.score} · Lines ${state.lines_cleared}`, 112, 316);
}

function render() {
  drawShellBackdrop();
  drawBoard(state?.board);

  if (!state) {
    drawIntroOverlay();
  } else if (state.game_over) {
    drawGameOverOverlay();
  }
}

function renderGameToText() {
  return JSON.stringify({
    coordinate_system: {
      origin: "top-left",
      x: "increases to the right",
      y: "increases downward",
    },
    mode: state ? "playing" : "menu",
    game_id: gameId,
    score: state?.score ?? 0,
    level: state?.level ?? 1,
    lines_cleared: state?.lines_cleared ?? 0,
    move_count: state?.move_count ?? 0,
    game_over: state?.game_over ?? false,
    current_piece: state?.current_piece ?? null,
    current_position: state?.current_position ?? null,
    current_rotation: state?.current_rotation ?? 0,
    next_queue: state?.next_queue ?? [],
    board: state?.board_text ?? Array.from({ length: BOARD_ROWS }, () => ".".repeat(BOARD_COLS)),
    message: statusMessage,
  });
}

async function advanceTime(ms) {
  accumulatorMs += ms;
  await maybeAdvanceGame();
  render();
}

async function toggleFullscreen() {
  const surface = canvas.parentElement;
  if (!document.fullscreenElement) {
    await surface.requestFullscreen();
    return;
  }
  await document.exitFullscreen();
}

function handleKeydown(event) {
  if (event.key === "f" || event.key === "F") {
    event.preventDefault();
    void toggleFullscreen();
    return;
  }

  const actionMap = {
    ArrowLeft: "MOVE_LEFT",
    ArrowRight: "MOVE_RIGHT",
    ArrowDown: "MOVE_DOWN",
    ArrowUp: "ROTATE_CW",
    x: "ROTATE_CW",
    X: "ROTATE_CW",
    z: "ROTATE_CCW",
    Z: "ROTATE_CCW",
    " ": "HARD_DROP",
  };

  const action = actionMap[event.key];
  if (!action) {
    return;
  }

  event.preventDefault();
  void sendAction(action);
}

function bindTouchDeck() {
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      void sendAction(button.dataset.action);
    });
  });
}

function frame(now) {
  const elapsed = now - lastFrameAt;
  lastFrameAt = now;

  if (state && !state.game_over) {
    accumulatorMs += elapsed;
    void maybeAdvanceGame();
  }

  render();
  window.requestAnimationFrame(frame);
}

startButton.addEventListener("click", () => {
  void startGame();
});

restartButton.addEventListener("click", () => {
  void restartGame();
});

document.addEventListener("keydown", handleKeydown);
bindTouchDeck();
applyShellMetadata(defaultManifest);
setStatus("Loading Game Design Agent assembly...", "neutral");
render();
window.requestAnimationFrame(frame);
void loadShellAssembly();

window.render_game_to_text = renderGameToText;
window.advanceTime = advanceTime;
