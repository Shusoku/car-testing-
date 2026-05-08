"""
Turn-based automated car testing environment.

Controls:
- Arrow keys / WASD: move your car one tile
- Space: stall (skip your turn)
- G: toggle AI mode (optimized <-> god)
- R: regenerate map
- Click X on incident report to close it
- Esc: quit
"""
from __future__ import annotations

import random
import sys
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

try:
    import pygame
except ImportError:
    print("Install pygame: py -m pip install pygame")
    sys.exit(1)

Pos = Tuple[int, int]

GRID_W = 22
GRID_H = 16
CELL = 38
CARS_TOTAL = 5
FPS = 60

ROAD = 0
WALL = 1

BG = (20, 22, 28)
ROAD_COLOR = (65, 72, 84)
WALL_COLOR = (34, 38, 48)
GRID_LINE = (46, 51, 61)
USER_COLOR = (255, 130, 110)
AI_COLORS = [(116, 195, 255), (162, 230, 145), (252, 214, 120), (201, 160, 250)]
TARGET_COLOR = (255, 230, 115)


@dataclass
class Car:
    pos: Pos
    target: Optional[Pos]
    is_player: bool = False
    color: Tuple[int, int, int] = (255, 255, 255)
    policy: str = "bfs"
    move_tick: int = 0


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < GRID_H and 0 <= c < GRID_W


def neighbors4(grid: List[List[int]], r: int, c: int) -> Sequence[Pos]:
    out: List[Pos] = []
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc) and grid[nr][nc] == ROAD:
            out.append((nr, nc))
    return out


def bfs_path(grid: List[List[int]], start: Pos, goal: Pos, blocked: Set[Pos]) -> Optional[List[Pos]]:
    if start == goal:
        return [start]
    q: deque[Pos] = deque([start])
    parent: dict[Pos, Optional[Pos]] = {start: None}
    while q:
        cur = q.popleft()
        if cur == goal:
            path: List[Pos] = []
            p: Optional[Pos] = cur
            while p is not None:
                path.append(p)
                p = parent[p]
            path.reverse()
            return path
        for nxt in neighbors4(grid, cur[0], cur[1]):
            if nxt in blocked:
                continue
            if nxt not in parent:
                parent[nxt] = cur
                q.append(nxt)
    return None


def choose_unblock_move(grid: List[List[int]], cur: Pos, occupied: Set[Pos], target: Optional[Pos]) -> Pos:
    """Try to escape local blockades by preferring moves with more future options."""
    options = [nxt for nxt in neighbors4(grid, cur[0], cur[1]) if nxt not in occupied]
    if not options:
        return cur

    best = cur
    best_score: Tuple[int, int, int] = (-1, -1, -10**9)
    for nxt in options:
        future_open = sum(1 for nn in neighbors4(grid, nxt[0], nxt[1]) if nn not in occupied or nn == cur)
        blocked_next = set(occupied)
        blocked_next.discard(cur)
        path = bfs_path(grid, nxt, target, blocked_next) if target is not None else None
        reachable = 1 if path else 0
        # Prefer reachable moves; if unreachable, still prefer highest mobility.
        target_bias = -len(path) if path else 0
        score = (reachable, future_open, target_bias)
        if score > best_score:
            best_score = score
            best = nxt
    return best


def random_road_cell(grid: List[List[int]], rng: random.Random, used: Set[Pos], candidates: Optional[List[Pos]] = None) -> Pos:
    source = candidates if candidates is not None else [(r, c) for r in range(GRID_H) for c in range(GRID_W)]
    roads = [(r, c) for r, c in source if grid[r][c] == ROAD and (r, c) not in used]
    if not roads:
        raise RuntimeError("No road cell available.")
    return rng.choice(roads)


def carve_hline(grid: List[List[int]], row: int, c0: int, c1: int) -> None:
    lo, hi = sorted((c0, c1))
    for c in range(lo, hi + 1):
        grid[row][c] = ROAD


def carve_vline(grid: List[List[int]], col: int, r0: int, r1: int) -> None:
    lo, hi = sorted((r0, r1))
    for r in range(lo, hi + 1):
        grid[r][col] = ROAD


def generate_road_grid(rng: random.Random) -> Tuple[List[List[int]], Dict[str, object]]:
    grid = [[WALL for _ in range(GRID_W)] for _ in range(GRID_H)]

    # Mandatory 4-way center lock.
    center_row = GRID_H // 2
    center_col = GRID_W // 2
    carve_hline(grid, center_row, 1, GRID_W - 2)
    carve_vline(grid, center_col, 1, GRID_H - 2)

    # Shared off-road parking lot to the east: one lane feeds into a 4x2 box.
    final_intersection = (center_row, GRID_W - 8)
    lot_left = GRID_W - 5
    lot_right = GRID_W - 4
    lot_top = center_row - 2
    lot_bottom = center_row + 1

    # Single approach lane from center to the lot entry.
    carve_hline(grid, center_row, center_col, final_intersection[1])
    carve_hline(grid, center_row, final_intersection[1], lot_left)

    # 4x2 parking box (4 rows x 2 cols), vertically stacked.
    for r in range(lot_top, lot_bottom + 1):
        for c in (lot_left, lot_right):
            grid[r][c] = ROAD
    # Internal connector between columns for easy parking flow.
    for r in range(lot_top, lot_bottom + 1):
        carve_hline(grid, r, lot_left, lot_right)

    # Add left-side streets for traffic variety, but avoid alternate lot access.
    for _ in range(4):
        rr = rng.randint(2, GRID_H - 3)
        cc = rng.randint(2, center_col - 2)
        carve_hline(grid, rr, 1, cc)
    for _ in range(3):
        cc = rng.randint(2, center_col - 1)
        carve_vline(grid, cc, 2, GRID_H - 3)

    # Fill order is designed to avoid blocking access:
    # first line (far/right column) top->bottom, then second line (left column).
    parking_slots: List[Pos] = [
        (center_row - 2, lot_right),  # player slot
        (center_row - 1, lot_right),
        (center_row, lot_right),
        (center_row + 1, lot_right),
        (center_row - 2, lot_left),
        (center_row - 1, lot_left),
        (center_row, lot_left),
        (center_row + 1, lot_left),
    ]

    spawn_zone = [(r, c) for r in range(1, GRID_H - 1) for c in range(1, center_col) if grid[r][c] == ROAD]
    gate_zone = {(center_row, c) for c in range(final_intersection[1], GRID_W - 3)}
    gate_zone.update(parking_slots)

    return grid, {
        "parking_slots": parking_slots,
        "player_goal": parking_slots[0],
        "final_intersection": final_intersection,
        "spawn_zone": spawn_zone,
        "gate_zone": gate_zone,
    }


def step_ai_car(
    grid: List[List[int]],
    car: Car,
    all_positions: Set[Pos],
    god_mode: bool,
    intersection_center: Pos,
) -> Pos:
    if car.target == intersection_center:
        # Center is never a valid parking target; force an unblock move instead.
        return choose_unblock_move(grid, car.pos, all_positions, target=None)

    if car.pos == intersection_center:
        # If someone is queued around the center, clear the intersection quickly.
        neighbors = neighbors4(grid, intersection_center[0], intersection_center[1])
        pressure = any(n in all_positions and n != car.pos for n in neighbors)
        if pressure:
            exits = [n for n in neighbors if n not in all_positions]
            if exits:
                # Prefer stepping to the side (N/S) so through-lane traffic can pass.
                exits.sort(key=lambda ex: (0 if ex[0] != intersection_center[0] else 1, abs(ex[1] - intersection_center[1])))
                if car.target is not None:
                    blocked = set(all_positions)
                    blocked.discard(car.pos)
                    scored: List[Tuple[int, Pos]] = []
                    for ex in exits:
                        path = bfs_path(grid, ex, car.target, blocked)
                        scored.append((len(path) if path else 10**9, ex))
                    scored.sort(key=lambda item: item[0])
                    if scored[0][0] < 10**9:
                        return scored[0][1]
                return random.choice(exits)

    if car.policy == "yield":
        # A3 yield behavior: if traffic is lined up on the lane, step aside.
        r, c = car.pos
        center_row = GRID_H // 2
        if r == center_row and ((r, c - 1) in all_positions or (r, c + 1) in all_positions):
            for side in ((r - 1, c), (r + 1, c)):
                if in_bounds(*side) and grid[side[0]][side[1]] == ROAD and side not in all_positions:
                    return side

    if car.policy == "support":
        # Route-clearing behavior: pick a legal move that gets away from congestion.
        opts = [nxt for nxt in neighbors4(grid, car.pos[0], car.pos[1]) if nxt not in all_positions]
        if not opts:
            return car.pos
        opts.sort(key=lambda p: abs(p[0] - GRID_H // 2) + abs(p[1] - GRID_W // 2), reverse=True)
        return opts[0]

    car.move_tick += 1
    # In optimized mode we keep the occasional random behavior for stress testing.
    # In god mode, use pure route solving every turn.
    if (car.move_tick % 3 == 0) and (not god_mode):
        return choose_unblock_move(grid, car.pos, all_positions, car.target)

    if car.target is None or car.pos == car.target:
        return car.pos

    blocked = set(all_positions)
    blocked.discard(car.pos)
    if god_mode:
        path = bfs_path(grid, car.pos, car.target, blocked=set())
    else:
        path = bfs_path(grid, car.pos, car.target, blocked=blocked)

    if path and len(path) >= 2:
        nxt = path[1]
        if nxt not in all_positions:
            return nxt
        return car.pos

    return choose_unblock_move(grid, car.pos, all_positions, car.target)


def run() -> None:
    rng = random.Random()
    pygame.init()
    font = pygame.font.SysFont("consolas", 18)
    small = pygame.font.SysFont("consolas", 15)
    logical_w = GRID_W * CELL
    logical_h = GRID_H * CELL + 72
    is_web = sys.platform == "emscripten"

    if is_web:
        screen = pygame.display.set_mode((logical_w, logical_h))
        canvas = screen
    else:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        canvas = pygame.Surface((logical_w, logical_h))
    pygame.display.set_caption("Automated Car Testing Environment")
    clock = pygame.time.Clock()

    def reset_world() -> Tuple[List[List[int]], List[Car], str, deque[str], Dict[str, object]]:
        grid, layout = generate_road_grid(rng)
        center = (GRID_H // 2, GRID_W // 2)
        used: Set[Pos] = set()
        cars: List[Car] = []
        player_goal: Pos = layout["player_goal"]  # type: ignore[assignment]
        parking_slots: List[Pos] = list(layout["parking_slots"])  # type: ignore[arg-type]
        spawn_zone: List[Pos] = list(layout["spawn_zone"])  # type: ignore[arg-type]
        ai_goals = [slot for slot in parking_slots if slot != player_goal]

        player_pos = random_road_cell(grid, rng, used, candidates=spawn_zone)
        used.add(player_pos)
        cars.append(Car(pos=player_pos, target=player_goal, is_player=True, color=USER_COLOR, policy="player"))
        used.add(player_goal)

        for i in range(CARS_TOTAL - 1):
            p = random_road_cell(grid, rng, used, candidates=spawn_zone)
            used.add(p)
            is_support = i == (CARS_TOTAL - 2)
            is_yield = i == 2 and not is_support  # This car is rendered as A3.
            t: Optional[Pos] = None if is_support else (ai_goals[i % len(ai_goals)] if ai_goals else player_goal)
            if t == center:
                non_center_slots = [slot for slot in parking_slots if slot != center]
                t = non_center_slots[i % len(non_center_slots)] if non_center_slots else None
            cars.append(
                Car(
                    pos=p,
                    target=t,
                    is_player=False,
                    color=AI_COLORS[i % len(AI_COLORS)],
                    policy="support" if is_support else ("yield" if is_yield else "bfs"),
                )
            )
            if t is not None:
                used.add(t)

        mode = "optimized"
        logs: deque[str] = deque(maxlen=4)
        logs.append("Turn-based mode: AI cars move when you move.")
        logs.append("AI policy: BFS with every 3rd random step; support car clears lanes.")
        logs.append("Space stalls your turn.")
        return grid, cars, mode, logs, layout

    grid, cars, ai_mode, logs, layout = reset_world()
    intersection_center: Pos = (GRID_H // 2, GRID_W // 2)
    final_intersection: Pos = layout["final_intersection"]  # type: ignore[assignment]
    gate_zone: Set[Pos] = set(layout["gate_zone"])  # type: ignore[arg-type]
    intersection_priority: Optional[int] = None  # 0=N, 1=E, 2=S, 3=W
    intersection_waiting: Set[int] = set()
    report_open = False
    report_lines: List[str] = []
    incident_history: deque[str] = deque(maxlen=200)
    incident_count = 0
    report_close_rect = pygame.Rect(0, 0, 0, 0)
    report_ready = False

    def log_incident(title: str, details: str) -> None:
        nonlocal incident_count
        incident_count += 1
        incident_history.appendleft(f"#{incident_count}: {title} - {details}")

    def build_final_report() -> None:
        nonlocal report_open, report_lines, report_ready
        if report_ready:
            return
        report_ready = True
        report_lines = [
            "Simulation Incident Report",
            f"Total incidents logged: {incident_count}",
            f"Mode: {ai_mode}",
            "Close with X when done reviewing.",
        ]
        report_open = True

    def refresh_live_report() -> None:
        nonlocal report_lines
        report_lines = [
            "Live Incident Report",
            f"Incidents so far: {incident_count}",
            f"Mode: {ai_mode}",
            "Press X to close/open this report.",
        ]

    def approach_dir(pos: Pos) -> Optional[int]:
        r, c = pos
        cr, cc = intersection_center
        if (r, c) == (cr - 1, cc):
            return 0
        if (r, c) == (cr, cc + 1):
            return 1
        if (r, c) == (cr + 1, cc):
            return 2
        if (r, c) == (cr, cc - 1):
            return 3
        return None

    def can_enter_intersection(from_pos: Pos, to_pos: Pos, occupied: Set[Pos]) -> bool:
        nonlocal intersection_priority
        if to_pos != intersection_center:
            return True
        direction = approach_dir(from_pos)
        if direction is None:
            return True
        if intersection_center in occupied:
            intersection_waiting.add(direction)
            return False

        active_dirs = set(intersection_waiting)
        active_dirs.add(direction)
        if intersection_priority is None:
            intersection_priority = direction
        else:
            for _ in range(4):
                if intersection_priority in active_dirs:
                    break
                intersection_priority = (intersection_priority + 1) % 4

        if direction != intersection_priority:
            intersection_waiting.add(direction)
            return False

        intersection_waiting.discard(direction)
        intersection_priority = (direction + 1) % 4
        return True

    def cleanup_intersection_state() -> None:
        nonlocal intersection_priority
        cr, cc = intersection_center
        occupied = {c.pos for c in cars}
        occupied_approaches = {
            d
            for d, cell in enumerate(((cr - 1, cc), (cr, cc + 1), (cr + 1, cc), (cr, cc - 1)))
            if cell in occupied
        }
        intersection_waiting.intersection_update(occupied_approaches)
        if intersection_center not in occupied and not intersection_waiting:
            intersection_priority = None

    def try_player_move(dr: int, dc: int) -> bool:
        player = cars[0]
        nr, nc = player.pos[0] + dr, player.pos[1] + dc
        if not in_bounds(nr, nc) or grid[nr][nc] != ROAD:
            return False
        occupied_now = {c.pos for c in cars}
        if not can_enter_intersection(player.pos, (nr, nc), occupied_now):
            logs.append("4-way hold: waiting right-of-way.")
            return False
        occupied = {c.pos for c in cars[1:]}
        if (nr, nc) in occupied:
            blocker = next((f"A{i}" for i, c in enumerate(cars[1:], start=1) if c.pos == (nr, nc)), "AI")
            log_incident("Intersection/road conflict", f"P attempted occupied tile at {(nr, nc)} by {blocker}.")
            return False
        player.pos = (nr, nc)
        cleanup_intersection_state()
        return True

    accomplished = False
    stagnant_turns = 0
    last_positions_key: Tuple[Pos, ...] = tuple(c.pos for c in cars)

    def all_cars_at_targets() -> bool:
        tracked = [car for car in cars if car.policy in ("player", "bfs")]
        return all(car.target is not None and car.pos == car.target for car in tracked)

    def player_arrived() -> bool:
        return cars[0].target is not None and cars[0].pos == cars[0].target

    def retreat_west_if_needed(car: Car, occupied: Set[Pos]) -> Pos:
        """Move AI out of the player-only approach lane before player arrival."""
        opts = [n for n in neighbors4(grid, car.pos[0], car.pos[1]) if n not in occupied]
        if not opts:
            return car.pos
        # Prefer moving to smaller columns (west), then away from center row.
        cr, _ = intersection_center
        opts.sort(key=lambda p: (p[1], abs(p[0] - cr)))
        best = opts[0]
        if best[1] < car.pos[1]:
            return best
        return car.pos

    def to_logical_pos(pos: Pos) -> Pos:
        sw, sh = screen.get_size()
        if sw <= 0 or sh <= 0:
            return pos
        lx = int(pos[0] * logical_w / sw)
        ly = int(pos[1] * logical_h / sh)
        return lx, ly

    def force_unstick_ai() -> bool:
        """Resolve prolonged stalls by nudging one AI to a safe alternate tile."""
        occupied = {c.pos for c in cars}
        cr, cc = intersection_center
        player_done = player_arrived()

        candidates = [car for car in cars[1:] if car.policy in ("bfs", "yield")]
        candidates.sort(key=lambda car: abs(car.pos[0] - cr) + abs(car.pos[1] - cc))

        for car in candidates:
            options = [n for n in neighbors4(grid, car.pos[0], car.pos[1]) if n not in occupied]
            if not options:
                continue

            ranked: List[Tuple[Tuple[int, int, int], Pos]] = []
            for nxt in options:
                if (not player_done) and nxt in gate_zone:
                    continue
                if nxt == final_intersection and car.policy == "support":
                    continue
                if not can_enter_intersection(car.pos, nxt, occupied):
                    continue

                future_open = sum(1 for nn in neighbors4(grid, nxt[0], nxt[1]) if nn not in occupied or nn == car.pos)
                dist_center = abs(nxt[0] - cr) + abs(nxt[1] - cc)
                west_bias = -nxt[1]
                ranked.append(((future_open, dist_center, west_bias), nxt))

            if not ranked:
                continue

            ranked.sort(reverse=True)
            chosen = ranked[0][1]
            occupied.discard(car.pos)
            occupied.add(chosen)
            car.pos = chosen
            cleanup_intersection_state()
            logs.append("Anti-deadlock: nudged one AI car to restore traffic flow.")
            return True

        return False

    def step_player_god_mode() -> bool:
        player = cars[0]
        if player.target is None or player.pos == player.target:
            return False
        occupied = {c.pos for c in cars[1:]}
        path = bfs_path(grid, player.pos, player.target, blocked=occupied)
        if not path or len(path) < 2:
            logs.append("God mode: no safe player route this turn.")
            return False
        nxt = path[1]
        occupied_now = {c.pos for c in cars}
        if not can_enter_intersection(player.pos, nxt, occupied_now):
            logs.append("God mode: player waiting for 4-way priority.")
            return False
        if nxt in occupied:
            logs.append("God mode: next tile occupied; waiting.")
            return False
        player.pos = nxt
        cleanup_intersection_state()
        return True

    def run_turn(player_moved: bool) -> None:
        nonlocal ai_mode
        nonlocal accomplished
        nonlocal stagnant_turns
        nonlocal last_positions_key
        player = cars[0]

        all_positions = {c.pos for c in cars}
        ai_moved = False
        for idx, car in enumerate(cars[1:], start=1):
            prev_pos = car.pos
            next_pos = step_ai_car(
                grid,
                car,
                all_positions,
                god_mode=(ai_mode == "god"),
                intersection_center=intersection_center,
            )
            if car.pos == intersection_center:
                # Hard center-clear rule: never hold center if any side/west exit is free.
                if next_pos == car.pos:
                    forced_exits = [
                        (intersection_center[0] - 1, intersection_center[1]),  # north
                        (intersection_center[0] + 1, intersection_center[1]),  # south
                        (intersection_center[0], intersection_center[1] - 1),  # west
                        (intersection_center[0], intersection_center[1] + 1),  # east fallback
                    ]
                    for ex in forced_exits:
                        if in_bounds(*ex) and grid[ex[0]][ex[1]] == ROAD and ex not in all_positions:
                            next_pos = ex
                            break
            if car.policy == "support":
                # Keep non-goal cars from clogging the final approach.
                if next_pos in gate_zone or next_pos == final_intersection:
                    next_pos = car.pos
            if car.pos != intersection_center and (not player_arrived()) and car.policy == "bfs":
                # Reserve eastbound corridor for player until player reaches parking.
                if car.pos[1] > intersection_center[1]:
                    next_pos = retreat_west_if_needed(car, all_positions)
                elif next_pos[1] > intersection_center[1]:
                    next_pos = car.pos
                if next_pos in gate_zone:
                    next_pos = car.pos
            if next_pos != car.pos and not can_enter_intersection(car.pos, next_pos, all_positions):
                next_pos = car.pos
            if next_pos != car.pos and next_pos in all_positions:
                log_incident("AI conflict avoided", f"A{idx} attempted occupied tile at {next_pos}.")
                next_pos = car.pos
            all_positions.discard(car.pos)
            all_positions.add(next_pos)
            car.pos = next_pos
            if car.pos != prev_pos:
                ai_moved = True
        cleanup_intersection_state()
        if not player_moved:
            logs.append("Stall turn: you skipped movement.")

        current_key: Tuple[Pos, ...] = tuple(c.pos for c in cars)
        if current_key == last_positions_key and (not player_moved) and (not ai_moved):
            stagnant_turns += 1
        else:
            stagnant_turns = 0
            last_positions_key = current_key

        if stagnant_turns >= 5 and not accomplished:
            if force_unstick_ai():
                stagnant_turns = 0
                last_positions_key = tuple(c.pos for c in cars)

        if all_cars_at_targets():
            accomplished = True
            logs.append("ACCOMPLISHED: all cars reached correct locations.")
            build_final_report()

    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                logical_mouse = to_logical_pos(event.pos)
                if report_open and report_close_rect.collidepoint(logical_mouse):
                    report_open = False
            elif event.type == pygame.KEYDOWN:
                moved = False
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    grid, cars, ai_mode, logs, layout = reset_world()
                    accomplished = False
                    stagnant_turns = 0
                    last_positions_key = tuple(c.pos for c in cars)
                    final_intersection = layout["final_intersection"]  # type: ignore[assignment]
                    gate_zone = set(layout["gate_zone"])  # type: ignore[arg-type]
                    intersection_priority = None
                    intersection_waiting.clear()
                    report_open = False
                    report_ready = False
                elif event.key in (pygame.K_g, pygame.K_m):
                    ai_mode = "god" if ai_mode == "optimized" else "optimized"
                    logs.append(f"AI mode -> {ai_mode}")
                elif event.key == pygame.K_x:
                    if report_open:
                        report_open = False
                    else:
                        if not accomplished:
                            refresh_live_report()
                        report_open = True
                elif event.key == pygame.K_SPACE and not accomplished:
                    if ai_mode == "god":
                        moved = step_player_god_mode()
                        run_turn(player_moved=moved)
                    else:
                        run_turn(player_moved=False)
                elif event.key in (pygame.K_UP, pygame.K_w) and not accomplished:
                    moved = try_player_move(-1, 0)
                elif event.key in (pygame.K_DOWN, pygame.K_s) and not accomplished:
                    moved = try_player_move(1, 0)
                elif event.key in (pygame.K_LEFT, pygame.K_a) and not accomplished:
                    moved = try_player_move(0, -1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d) and not accomplished:
                    moved = try_player_move(0, 1)

                if moved:
                    run_turn(player_moved=True)

        canvas.fill(BG)
        for r in range(GRID_H):
            for c in range(GRID_W):
                rect = pygame.Rect(c * CELL, r * CELL, CELL, CELL)
                color = ROAD_COLOR if grid[r][c] == ROAD else WALL_COLOR
                pygame.draw.rect(canvas, color, rect)
                pygame.draw.rect(canvas, GRID_LINE, rect, 1)

        cr, cc = intersection_center
        center_px = (cc * CELL + CELL // 2, cr * CELL + CELL // 2)
        pygame.draw.circle(canvas, (255, 220, 120), center_px, max(5, CELL // 6), 2)
        dir_cells = [(cr - 1, cc), (cr, cc + 1), (cr + 1, cc), (cr, cc - 1)]
        dir_labels = ["N", "E", "S", "W"]
        for d, (rr, rc) in enumerate(dir_cells):
            highlight = d == intersection_priority
            col = (255, 235, 130) if highlight else (170, 176, 190)
            txt = small.render(dir_labels[d], True, col)
            canvas.blit(txt, (rc * CELL + CELL // 3, rr * CELL + CELL // 3))

        for idx, car in enumerate(cars):
            if car.target is not None:
                tr, tc = car.target
                marker_color = (255, 150, 120) if car.is_player else TARGET_COLOR
                pygame.draw.circle(
                    canvas,
                    marker_color,
                    (tc * CELL + CELL // 2, tr * CELL + CELL // 2),
                    max(4, CELL // 8),
                    1,
                )
            rr, cc = car.pos
            pygame.draw.circle(
                canvas,
                car.color,
                (cc * CELL + CELL // 2, rr * CELL + CELL // 2),
                max(7, CELL // 3),
            )
            label = "P" if idx == 0 else f"A{idx}"
            text = small.render(label, True, (20, 20, 20))
            canvas.blit(text, (cc * CELL + CELL // 3, rr * CELL + CELL // 4))

        hud_y = GRID_H * CELL + 8
        bfs_count = sum(1 for c in cars[1:] if c.policy == "bfs")
        support_count = sum(1 for c in cars[1:] if c.policy == "support")
        hud_text = (
            f"Mode: {ai_mode} | Cars: {len(cars)} | BFS AI: {bfs_count} | Support AI: {support_count}"
        )
        canvas.blit(font.render(hud_text, True, (230, 232, 240)), (8, hud_y))
        canvas.blit(
            small.render("Controls: WASD/Arrows move, Space stall, G god-mode, X report, R reset", True, (190, 198, 214)),
            (8, hud_y + 20),
        )
        if ai_mode == "god":
            canvas.blit(small.render("God mode: Space auto-steps player via BFS route.", True, (200, 210, 226)), (8, hud_y + 52))
        gate_msg = "AI hold at final intersection until player reaches parking lot."
        canvas.blit(small.render(gate_msg, True, (190, 198, 214)), (8, hud_y + 36))
        if accomplished:
            msg = "GAME ACCOMPLISHED - all cars at correct locations (press R to play again)"
            done_y = 70 if ai_mode == "god" else 54
            canvas.blit(small.render(msg, True, (120, 255, 170)), (8, hud_y + done_y))
        for i, ln in enumerate(logs):
            base_offset = 88 if ai_mode == "god" else 72
            offset = base_offset if accomplished else (base_offset - 16)
            canvas.blit(small.render(ln, True, (180, 190, 210)), (8, hud_y + offset + i * 16))

        if report_open:
            panel_w = GRID_W * CELL - 120
            panel_h = 300
            panel_x = 60
            panel_y = 70
            panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            pygame.draw.rect(canvas, (18, 22, 32), panel, border_radius=8)
            pygame.draw.rect(canvas, (230, 130, 130), panel, 2, border_radius=8)
            report_close_rect = pygame.Rect(panel.right - 34, panel.y + 8, 24, 24)
            pygame.draw.rect(canvas, (120, 48, 48), report_close_rect, border_radius=4)
            pygame.draw.rect(canvas, (230, 170, 170), report_close_rect, 1, border_radius=4)
            x_txt = font.render("X", True, (255, 230, 230))
            canvas.blit(x_txt, (report_close_rect.x + 5, report_close_rect.y + 1))
            for i, line in enumerate(report_lines):
                color = (255, 210, 210) if i == 0 else (220, 225, 235)
                canvas.blit(font.render(line, True, color), (panel.x + 14, panel.y + 14 + i * 28))
            canvas.blit(small.render("Session incident history (newest first):", True, (210, 216, 230)), (panel.x + 14, panel.y + 128))
            recent = list(incident_history)[:7]
            for i, item in enumerate(recent):
                canvas.blit(small.render(item, True, (195, 202, 218)), (panel.x + 14, panel.y + 148 + i * 18))

        if canvas is not screen:
            scaled = pygame.transform.smoothscale(canvas, screen.get_size())
            screen.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
