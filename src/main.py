import pygame
import random
import sys

# --- CONFIGURATION ---
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TILE_SIZE = 32
FPS = 60

# Colors
COLOR_GROUND = (34, 139, 34)   # Green
COLOR_WATER = (0, 119, 190)    # Blue
COLOR_SKY_BG = (10, 10, 50)    # Dark Blue/Space
COLOR_ROCK = (100, 100, 100)
COLOR_TREE = (0, 100, 0)
COLOR_SATELLITE = (200, 200, 0)
COLOR_MACHINE = (150, 50, 50)
COLOR_PLAYER = (255, 255, 255)
COLOR_UI_BG = (50, 50, 50, 200)

# --- CLASSES ---

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.x + int(SCREEN_WIDTH / 2)
        y = -target.rect.y + int(SCREEN_HEIGHT / 2)
        
        # Limit scrolling to map size
        x = min(0, max(-(self.width - SCREEN_WIDTH), x))
        y = min(0, max(-(self.height - SCREEN_HEIGHT), y))
        
        self.camera = pygame.Rect(x, y, self.width, self.height)

class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, tile_type, group):
        super().__init__(group)
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.tile_type = tile_type
        
        if tile_type == 'grass':
            self.image.fill(COLOR_GROUND)
        elif tile_type == 'water':
            self.image.fill(COLOR_WATER)
            
        self.rect = self.image.get_rect()
        self.rect.x = x * TILE_SIZE
        self.rect.y = y * TILE_SIZE

class Resource(pygame.sprite.Sprite):
    def __init__(self, x, y, res_type, group):
        super().__init__(group)
        self.res_type = res_type
        self.image = pygame.Surface((TILE_SIZE - 8, TILE_SIZE - 8))
        
        if res_type == 'rock':
            self.image.fill(COLOR_ROCK)
            self.yield_item = 'stone'
        elif res_type == 'tree':
            self.image.fill(COLOR_TREE)
            self.yield_item = 'wood'
            
        self.rect = self.image.get_rect()
        self.rect.x = x * TILE_SIZE + 4
        self.rect.y = y * TILE_SIZE + 4

class Building(pygame.sprite.Sprite):
    def __init__(self, x, y, b_type, group):
        super().__init__(group)
        self.b_type = b_type
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        
        if b_type == 'furnace':
            self.image.fill(COLOR_MACHINE)
            # Draw distinct detail
            pygame.draw.circle(self.image, (0, 0, 0), (TILE_SIZE//2, TILE_SIZE//2), 5)
        elif b_type == 'solar_panel':
            self.image.fill((0, 0, 150))
            pygame.draw.rect(self.image, (200, 200, 255), (4, 4, 24, 24))

        self.rect = self.image.get_rect()
        self.rect.x = x * TILE_SIZE
        self.rect.y = y * TILE_SIZE

class Satellite(pygame.sprite.Sprite):
    def __init__(self, x, y, s_type, group):
        super().__init__(group)
        self.s_type = s_type
        self.image = pygame.Surface((48, 48))
        self.image.fill(COLOR_SATELLITE)
        pygame.draw.line(self.image, (0,0,0), (0,24), (48,24), 2)
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vx = random.choice([-1, 1]) * random.uniform(0.5, 2)
        self.vy = random.choice([-1, 1]) * random.uniform(0.5, 2)

    def update(self):
        # Bounce around in space view
        self.rect.x += self.vx
        self.rect.y += self.vy
        
        if self.rect.left < 0 or self.rect.right > 2000: # Virtual space bounds
            self.vx *= -1
        if self.rect.top < 0 or self.rect.bottom > 2000:
            self.vy *= -1

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, group):
        super().__init__(group)
        self.image = pygame.Surface((24, 24))
        self.image.fill(COLOR_PLAYER)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 5
        self.inventory = {'wood': 0, 'stone': 0, 'iron': 0}

    def move(self, dx, dy, width, height):
        self.rect.x += dx * self.speed
        self.rect.y += dy * self.speed
        
        # Keep player in bounds
        self.rect.x = max(0, min(self.rect.x, width - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, height - self.rect.height))

class GameState:
    def __init__(self):
        self.role = 'GROUND' # 'GROUND' or 'SKY'
        self.global_energy = 0
        self.global_heat = 0 # Sky player manages this
        self.messages = []

    def add_message(self, text):
        self.messages.append((text, 120)) # Text, timer frames

    def update_messages(self):
        self.messages = [(txt, time-1) for txt, time in self.messages if time > 0]

# --- MAIN GAME CLASS ---

class TerraSkyGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("TerraSky: Prototype")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        
        self.map_width = 2048
        self.map_height = 2048
        
        # Groups
        self.all_sprites = pygame.sprite.Group()
        self.tiles = pygame.sprite.Group()
        self.resources = pygame.sprite.Group()
        self.buildings = pygame.sprite.Group()
        self.satellites = pygame.sprite.Group()
        
        # Initialization
        self.generate_world()
        self.player = Player(self.map_width//2, self.map_height//2, self.all_sprites)
        self.camera = Camera(self.map_width, self.map_height)
        self.state = GameState()
        
        # Pre-spawn some satellites
        for _ in range(3):
            Satellite(random.randint(0, 1000), random.randint(0, 1000), 'comm', self.satellites)

    def generate_world(self):
        # Simple noise generation simulation
        for x in range(0, self.map_width // TILE_SIZE):
            for y in range(0, self.map_height // TILE_SIZE):
                t_type = 'grass'
                if random.random() < 0.1:
                    t_type = 'water'
                
                Tile(x, y, t_type, self.tiles)
                
                # Spawn resources on grass
                if t_type == 'grass':
                    r = random.random()
                    if r < 0.05:
                        Resource(x, y, 'rock', self.resources)
                    elif r < 0.1:
                        Resource(x, y, 'tree', self.resources)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                # Toggle Role
                if event.key == pygame.K_TAB:
                    if self.state.role == 'GROUND':
                        self.state.role = 'SKY'
                        self.state.add_message("Switched to SKY ORBIT")
                    else:
                        self.state.role = 'GROUND'
                        self.state.add_message("Switched to GROUND CONTROL")

                # Action Button
                if event.key == pygame.K_SPACE and self.state.role == 'GROUND':
                    self.interact_ground()
                
                if event.key == pygame.K_e and self.state.role == 'GROUND':
                    self.build_structure('furnace')

                if event.key == pygame.K_e and self.state.role == 'SKY':
                    self.launch_satellite()

        # Continuous movement
        if self.state.role == 'GROUND':
            dx, dy = 0, 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]: dy = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy = 1
            self.player.move(dx, dy, self.map_width, self.map_height)
        
        elif self.state.role == 'SKY':
            # Sky camera movement simply moves the view point, not a player char
            pass

    def interact_ground(self):
        # Simple hitbox check for gathering
        hits = pygame.sprite.spritecollide(self.player, self.resources, True)
        for hit in hits:
            self.player.inventory[hit.yield_item] += 1
            self.state.add_message(f"Gathered 1 {hit.yield_item}")

    def build_structure(self, b_type):
        # Check cost
        cost = {'wood': 2, 'stone': 2}
        
        can_build = True
        for res, amount in cost.items():
            if self.player.inventory.get(res, 0) < amount:
                can_build = False
        
        if can_build:
            # Deduct cost
            for res, amount in cost.items():
                self.player.inventory[res] -= amount
            
            # Snap to grid
            grid_x = round(self.player.rect.x / TILE_SIZE)
            grid_y = round(self.player.rect.y / TILE_SIZE)
            
            Building(grid_x, grid_y, b_type, self.buildings)
            self.state.add_message("Built Furnace!")
        else:
            self.state.add_message("Not enough resources (Need 2 Wood, 2 Stone)")

    def launch_satellite(self):
        # Sky player action (Simulated cost)
        if self.state.global_energy >= 10:
            self.state.global_energy -= 10
            # Spawn near center of view
            sx = random.randint(0, SCREEN_WIDTH)
            sy = random.randint(0, SCREEN_HEIGHT)
            Satellite(sx, sy, 'comm', self.satellites)
            self.state.add_message("Satellite Deployed")
        else:
            self.state.add_message("Need 10 Global Energy")

    def update(self):
        self.camera.update(self.player)
        self.satellites.update()
        self.state.update_messages()
        
        # Passive Energy Generation Logic (The "Sim" part)
        # Every 60 frames, generate energy based on satellites
        if pygame.time.get_ticks() % 60 == 0:
            energy_gain = len(self.satellites)
            self.state.global_energy += energy_gain

    def draw_ground_view(self):
        self.screen.fill((0, 0, 0))
        
        # Draw all tiles relative to camera
        for tile in self.tiles:
            self.screen.blit(tile.image, self.camera.apply(tile))
            
        for res in self.resources:
            self.screen.blit(res.image, self.camera.apply(res))
            
        for b in self.buildings:
            self.screen.blit(b.image, self.camera.apply(b))
            
        self.screen.blit(self.player.image, self.camera.apply(self.player))

    def draw_sky_view(self):
        self.screen.fill(COLOR_SKY_BG)
        
        # Draw a "mini-map" representation of the ground below
        map_surface = pygame.Surface((400, 400))
        map_surface.fill(COLOR_GROUND)
        # Draw dots for buildings
        for b in self.buildings:
            bx = (b.rect.x / self.map_width) * 400
            by = (b.rect.y / self.map_height) * 400
            pygame.draw.circle(map_surface, COLOR_MACHINE, (int(bx), int(by)), 3)
            
        map_rect = map_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.screen.blit(map_surface, map_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), map_rect, 2)
        
        # Draw satellites (floating over everything)
        for s in self.satellites:
            self.screen.blit(s.image, s.rect)

    def draw_ui(self):
        # Top Bar
        ui_surf = pygame.Surface((SCREEN_WIDTH, 40), pygame.SRCALPHA)
        ui_surf.fill(COLOR_UI_BG)
        self.screen.blit(ui_surf, (0, 0))
        
        role_txt = self.font.render(f"ROLE: {self.state.role} (Press TAB to Switch)", True, (255, 215, 0))
        self.screen.blit(role_txt, (10, 10))
        
        energy_txt = self.font.render(f"GLOBAL ENERGY: {self.state.global_energy}", True, (0, 255, 255))
        self.screen.blit(energy_txt, (SCREEN_WIDTH - 200, 10))
        
        if self.state.role == 'GROUND':
            inv_text = f"Wood: {self.player.inventory['wood']}  Stone: {self.player.inventory['stone']}"
            inv_surf = self.font.render(inv_text, True, (255, 255, 255))
            self.screen.blit(inv_surf, (10, SCREEN_HEIGHT - 30))
            
            help_txt = self.font.render("WASD: Move | SPACE: Harvest | E: Build Furnace (Cost: 2W, 2S)", True, (200, 200, 200))
            self.screen.blit(help_txt, (10, SCREEN_HEIGHT - 60))
            
        elif self.state.role == 'SKY':
            help_txt = self.font.render("E: Deploy Satellite (Cost: 10 Energy)", True, (200, 200, 200))
            self.screen.blit(help_txt, (10, SCREEN_HEIGHT - 60))

        # Floating Messages
        y_offset = 50
        for msg, _ in self.state.messages:
            txt = self.font.render(msg, True, (255, 255, 255))
            self.screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, y_offset))
            y_offset += 25

    def run(self):
        while True:
            self.handle_input()
            self.update()
            
            if self.state.role == 'GROUND':
                self.draw_ground_view()
            else:
                self.draw_sky_view()
                
            self.draw_ui()
            
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = TerraSkyGame()
    game.run()