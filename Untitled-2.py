import random

WIDTH = 7
HEIGHT = 7

maze = [[1 for _ in range(WIDTH)] for _ in range(HEIGHT)]
DIRS = [(0,1), (0,-1), (1,0), (-1,0)]

def in_bounds(x, y):
    return 0 <= x < WIDTH and 0 <= y < HEIGHT

def flood_maze_iterative(start_x, start_y):
    stack = [(start_x, start_y)]
    maze[start_y][start_x] = 0

    while stack:
        x, y = stack[-1]
        dirs = DIRS[:]
        random.shuffle(dirs)

        carved = False

        for dx, dy in dirs:
            nx, ny = x + dx * 2, y + dy * 2

            # Check bounds BEFORE touching maze[ny][nx]
            if in_bounds(nx, ny) and maze[ny][nx] == 1:
                # Knock down wall
                maze[y + dy][x + dx] = 0
                maze[ny][nx] = 0

                stack.append((nx, ny))
                carved = True
                break

        if not carved:
            stack.pop()

def print_maze():
    for row in maze:
        print("".join("█" if cell == 1 else " " for cell in row))

flood_maze_iterative(0, 0)
print_maze()
