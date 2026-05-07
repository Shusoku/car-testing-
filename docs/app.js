const GRID_W = 22;
const GRID_H = 16;
const CELL = 38;
const CARS_TOTAL = 5;

const ROAD = 0;
const WALL = 1;

const COLORS = {
  bg: "#161a22",
  road: "#414854",
  wall: "#242a34",
  grid: "#2f3541",
  player: "#ff826e",
  ai: ["#74c3ff", "#a2e691", "#fcd678", "#c9a0fa"],
  target: "#ffe673",
};

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");
const reportEl = document.getElementById("report");
const reportSummaryEl = document.getElementById("reportSummary");
const reportListEl = document.getElementById("reportList");
document.getElementById("closeReport").onclick = () => (reportEl.style.display = "none");

function randInt(lo, hi) { return Math.floor(Math.random() * (hi - lo + 1)) + lo; }
function inBounds(r, c) { return r >= 0 && r < GRID_H && c >= 0 && c < GRID_W; }
function key(pos) { return `${pos[0]},${pos[1]}`; }

function neighbors4(grid, r, c) {
  const out = [];
  for (const [dr, dc] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    const nr = r + dr, nc = c + dc;
    if (inBounds(nr, nc) && grid[nr][nc] === ROAD) out.push([nr, nc]);
  }
  return out;
}

function bfsPath(grid, start, goal, blockedSet) {
  if (!goal) return null;
  if (start[0] === goal[0] && start[1] === goal[1]) return [start];
  const q = [start];
  const parent = new Map([[key(start), null]]);
  while (q.length) {
    const cur = q.shift();
    if (cur[0] === goal[0] && cur[1] === goal[1]) {
      const path = [];
      let k = key(cur);
      while (k) {
        const [r, c] = k.split(",").map(Number);
        path.push([r, c]);
        k = parent.get(k);
      }
      path.reverse();
      return path;
    }
    for (const nxt of neighbors4(grid, cur[0], cur[1])) {
      const nk = key(nxt);
      if (blockedSet.has(nk)) continue;
      if (!parent.has(nk)) {
        parent.set(nk, key(cur));
        q.push(nxt);
      }
    }
  }
  return null;
}

function generateWorld() {
  const grid = Array.from({ length: GRID_H }, () => Array(GRID_W).fill(WALL));
  const center = [Math.floor(GRID_H / 2), Math.floor(GRID_W / 2)];
  const [cr, cc] = center;
  for (let c = 1; c < GRID_W - 1; c++) grid[cr][c] = ROAD;
  for (let r = 1; r < GRID_H - 1; r++) grid[r][cc] = ROAD;

  const finalIntersection = [cr, GRID_W - 8];
  const lotLeft = GRID_W - 5;
  const lotRight = GRID_W - 4;
  const lotTop = cr - 2;
  const lotBottom = cr + 1;
  for (let c = cc; c <= finalIntersection[1]; c++) grid[cr][c] = ROAD;
  for (let c = finalIntersection[1]; c <= lotLeft; c++) grid[cr][c] = ROAD;
  for (let r = lotTop; r <= lotBottom; r++) {
    grid[r][lotLeft] = ROAD;
    grid[r][lotRight] = ROAD;
  }

  for (let i = 0; i < 4; i++) {
    const rr = randInt(2, GRID_H - 3), cc2 = randInt(2, cc - 2);
    for (let c = 1; c <= cc2; c++) grid[rr][c] = ROAD;
  }
  for (let i = 0; i < 3; i++) {
    const cc2 = randInt(2, cc - 1);
    for (let r = 2; r <= GRID_H - 3; r++) grid[r][cc2] = ROAD;
  }

  const parkingSlots = [
    [cr - 2, lotRight], [cr - 1, lotRight], [cr, lotRight], [cr + 1, lotRight],
    [cr - 2, lotLeft], [cr - 1, lotLeft], [cr, lotLeft], [cr + 1, lotLeft],
  ];
  const playerGoal = parkingSlots[0];
  const spawn = [];
  for (let r = 1; r < GRID_H - 1; r++) {
    for (let c = 1; c < cc; c++) if (grid[r][c] === ROAD) spawn.push([r, c]);
  }

  return { grid, center, finalIntersection, parkingSlots, playerGoal, spawn };
}

function randomCell(candidates, used) {
  const avail = candidates.filter((p) => !used.has(key(p)));
  return avail[randInt(0, avail.length - 1)];
}

let state = null;
function reset() {
  const world = generateWorld();
  const used = new Set();
  const cars = [];
  const playerPos = randomCell(world.spawn, used); used.add(key(playerPos));
  cars.push({ pos: playerPos, target: world.playerGoal, color: COLORS.player, policy: "player", moveTick: 0 });
  used.add(key(world.playerGoal));
  const aiGoals = world.parkingSlots.slice(1);
  for (let i = 0; i < CARS_TOTAL - 1; i++) {
    const pos = randomCell(world.spawn, used); used.add(key(pos));
    const isSupport = i === (CARS_TOTAL - 2);
    const isYield = i === 2 && !isSupport;
    const target = isSupport ? null : aiGoals[i % aiGoals.length];
    cars.push({
      pos, target, color: COLORS.ai[i % COLORS.ai.length],
      policy: isSupport ? "support" : (isYield ? "yield" : "bfs"), moveTick: 0,
    });
    if (target) used.add(key(target));
  }
  state = {
    ...world,
    cars,
    mode: "optimized",
    incidents: [],
    logs: ["Turn-based mode enabled.", "G toggles god mode.", "X opens incident report."],
    intersectionPriority: null,
    achieved: false,
  };
}

function canEnterIntersection(from, to, occupiedSet) {
  const center = state.center;
  if (to[0] !== center[0] || to[1] !== center[1]) return true;
  if (occupiedSet.has(key(center))) return false;
  return true;
}

function chooseUnblockMove(car, occupiedSet) {
  const opts = neighbors4(state.grid, car.pos[0], car.pos[1]).filter((p) => !occupiedSet.has(key(p)));
  if (!opts.length) return car.pos;
  let best = opts[0], bestScore = -1e9;
  for (const p of opts) {
    const mobility = neighbors4(state.grid, p[0], p[1]).length;
    const blocked = new Set(occupiedSet); blocked.delete(key(car.pos));
    const path = car.target ? bfsPath(state.grid, p, car.target, blocked) : null;
    const score = (path ? 500 - path.length : 0) + mobility;
    if (score > bestScore) { bestScore = score; best = p; }
  }
  return best;
}

function stepAI(car, occupiedSet) {
  const center = state.center;
  if (car.pos[0] === center[0] && car.pos[1] === center[1]) {
    for (const ex of [[center[0] - 1, center[1]], [center[0] + 1, center[1]], [center[0], center[1] - 1], [center[0], center[1] + 1]]) {
      if (inBounds(ex[0], ex[1]) && state.grid[ex[0]][ex[1]] === ROAD && !occupiedSet.has(key(ex))) return ex;
    }
  }
  if (car.policy === "yield") {
    const [r, c] = car.pos;
    if (r === state.center[0] && (occupiedSet.has(key([r, c - 1])) || occupiedSet.has(key([r, c + 1])))) {
      for (const side of [[r - 1, c], [r + 1, c]]) {
        if (inBounds(side[0], side[1]) && state.grid[side[0]][side[1]] === ROAD && !occupiedSet.has(key(side))) return side;
      }
    }
  }
  car.moveTick += 1;
  if (state.mode === "optimized" && car.moveTick % 3 === 0) return chooseUnblockMove(car, occupiedSet);
  if (!car.target) return chooseUnblockMove(car, occupiedSet);
  const blocked = new Set(occupiedSet); blocked.delete(key(car.pos));
  const path = bfsPath(state.grid, car.pos, car.target, state.mode === "god" ? new Set() : blocked);
  if (path && path.length >= 2 && !occupiedSet.has(key(path[1]))) return path[1];
  return chooseUnblockMove(car, occupiedSet);
}

function runTurn(playerMoved) {
  const occupied = new Set(state.cars.map((c) => key(c.pos)));
  const playerArrived = () => {
    const p = state.cars[0];
    return p.pos[0] === p.target[0] && p.pos[1] === p.target[1];
  };
  for (let i = 1; i < state.cars.length; i++) {
    const car = state.cars[i];
    let next = stepAI(car, occupied);
    if (!playerArrived() && car.policy === "bfs" && next[1] > state.center[1] && !(car.pos[0] === state.center[0] && car.pos[1] === state.center[1])) {
      next = car.pos;
    }
    if (!canEnterIntersection(car.pos, next, occupied)) next = car.pos;
    if (occupied.has(key(next)) && key(next) !== key(car.pos)) {
      state.incidents.unshift(`AI attempted occupied tile at ${next}`);
      next = car.pos;
    }
    occupied.delete(key(car.pos));
    occupied.add(key(next));
    car.pos = next;
  }
  if (!playerMoved) state.logs.unshift("Stall turn: player skipped movement.");
  const tracked = state.cars.filter((c) => c.policy === "player" || c.policy === "bfs");
  state.achieved = tracked.every((c) => c.target && c.pos[0] === c.target[0] && c.pos[1] === c.target[1]);
}

function tryPlayerMove(dr, dc) {
  const p = state.cars[0];
  const nxt = [p.pos[0] + dr, p.pos[1] + dc];
  if (!inBounds(nxt[0], nxt[1]) || state.grid[nxt[0]][nxt[1]] !== ROAD) return false;
  const occupied = new Set(state.cars.slice(1).map((c) => key(c.pos)));
  if (occupied.has(key(nxt))) {
    state.incidents.unshift(`Player attempted occupied tile at ${nxt}`);
    return false;
  }
  if (!canEnterIntersection(p.pos, nxt, new Set(state.cars.map((c) => key(c.pos))))) return false;
  p.pos = nxt;
  return true;
}

function draw() {
  ctx.fillStyle = COLORS.bg;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  for (let r = 0; r < GRID_H; r++) {
    for (let c = 0; c < GRID_W; c++) {
      ctx.fillStyle = state.grid[r][c] === ROAD ? COLORS.road : COLORS.wall;
      ctx.fillRect(c * CELL, r * CELL, CELL, CELL);
      ctx.strokeStyle = COLORS.grid;
      ctx.strokeRect(c * CELL, r * CELL, CELL, CELL);
    }
  }
  for (let i = 0; i < state.cars.length; i++) {
    const car = state.cars[i];
    if (car.target) {
      ctx.strokeStyle = i === 0 ? "#ff967f" : COLORS.target;
      ctx.beginPath();
      ctx.arc(car.target[1] * CELL + CELL / 2, car.target[0] * CELL + CELL / 2, 6, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.fillStyle = car.color;
    ctx.beginPath();
    ctx.arc(car.pos[1] * CELL + CELL / 2, car.pos[0] * CELL + CELL / 2, CELL / 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#111";
    ctx.fillText(i === 0 ? "P" : `A${i}`, car.pos[1] * CELL + 12, car.pos[0] * CELL + 22);
  }

  statusEl.textContent = `Mode: ${state.mode} | Cars: ${state.cars.length} | Incidents: ${state.incidents.length}${state.achieved ? " | ACCOMPLISHED" : ""}`;
}

function updateReport() {
  reportSummaryEl.textContent = `Total incidents: ${state.incidents.length}`;
  reportListEl.innerHTML = "";
  for (const line of state.incidents.slice(0, 20)) {
    const li = document.createElement("li");
    li.textContent = line;
    reportListEl.appendChild(li);
  }
}

window.addEventListener("keydown", (e) => {
  if (!state) return;
  let moved = false;
  if (e.key === "r" || e.key === "R") reset();
  else if (e.key === "g" || e.key === "G") state.mode = state.mode === "god" ? "optimized" : "god";
  else if (e.key === "x" || e.key === "X") {
    updateReport();
    reportEl.style.display = reportEl.style.display === "flex" ? "none" : "flex";
  } else if (!state.achieved && (e.key === "ArrowUp" || e.key === "w" || e.key === "W")) moved = tryPlayerMove(-1, 0);
  else if (!state.achieved && (e.key === "ArrowDown" || e.key === "s" || e.key === "S")) moved = tryPlayerMove(1, 0);
  else if (!state.achieved && (e.key === "ArrowLeft" || e.key === "a" || e.key === "A")) moved = tryPlayerMove(0, -1);
  else if (!state.achieved && (e.key === "ArrowRight" || e.key === "d" || e.key === "D")) moved = tryPlayerMove(0, 1);
  else if (!state.achieved && e.code === "Space") {
    if (state.mode === "god") {
      const p = state.cars[0];
      const occupied = new Set(state.cars.slice(1).map((c) => key(c.pos)));
      const path = bfsPath(state.grid, p.pos, p.target, occupied);
      if (path && path.length >= 2) {
        const nxt = path[1];
        if (!occupied.has(key(nxt))) {
          p.pos = nxt;
          moved = true;
        }
      }
      runTurn(moved);
    } else {
      runTurn(false);
    }
  }
  if (moved) runTurn(true);
  draw();
});

reset();
draw();
