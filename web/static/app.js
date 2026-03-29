const canvas = document.getElementById("game-canvas");
const ctx = canvas.getContext("2d");
const startButton = document.getElementById("start-btn");
const restartButton = document.getElementById("restart-btn");

const BOARD_ORIGIN = { x: 70, y: 80 };
const CELL_SIZE = 26;
const PANEL_X = 420;
const BOARD_ROWS = 20;
const BOARD_COLS = 10;

const pieceColors = {
  I: "#49dbe6",
  O: "#f4d35e",
  T: "#c084fc",
  S: "#7ddf64",
  Z: "#ff6b6b",
  J: "#60a5fa",
  L: "#fb923c",
};

const previewShapes = {
  I: [[0, 1], [1, 1], [2, 1], [3, 1]],
  O: [[1, 0], [2, 0], [1, 1], [2, 1]],
  T: [[1, 0], [0, 1], [1, 1], [2, 1]],
  S: [[1, 0], [2, 0], [0, 1], [1, 1]],
  Z: [[0, 0], [1, 0], [1, 1], [2, 1]],
  J: [[0, 0], [0, 1], [1, 1], [2, 1]],
  L: [[2, 0], [0, 1], [1, 1], [2, 1]],
};

let gameId = null;
let state = null;
let statusMessage = "Press Start Game to launch a standalone Python-backed run.";
let accumulatorMs = 0;
let lastFrameAt = performance.now();
let requestInFlight = false;

async function apiRequest(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function randomPlayerId() {
  return `player-${Math.random().toString(36).slice(2, 9)}`;
}

function syncState(nextState) {
  state = nextState;
  if (nextState && nextState.game_id) {
    gameId = nextState.game_id;
    restartButton.disabled = false;
  }
  statusMessage = nextState?.message || statusMessage;
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
    statusMessage = error.message;
  } finally {
    requestInFlight = false;
  }
}

async function startGame() {
  accumulatorMs = 0;
  await guardedRequest(() =>
    apiRequest("/api/game/start", {
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
    apiRequest("/api/game/restart", {
      game_id: gameId,
    }),
  );
}

async function sendAction(action) {
  if (!gameId || !state || state.game_over) {
    return;
  }
  await guardedRequest(() =>
    apiRequest("/api/game/action", {
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
    apiRequest("/api/game/advance", {
      game_id: gameId,
      steps,
    }),
  );
}

function drawRoundedRect(x, y, width, height, radius, fillStyle) {
  ctx.save();
  ctx.fillStyle = fillStyle;
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
  ctx.fill();
  ctx.restore();
}

function drawBoard(board) {
  drawRoundedRect(BOARD_ORIGIN.x - 18, BOARD_ORIGIN.y - 18, 316, 556, 18, "#0c1019");

  for (let row = 0; row < BOARD_ROWS; row += 1) {
    for (let col = 0; col < BOARD_COLS; col += 1) {
      const x = BOARD_ORIGIN.x + col * CELL_SIZE;
      const y = BOARD_ORIGIN.y + row * CELL_SIZE;
      const cell = board?.[row]?.[col] || null;

      ctx.fillStyle = cell ? pieceColors[cell] || "#f4f1de" : "#182130";
      ctx.fillRect(x, y, CELL_SIZE - 2, CELL_SIZE - 2);

      ctx.fillStyle = cell ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.03)";
      ctx.fillRect(x + 3, y + 3, CELL_SIZE - 8, 6);
    }
  }
}

function drawPreviewPiece(piece, originX, originY) {
  const shape = previewShapes[piece];
  if (!shape) {
    return;
  }
  for (const [x, y] of shape) {
    ctx.fillStyle = pieceColors[piece];
    ctx.fillRect(originX + x * 16, originY + y * 16, 14, 14);
  }
}

function drawSidebar() {
  drawRoundedRect(PANEL_X, 80, 470, 500, 22, "#f3ece0");

  ctx.fillStyle = "#132642";
  ctx.font = "700 40px Trebuchet MS";
  ctx.fillText("Standalone Tetris", PANEL_X + 30, 130);

  ctx.fillStyle = "#4b5563";
  ctx.font = "18px Trebuchet MS";
  ctx.fillText("Python simulation, canvas renderer, browser controls.", PANEL_X + 30, 165);

  const stats = state || {
    score: 0,
    level: 1,
    lines_cleared: 0,
    move_count: 0,
    gravity_ms: 800,
    next_queue: [],
  };

  const statRows = [
    ["Score", String(stats.score)],
    ["Level", String(stats.level)],
    ["Lines", String(stats.lines_cleared)],
    ["Moves", String(stats.move_count)],
    ["Gravity", `${stats.gravity_ms} ms`],
  ];

  ctx.font = "700 22px Trebuchet MS";
  ctx.fillStyle = "#132642";
  ctx.fillText("Run Stats", PANEL_X + 30, 225);

  ctx.font = "18px Trebuchet MS";
  statRows.forEach(([label, value], index) => {
    const top = 260 + index * 42;
    ctx.fillStyle = "#6b7280";
    ctx.fillText(label, PANEL_X + 30, top);
    ctx.fillStyle = "#111827";
    ctx.fillText(value, PANEL_X + 175, top);
  });

  ctx.font = "700 22px Trebuchet MS";
  ctx.fillStyle = "#132642";
  ctx.fillText("Next Queue", PANEL_X + 30, 470);

  (stats.next_queue || []).slice(0, 3).forEach((piece, index) => {
    const boxX = PANEL_X + 35 + index * 125;
    const boxY = 500;
    drawRoundedRect(boxX, boxY, 105, 70, 18, "#fffaf2");
    drawPreviewPiece(piece, boxX + 18, boxY + 16);
    ctx.fillStyle = "#6b7280";
    ctx.font = "15px Trebuchet MS";
    ctx.fillText(piece, boxX + 74, boxY + 56);
  });
}

function drawFooter() {
  drawRoundedRect(60, 570, 860, 42, 18, "rgba(12,16,25,0.84)");
  ctx.fillStyle = state?.game_over ? "#ff6b6b" : "#f6f3eb";
  ctx.font = "18px Trebuchet MS";
  ctx.fillText(statusMessage, 84, 598);
}

function drawStartOverlay() {
  drawRoundedRect(110, 120, 740, 390, 34, "rgba(12,16,25,0.92)");

  ctx.fillStyle = "#f8f7f2";
  ctx.font = "700 56px Trebuchet MS";
  ctx.fillText("Standalone Tetris", 156, 208);

  ctx.fillStyle = "#f4d35e";
  ctx.font = "22px Trebuchet MS";
  ctx.fillText("Built in Python, rendered in HTML canvas, no external game engine.", 156, 252);

  ctx.fillStyle = "#d1d5db";
  ctx.font = "20px Trebuchet MS";
  const lines = [
    "Controls",
    "Arrow Left / Right: move",
    "Arrow Down: soft drop",
    "Arrow Up or X: rotate clockwise",
    "Z: rotate counter-clockwise",
    "Space: hard drop",
    "F: fullscreen",
  ];
  lines.forEach((line, index) => {
    ctx.fillText(line, 156, 312 + index * 34);
  });
}

function drawGameOverOverlay() {
  if (!state?.game_over) {
    return;
  }

  drawRoundedRect(180, 220, 600, 170, 28, "rgba(12,16,25,0.88)");
  ctx.fillStyle = "#ffedd5";
  ctx.font = "700 46px Trebuchet MS";
  ctx.fillText("Run Complete", 330, 285);

  ctx.font = "22px Trebuchet MS";
  ctx.fillStyle = "#f9fafb";
  ctx.fillText(`Final score ${state.score} | ${state.lines_cleared} cleared lines`, 255, 330);
}

function render() {
  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  gradient.addColorStop(0, "#151722");
  gradient.addColorStop(0.58, "#1f2937");
  gradient.addColorStop(1, "#101319");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  drawBoard(state?.board);
  drawSidebar();
  drawFooter();

  if (!state) {
    drawStartOverlay();
  } else if (state.game_over) {
    drawGameOverOverlay();
  }
}

function renderGameToText() {
  const payload = {
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
  };
  return JSON.stringify(payload);
}

async function advanceTime(ms) {
  accumulatorMs += ms;
  await maybeAdvanceGame();
  render();
}

async function toggleFullscreen() {
  if (!document.fullscreenElement) {
    await canvas.requestFullscreen();
    return;
  }
  await document.exitFullscreen();
}

function handleKeydown(event) {
  const key = event.key;
  if (key === "f" || key === "F") {
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

  const action = actionMap[key];
  if (!action) {
    return;
  }

  event.preventDefault();
  void sendAction(action);
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

window.render_game_to_text = renderGameToText;
window.advanceTime = advanceTime;

render();
window.requestAnimationFrame(frame);
