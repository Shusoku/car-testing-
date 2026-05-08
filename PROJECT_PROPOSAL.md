# Final (Signature) Project Proposal

**Fill in bracketed placeholders before submission.**

---

## 1. Cover Page

| | |
|--|--|
| **Project Title** | Interactive Maze Exploration with Multi-Algorithm Path Planning and Turn-Based Combat |
| **Student Name(s)** | [Your name(s)] |
| **Course Name & Code** | [e.g., CS 455 – Course title] |
| **Instructor Name** | [Instructor name] |
| **Institution Name** | [Institution] |
| **Submission Date** | [Date] |

---

## 2. Project Overview / Abstract (150–250 words)

Exploring and escaping procedurally generated mazes is a classic planning and search problem, yet many classroom demos either show algorithms in isolation or use a passive visualizer. This project addresses the gap between **abstract graph search** and **playable experience** by combining a shared maze core, four path planners, and a real-time Pygame front end with fog of war, collectibles, and combat.

The problem is to let a player (or an automated “god mode”) navigate an unknown maze, gather keys to unlock an exit, avoid or fight enemies, and **compare path-planning behaviors** (BFS, DFS, A*, and RRT adapted to a grid) on the same layout. The proposed solution is a modular architecture: `maze_core` for generation and geometry; separate solver modules with a common interface; and `maze_game` for rendering, input, inventory, and integration with a turn-based battle layer derived from structured attack trees.

Expected outcomes include a **working game prototype** with configurable maze sizes (including large custom dimensions), overlay paths from each solver, optional autopilot that prioritizes collecting all keys, and **documented deliverables** (code, proposal, final report, presentation, testing notes). The work demonstrates applied algorithms, software design, and measurable evaluation of solver paths and playability.

*(Word count for the abstract paragraph above: within 150–250 words — trim if your course requires a strict count.)*

---

## 3. Problem Statement

**Description:** Players and instructors need a unified environment where **maze generation, visibility-limited exploration, resource collection, and combat** coexist with **reproducible path-planning comparisons**. Pure solvers do not show gameplay friction; pure games rarely expose BFS vs A* on identical graphs.

**Importance:** Search and planning are central to robotics and games. Connecting theory to an interactive maze clarifies optimality, completeness, and trade-offs under obstacles and partial information.

**Who is affected:** Students learning AI/search; anyone evaluating planner behavior in grid worlds; future extension to coursework demos.

**Limitations / gaps:** Commercial games rarely open four algorithms side-by-side on one maze; many academic assignments omit real-time UX, fog of war, or structured combat rules.

---

## 4. Project Objectives

**Main goal:** Deliver a playable maze application that integrates **multiple search algorithms** with a coherent game loop and clear documentation.

**Specific objectives:**

1. **Develop a functional prototype** of a grid maze with procedural generation, keys, exit gating, chests, and enemy encounters.
2. **Implement and compare** BFS, DFS, A*, and RRT-style planning on the same grid API; visualize paths in-game.
3. **Design and implement** a side panel UI, fog of war, god-mode autopilot (keys-first, then exit), and a pauseable inventory with optional stats panel.
4. **Integrate** a turn-based combat subsystem using attack/defend trees and effect logic (CPU vs player).
5. **Analyze performance** of solvers (path length, runtime where measured) and document test scenarios for regression after changes.
6. **Support scalable maze dimensions** (CLI presets and custom `--cols` / `--rows` within safe bounds).

---

## 5. Scope of the Project

### In scope

- Shared maze generation and `Maze` wrapper; corner-goal and key/chest placement.
- Solvers: BFS, DFS, A*, RRT (grid path with optional densification).
- Pygame application: movement, fullscreen, legend, solver hotkeys (1–4), regeneration.
- Features: fog/exploration, monsters, battle overlay, inventory (WASD slots, Tab stats), god mode.
- Documentation: proposal, README-level usage, final report, presentation slides (to be produced).
- Basic manual testing and notes on breaking grid sizes or edge cases.

### Out of scope

- Multiplayer networking; mobile builds; 3D graphics.
- Full RL or learning-based opponents; extensive narrative or level design beyond procedural mazes.
- Formal user study or institutional IRB process unless course requires it.
- Guaranteeing optimality proofs in code (analysis can be descriptive).
- Production-grade art, audio, or localization.

---

## 6. Literature Review / Background (if required)

**Related work:** Maze generation via recursive backtracking / flood carve; classic graph search (BFS/DFS/A*); sampling-based planning (RRT/RRT* concepts) adapted discretely for grid comparison.

**Existing solutions:** Separate educational applets (pathfinding demos), roguelikes without exposed multi-solver APIs, and assignment-only scripts without a unified game shell.

**Technologies:** Python 3, Pygame, standard library (`heapq` for A*, random seeds for reproducibility).

**Research gap bridged (project level):** A **single codebase** where the same grid feeds solvers, visualization, and gameplay constraints (fog, combat pause, inventory), making trade-offs tangible.

---

## 7. Proposed Methodology

**Approach:** Iterative development — core grid → solvers → Pygame shell → features (combat, inventory, scalability) → testing and documentation.

**Tools:** Python, Pygame, Git; optional plotting from solver experiments (`part2` / RRT save path if used).

**Architecture (high level):**

- **Data / logic:** `maze_core` (generation, neighbors, goals, dimension clamping).
- **Algorithms:** `BFS_mazesolving`, `DFS_mazesolving`, `astar_mazesolving`, `RRT_mazesolving`.
- **Game:** `maze_game` (loop, UI, state); `maze_battle` (attack trees, turn resolution).
- **Integration:** `part2` or CLI entry points call shared APIs.

**Design steps:** Specify interfaces (`solve(grid, start, goal)` pattern); keep maze grid convention `(row, col)` consistent; separate rendering from pure search; use seeds for reproducible demos.

**Data collection (if applicable):** Log path lengths and wall-clock time for solver calls on fixed seeds; optional CSV export (stretch).

---

## 8. Expected Deliverables

| Deliverable | Description |
|-------------|-------------|
| **Software** | Runnable maze game (`maze_game.py`), core and solver modules, `requirements.txt`. |
| **Documentation** | This proposal; user-oriented usage (how to run, key bindings); architecture diagram or section in final report. |
| **Presentation** | Slide deck summarizing problem, design, demo, results. |
| **Final report** | Expanded methodology, results, reflection, limitations. |
| **Testing results** | Checklist or short log: small/large mazes, each solver, battle flow, god mode, inventory pause. |

---

## 9. Timeline / Project Plan

*Adjust dates to your academic calendar.*

| Phase | Task | Duration | Deadline |
|-------|------|----------|----------|
| Phase 1 | Research & requirements; finalize proposal | 1 week | [Date] |
| Phase 2 | Core maze + all solvers + flags stable | 2 weeks | [Date] |
| Phase 3 | Pygame UX: fog, panel, keys, monsters, battle, inventory | 3 weeks | [Date] |
| Phase 4 | Testing, bug fixes, scalability & performance checks | 1 week | [Date] |
| Phase 5 | Final report, slides, polish, submission | 1 week | [Date] |

---

## 10. Resources Required

- **Software:** Python 3.x, Pygame (`pip install -r requirements.txt`), Git, IDE or editor.
- **Hardware:** PC with display; sufficient RAM for large grids (upper bound enforced in code).
- **Datasets:** None required (procedural mazes); optional saved seeds for demos.
- **Research materials:** Course notes on search; optional readings on RRT/A*.

---

## 11. Risk Analysis (Optional but Recommended)

| Risk | Mitigation |
|------|------------|
| Time overrun on UI/combat | Weekly milestones; freeze features before report week. |
| Algorithm correctness / coordinate bugs | Unit-style checks on tiny mazes; consistent `(row,col)` convention. |
| Large maze performance | Dimension caps; fullscreen tile scaling; profile hot paths if needed. |
| Scope creep | Strict in/out of scope list; defer multiplayer / 3D. |

---

## 12. Evaluation Criteria

**Success measures:**

- Game runs from clean clone + `pip install -r requirements.txt`.
- All four solvers produce valid paths (or documented failure) on test grids.
- Player can win: collect keys, reach exit; combat resolves without softlocks.
- God mode collects keys then exits; inventory pauses simulation.
- Documentation allows instructor/peer to reproduce key scenarios.

**Metrics (examples):** Path length vs Manhattan lower bound where applicable; solver wall time for fixed `--seed` and `--cols`/`--rows`; manual pass/fail checklist.

**Testing methods:** Manual exploratory testing; scripted runs with `--seed`; regression after refactors.

---

## 13. Conclusion

This project matters because it **grounds classical search and planning in an interactive system** that students and reviewers can experience directly rather than only inspect pseudocode. The expected impact is clearer intuition for BFS vs DFS vs A* vs sampling-based approaches, plus a reusable codebase for demos and future extensions (new enemies, planners, or evaluation harnesses). The work is justified by its **integration breadth** (algorithms + UX + evaluation) appropriate for a capstone or signature project in computing.

---

*End of proposal draft.*
