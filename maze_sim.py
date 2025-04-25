import pygame
import random
import time
import math

# Инициализация Pygame
pygame.init()

# Константы
WIDTH, HEIGHT = 1000, 800
CELL_SIZE = 40
COLORS = {
    'background': (245, 245, 245),
    'wall': (64, 64, 64),
    'path': (255, 255, 255),
    'exit': (255, 215, 0),
    'panel': (230, 230, 250),
    'panel_border': (180, 180, 180),
    'text': (50, 50, 50),
    'button': (100, 200, 100),
    'button_hover': (120, 220, 120),
    'button_text': (255, 255, 255),
    'white': (255, 255, 255),
    'black': (0, 0, 0),
    'best_path': (255, 182, 193),
    'counter': (70, 130, 180),
    'agents': [
        (255, 99, 71), (50, 205, 50), (70, 130, 180),
        (0, 255, 255), (255, 0, 255)
    ]
}

# Настройки лабиринта
MAZE_WIDTH = 25
MAZE_HEIGHT = 15
ITERATION_DELAY = 0.01
AGENT_SPEED = 1.0


class Camera:
    def __init__(self):
        self.dx = 0
        self.dy = 0
        self.speed = 5
        self.target_dx = 0
        self.target_dy = 0

    def apply(self, rect):
        return rect.move(int(self.dx), int(self.dy))

    def update(self, keys):
        if keys[pygame.K_LEFT]: self.target_dx += self.speed
        if keys[pygame.K_RIGHT]: self.target_dx -= self.speed
        if keys[pygame.K_UP]: self.target_dy += self.speed
        if keys[pygame.K_DOWN]: self.target_dy -= self.speed

        self.dx += (self.target_dx - self.dx) * 0.1
        self.dy += (self.target_dy - self.dy) * 0.1
        self.target_dx *= 0.8
        self.target_dy *= 0.8


class Button:
    def __init__(self, x, y, width, height, text, action):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.hover = False

    def draw(self, surface):
        color = COLORS['button_hover'] if self.hover else COLORS['button']
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, COLORS['panel_border'], self.rect, 2, border_radius=5)

        font = pygame.font.SysFont('Arial', 24)
        text = font.render(self.text, True, COLORS['button_text'])
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(text, text_rect)

    def check_hover(self, pos):
        self.hover = self.rect.collidepoint(pos)
        return self.hover


class Maze:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[1 for _ in range(width)] for _ in range(height)]
        self.generate_maze()
        self.exit_pos = (width - 2, height - 2)
        self.grid[self.exit_pos[1]][self.exit_pos[0]] = 0

    def generate_maze(self):
        stack = [(1, 1)]
        self.grid[1][1] = 0

        while stack:
            x, y = stack[-1]
            directions = []

            possible_dirs = [(-2, 0), (2, 0), (0, -2), (0, 2)]
            random.shuffle(possible_dirs)

            for dx, dy in possible_dirs:
                nx, ny = x + dx, y + dy
                if 0 < nx < self.width - 1 and 0 < ny < self.height - 1 and self.grid[ny][nx] == 1:
                    self.grid[ny][nx] = 0
                    self.grid[y + dy // 2][x + dx // 2] = 0
                    stack.append((nx, ny))
                    break
            else:
                stack.pop()

    def is_wall(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height and self.grid[y][x] == 1

    def is_exit(self, x, y):
        return (x, y) == self.exit_pos


class Environment:
    def __init__(self, maze):
        self.maze = maze
        self.agents = []
        self.iteration = 0
        self.running = False
        self.last_update = 0
        self.shared_knowledge = {
            'visited': set(),
            'dead_ends': set(),
            'best_path': None
        }
        self.finished = False
        self.total_cells = self.calculate_passable_cells()

    def calculate_passable_cells(self):
        count = 0
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                if not self.maze.is_wall(x, y):
                    count += 1
        return count

    def register_agent(self, agent):
        self.agents.append(agent)

    def update(self):
        current_time = time.time()
        if self.running and not self.finished and current_time - self.last_update > ITERATION_DELAY:
            self.iteration += 1
            self.last_update = current_time

            # Обновление знаний перед шагом агентов
            for agent in self.agents:
                if not agent.found_exit:
                    agent.update_shared_knowledge()

            # Движение агентов
            for agent in self.agents:
                if not agent.found_exit:
                    agent.act()

            # Проверка завершения
            self.finished = all(agent.found_exit for agent in self.agents)


class Agent:
    def __init__(self, x, y, color_idx, environment, name):
        self.x = x
        self.y = y
        self.target_x = x
        self.target_y = y
        self.color_idx = color_idx
        self.environment = environment
        self.name = name
        self.found_exit = False
        self.visited = set()
        self.iteration_count = 0
        self.current_path = []
        self.successful_path = None
        environment.register_agent(self)

    def update_shared_knowledge(self):
        current_pos = (int(self.x), int(self.y))
        self.environment.shared_knowledge['visited'].add(current_pos)

        if self.found_exit and not self.environment.shared_knowledge['best_path']:
            self.successful_path = self.current_path.copy()
            self.environment.shared_knowledge['best_path'] = self.successful_path

    def act(self):
        if self.environment.shared_knowledge['best_path']:
            self.follow_best_path()
            return

        if self.found_exit:
            return

        if math.dist((self.x, self.y), (self.target_x, self.target_y)) < 0.1:
            self.iteration_count += 1
            self.x = self.target_x
            self.y = self.target_y

            current_pos = (int(self.x), int(self.y))
            self.current_path.append(current_pos)

            if self.environment.maze.is_exit(int(self.x), int(self.y)):
                self.found_exit = True
                return

            directions = []
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx = int(self.x) + dx
                ny = int(self.y) + dy
                pos = (nx, ny)

                if not self.environment.maze.is_wall(nx, ny):
                    if pos not in self.environment.shared_knowledge['dead_ends']:
                        directions.append((dx, dy))

            if directions:
                dx, dy = random.choice(directions)
                self.target_x = self.x + dx
                self.target_y = self.y + dy
            else:
                self.mark_path_as_dead_end()
        else:
            self.x += (self.target_x - self.x) * AGENT_SPEED
            self.y += (self.target_y - self.y) * AGENT_SPEED

    def mark_path_as_dead_end(self):
        for pos in self.current_path:
            self.environment.shared_knowledge['dead_ends'].add(pos)
        self.current_path = []

    def follow_best_path(self):
        if not self.environment.shared_knowledge['best_path']:
            return

        current_pos = (int(self.x), int(self.y))
        best_path = self.environment.shared_knowledge['best_path']

        if current_pos in best_path:
            idx = best_path.index(current_pos)
            if idx < len(best_path) - 1:
                self.target_x, self.target_y = best_path[idx + 1]
                self.x += (self.target_x - self.x) * AGENT_SPEED
                self.y += (self.target_y - self.y) * AGENT_SPEED
                self.found_exit = (idx + 1 == len(best_path) - 1)


def draw_statistics(surface, agents, env, width):
    panel_height = 160
    panel_rect = pygame.Rect(0, HEIGHT - panel_height, width, panel_height)

    # Фон панели
    pygame.draw.rect(surface, COLORS['panel'], panel_rect)
    pygame.draw.rect(surface, COLORS['panel_border'], panel_rect, 2)

    # Заголовок
    font = pygame.font.SysFont('Arial', 20)
    title = font.render("Статистика агентов", True, COLORS['text'])
    surface.blit(title, (panel_rect.x + 20, panel_rect.y + 15))

    # Разделительная линия
    pygame.draw.line(surface, COLORS['panel_border'],
                     (panel_rect.x + 20, panel_rect.y + 50),
                     (panel_rect.x + panel_rect.width - 20, panel_rect.y + 50), 2)

    # Статистика по агентам
    font = pygame.font.SysFont('Arial', 16)
    for i, agent in enumerate(agents[:3]):
        status = "Финиш" if agent.found_exit else f"{agent.iteration_count} итераций"
        text = f"{agent.name}: {status}"
        agent_text = font.render(text, True, COLORS['agents'][agent.color_idx])
        surface.blit(agent_text, (panel_rect.x + 30, panel_rect.y + 60 + i * 25))

    for i, agent in enumerate(agents[3:]):
        status = "Финиш" if agent.found_exit else f"{agent.iteration_count} итераций"
        text = f"{agent.name}: {status}"
        agent_text = font.render(text, True, COLORS['agents'][agent.color_idx])
        surface.blit(agent_text, (panel_rect.x + width // 2 + 30, panel_rect.y + 60 + i * 25))

    # Прогресс исследования
    progress_text = font.render(
        f"Исследовано клеток лабиринта: {len(env.shared_knowledge['visited'])}/{env.total_cells}",
        True, COLORS['counter']
    )
    surface.blit(progress_text, (panel_rect.x + 530, panel_rect.y + panel_height - 50))

    # Общая статистика
    total_text = font.render(f"Всего итераций: {env.iteration}", True, COLORS['text'])
    surface.blit(total_text, (panel_rect.x + 530, panel_rect.y + panel_height - 25))


def draw_maze(surface, maze, camera, env):
    # Границы лабиринта
    border_rect = pygame.Rect(0, 0, maze.width * CELL_SIZE, maze.height * CELL_SIZE)
    pygame.draw.rect(surface, COLORS['wall'], camera.apply(border_rect), 3)

    # Клетки лабиринта
    for y in range(maze.height):
        for x in range(maze.width):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            adjusted_rect = camera.apply(rect)

            if maze.is_wall(x, y):
                pygame.draw.rect(surface, COLORS['wall'], adjusted_rect)
            else:
                pygame.draw.rect(surface, COLORS['path'], adjusted_rect)

    # Оптимальный путь
    if env.shared_knowledge['best_path']:
        for pos in env.shared_knowledge['best_path']:
            x, y = pos
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            adjusted_rect = camera.apply(rect)
            pygame.draw.rect(surface, COLORS['best_path'], adjusted_rect)

    # Выход
    exit_rect = pygame.Rect(
        maze.exit_pos[0] * CELL_SIZE,
        maze.exit_pos[1] * CELL_SIZE,
        CELL_SIZE,
        CELL_SIZE
    )
    pygame.draw.rect(surface, COLORS['exit'], camera.apply(exit_rect))


def draw_agents(surface, agents, camera):
    for agent in agents:
        if not agent.found_exit:
            x = agent.x * CELL_SIZE + CELL_SIZE // 2
            y = agent.y * CELL_SIZE + CELL_SIZE // 2
            pos = camera.apply(pygame.Rect(0, 0, 0, 0)).move(int(x), int(y))

            # Тело агента
            pygame.draw.circle(surface, COLORS['agents'][agent.color_idx],
                               (pos.x, pos.y), CELL_SIZE // 2 - 2)

            # Глаза
            eye_size = CELL_SIZE // 6
            pygame.draw.circle(surface, COLORS['white'],
                               (pos.x - CELL_SIZE // 6, pos.y - CELL_SIZE // 6), eye_size)
            pygame.draw.circle(surface, COLORS['white'],
                               (pos.x + CELL_SIZE // 6, pos.y - CELL_SIZE // 6), eye_size)
            pygame.draw.circle(surface, COLORS['black'],
                               (pos.x - CELL_SIZE // 6, pos.y - CELL_SIZE // 6), eye_size // 2)
            pygame.draw.circle(surface, COLORS['black'],
                               (pos.x + CELL_SIZE // 6, pos.y - CELL_SIZE // 6), eye_size // 2)


def draw_buttons(surface, buttons):
    for btn in buttons:
        btn.draw(surface)


def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Кооперативный поиск в лабиринте")
    clock = pygame.time.Clock()

    maze = Maze(MAZE_WIDTH, MAZE_HEIGHT)
    env = Environment(maze)
    camera = Camera()

    agents = [
        Agent(1, 1, 0, env, "Красный"),
        Agent(1, 3, 1, env, "Зеленый"),
        Agent(3, 1, 2, env, "Синий"),
        Agent(5, 5, 3, env, "Голубой"),
        Agent(7, 3, 4, env, "Розовый")
    ]

    buttons = [
        Button(20, HEIGHT - 195, 120, 30, "Старт", lambda: setattr(env, 'running', True)),
        Button(160, HEIGHT - 195, 120, 30, "Стоп", lambda: setattr(env, 'running', False))
    ]

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                for btn in buttons:
                    if btn.check_hover(mouse_pos):
                        btn.action()

        # Управление камерой
        keys = pygame.key.get_pressed()
        camera.update(keys)

        # Отрисовка
        screen.fill(COLORS['background'])
        draw_maze(screen, maze, camera, env)
        draw_agents(screen, agents, camera)
        draw_buttons(screen, buttons)
        draw_statistics(screen, agents, env, WIDTH)

        # Обновление логики
        if env.running and not env.finished:
            env.update()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()