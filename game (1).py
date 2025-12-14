import pygame
import random
import math
from collections import deque

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

PLAYER_SPEED = 4
BULLET_SPEED = 10
ENEMY_SPEED_MIN = 1.0
ENEMY_SPEED_MAX = 3.0
SPAWN_INTERVAL = 900
POWERUP_INTERVAL = 12000
POWERUP_DURATION = 6000


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dx=0, dy=-1, speed=BULLET_SPEED, owner='player'):
        super().__init__()
        self.owner = owner
        self.image = pygame.Surface((8, 20), pygame.SRCALPHA)

        pygame.draw.rect(self.image, (255, 240, 80), (2, 0, 4, 18))
        pygame.draw.rect(self.image, (255, 190, 60), (1, 5, 6, 10))
        pygame.draw.ellipse(self.image, (255, 255, 150), (2, -6, 4, 10))

        self.rect = self.image.get_rect(center=(x, y))
        self.vx = dx * speed
        self.vy = dy * speed

    def update(self, dt):
        self.rect.x += self.vx
        self.rect.y += self.vy
        if self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT or self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, speed=None, kind=0):
        super().__init__()
        size = 40 + kind * 10
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.kind = kind

        base_color = (200, 70 + kind * 40, 70)

        pygame.draw.polygon(
            self.image,
            base_color,
            [(size * 0.5, 0), (size, size * 0.9), (0, size * 0.9)]
        )

        pygame.draw.circle(self.image, (255, 255, 255), (int(size * 0.35), int(size * 0.45)), 5)
        pygame.draw.circle(self.image, (255, 255, 255), (int(size * 0.65), int(size * 0.45)), 5)
        pygame.draw.circle(self.image, (0, 0, 0), (int(size * 0.35), int(size * 0.45)), 2)
        pygame.draw.circle(self.image, (0, 0, 0), (int(size * 0.65), int(size * 0.45)), 2)

        outline = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.polygon(
            outline,
            (255, 120, 120, 90),
            [(size * 0.5, 0), (size, size * 0.9), (0, size * 0.9)],
            4
        )
        self.image.blit(outline, (0, 0))

        self.rect = self.image.get_rect(center=(x, y))

        self.speed = speed if speed is not None else random.uniform(ENEMY_SPEED_MIN, ENEMY_SPEED_MAX)
        self.health = 1 + kind
        self.sway = random.uniform(-0.5, 0.5)
        self.angular = random.uniform(0.5, 1.5)

    def update(self, dt, player_pos=None):
        self.rect.y += self.speed * dt
        self.rect.x += math.sin(pygame.time.get_ticks() * 0.001 * self.angular) * self.sway * dt * 2

        if self.kind >= 2 and player_pos is not None:
            px, py = player_pos
            if px < self.rect.centerx:
                self.rect.x -= 0.5 * dt
            else:
                self.rect.x += 0.5 * dt

        if self.rect.top > SCREEN_HEIGHT + 50:
            self.kill()

    def damage(self, amount=1):
        self.health -= amount
        if self.health <= 0:
            self.kill()
            return True
        return False


class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, p_type='rapid'):
        super().__init__()
        self.type = p_type
        self.image = pygame.Surface((26, 26), pygame.SRCALPHA)

        if self.type == 'rapid':
            pygame.draw.circle(self.image, (60, 200, 255), (13, 13), 12)
            pygame.draw.circle(self.image, (255, 255, 255), (13, 13), 6)
        else:
            pygame.draw.circle(self.image, (180, 255, 120), (13, 13), 12)
            pygame.draw.circle(self.image, (80, 120, 60), (13, 13), 6)

        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 1.2

    def update(self, dt):
        self.rect.y += self.speed * dt
        if self.rect.top > SCREEN_HEIGHT + 20:
            self.kill()


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.base_image = pygame.Surface((60, 40), pygame.SRCALPHA)

        pygame.draw.polygon(
            self.base_image,
            (40, 180, 200),
            [(0, 40), (30, 0), (60, 40)]
        )

        pygame.draw.ellipse(
            self.base_image,
            (120, 240, 255),
            (20, 10, 20, 15)
        )

        pygame.draw.rect(
            self.base_image,
            (255, 180, 80, 180),
            (22, 35, 16, 8)
        )
        pygame.draw.rect(
            self.base_image,
            (255, 240, 150, 180),
            (25, 37, 10, 5)
        )

        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(x, y))

        self.speed = PLAYER_SPEED
        self.health = 5
        self.score = 0

        self.fire_delay = 300
        self.last_fire = -9999

        self.powerup = None
        self.powerup_end = 0
        self.shield_active = False
        self.hit_timer = 0

    def move(self, dx, dy, dt):
        self.rect.x += dx * self.speed * dt
        self.rect.y += dy * self.speed * dt

        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(SCREEN_WIDTH, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(SCREEN_HEIGHT, self.rect.bottom)

    def can_fire(self, now):
        return now - self.last_fire >= self.fire_delay

    def fire(self, now, bullets_group, triple=False):
        if not self.can_fire(now):
            return
        self.last_fire = now
        cx, cy = self.rect.center
        if triple:
            bullets_group.add(Bullet(cx, cy - 16, dx=-0.15, dy=-1))
            bullets_group.add(Bullet(cx, cy - 16, dx=0, dy=-1))
            bullets_group.add(Bullet(cx, cy - 16, dx=0.15, dy=-1))
        else:
            bullets_group.add(Bullet(cx, cy - 16, dx=0, dy=-1))

    def apply_powerup(self, p_type, now):
        self.powerup = p_type
        self.powerup_end = now + POWERUP_DURATION
        if p_type == 'rapid':
            self.fire_delay = 120
        elif p_type == 'shield':
            self.shield_active = True

    def update_powerup(self, now):
        if self.powerup and now >= self.powerup_end:
            self.powerup = None
            self.fire_delay = 300
            self.shield_active = False

    def take_hit(self):
        if self.shield_active:
            self.shield_active = False
            self.powerup = None
            self.fire_delay = 300
            return False
        else:
            self.health -= 1
            self.hit_timer = 300
            return True

    def update(self, dt, now):
        if self.hit_timer > 0:
            self.hit_timer -= dt * 1000
            self.image = self.base_image.copy()
            overlay = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 80, 80, 100))
            self.image.blit(overlay, (0, 0))
        else:
            self.image = self.base_image.copy()

        if self.shield_active:
            ring = pygame.Surface((self.rect.width + 12, self.rect.height + 12), pygame.SRCALPHA)
            pygame.draw.ellipse(ring, (180, 255, 120, 120), ring.get_rect(), 4)
            self.image.blit(ring, (-6, -6))


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Pygame 2D Shooter")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.large_font = pygame.font.SysFont("Arial", 36)

        self.player_group = pygame.sprite.GroupSingle()
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.LayeredUpdates()

        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80)
        self.player_group.add(self.player)
        self.all_sprites.add(self.player, layer=2)

        self.running = True
        self.paused = False

        self.last_spawn = pygame.time.get_ticks()
        self.last_powerup = pygame.time.get_ticks()

        self.level = 1
        self.spawn_interval = SPAWN_INTERVAL

        self.dt_factor = 1 / (1000.0 / FPS)

        self.message = deque(maxlen=3)
        self.message_timer = 0

    def spawn_enemy(self):
        x = random.randint(40, SCREEN_WIDTH - 40)
        y = -40
        kind = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
        speed = random.uniform(ENEMY_SPEED_MIN + self.level * 0.1, ENEMY_SPEED_MAX + self.level * 0.2)
        enemy = Enemy(x, y, speed=speed, kind=kind)
        self.enemies.add(enemy)
        self.all_sprites.add(enemy, layer=1)

    def spawn_powerup(self):
        x = random.randint(40, SCREEN_WIDTH - 40)
        y = -20
        p_type = random.choice(['rapid', 'shield'])
        p = PowerUp(x, y, p_type=p_type)
        self.powerups.add(p)
        self.all_sprites.add(p, layer=1)
        self.push_message("Powerup incoming")

    def push_message(self, text, ttl=2500):
        self.message.append((text, pygame.time.get_ticks() + ttl))
        self.message_timer = pygame.time.get_ticks() + ttl

    def handle_collisions(self):
        hits = pygame.sprite.groupcollide(self.enemies, self.bullets, False, True)
        for enemy, bullets in hits.items():
            for b in bullets:
                if enemy.damage(1):
                    self.player.score += 10 + enemy.kind * 5
                    if random.random() < 0.12:
                        p_type = random.choice(['rapid', 'shield'])
                        pu = PowerUp(enemy.rect.centerx, enemy.rect.centery, p_type=p_type)
                        self.powerups.add(pu)
                        self.all_sprites.add(pu, layer=1)

        collided_enemy = pygame.sprite.spritecollideany(self.player, self.enemies)
        if collided_enemy:
            collided_enemy.kill()
            self.player.take_hit()
            if self.player.health <= 0:
                self.running = False

        pu = pygame.sprite.spritecollideany(self.player, self.powerups)
        if pu:
            now = pygame.time.get_ticks()
            self.player.apply_powerup(pu.type, now)
            pu.kill()
            self.push_message("Powerup collected")

    def update(self, dt):
        now = pygame.time.get_ticks()

        if now - self.last_spawn >= self.spawn_interval:
            self.spawn_enemy()
            self.last_spawn = now

        if now - self.last_powerup >= POWERUP_INTERVAL:
            self.spawn_powerup()
            self.last_powerup = now

        for enemy in list(self.enemies):
            enemy.update(dt * self.dt_factor, player_pos=self.player.rect.center)

        self.bullets.update(dt * self.dt_factor)
        self.enemy_bullets.update(dt * self.dt_factor)
        self.powerups.update(dt * self.dt_factor)
        self.player.update(dt * self.dt_factor, now)

        self.handle_collisions()

        self.level = 1 + self.player.score // 200
        self.spawn_interval = max(350, SPAWN_INTERVAL - self.level * 40)

    def draw_hud(self):
        score_surf = self.font.render(f"Score: {self.player.score}", True, (230, 230, 230))
        self.screen.blit(score_surf, (10, 10))

        hp_surf = self.font.render(f"Health: {self.player.health}", True, (230, 230, 230))
        self.screen.blit(hp_surf, (10, 36))

        pu_text = f"Powerup: {self.player.powerup or 'None'}"
        pu_surf = self.font.render(pu_text, True, (230, 230, 230))
        self.screen.blit(pu_surf, (10, 62))

        level_surf = self.font.render(f"Level: {self.level}", True, (230, 230, 230))
        self.screen.blit(level_surf, (SCREEN_WIDTH - 110, 10))

        y = SCREEN_HEIGHT - 26
        for text, expiry in list(self.message):
            if pygame.time.get_ticks() <= expiry:
                msg_surf = self.font.render(text, True, (255, 255, 200))
                self.screen.blit(msg_surf, (10, y))
                y -= 22

    def run(self):
        while self.running:
            dt_ms = self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused

            if self.paused:
                self.screen.fill((30, 30, 30))
                pause_surf = self.large_font.render("Paused", True, (240, 240, 240))
                self.screen.blit(pause_surf, pause_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
                pygame.display.flip()
                continue

            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1

            self.player.move(dx, dy, dt_ms * self.dt_factor)

            now = pygame.time.get_ticks()
            if keys[pygame.K_SPACE]:
                triple = (self.player.powerup == 'rapid' and random.random() < 0.25)
                self.player.fire(now, self.bullets, triple=triple)

            self.update(dt_ms)

            self.screen.fill((12, 12, 30))
            for i in range(40):
                sx = (i * 37 + pygame.time.get_ticks() // 40) % SCREEN_WIDTH
                sy = (i * 53 + pygame.time.get_ticks() // 20) % SCREEN_HEIGHT
                self.screen.set_at((sx, sy), (40, 40, 70))

            for s in self.all_sprites:
                if s.alive():
                    self.screen.blit(s.image, s.rect)

            for b in self.bullets:
                self.screen.blit(b.image, b.rect)

            self.draw_hud()

            if self.player.health <= 0:
                self.running = False

            pygame.display.flip()

        self.game_over_screen()

    def game_over_screen(self):
        self.screen.fill((8, 8, 16))
        go_surf = self.large_font.render("Game Over", True, (240, 120, 120))
        score_surf = self.font.render(f"Final Score: {self.player.score}", True, (230, 230, 230))
        hint_surf = self.font.render("Press Enter to play again or Esc to quit", True, (200, 200, 200))

        self.screen.blit(go_surf, go_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)))
        self.screen.blit(score_surf, score_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)))

        pygame.display.flip()

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.__init__()
                        self.run()
                        waiting = False
                    elif event.key == pygame.K_ESCAPE:
                        waiting = False
            self.clock.tick(30)
        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
