import arcade
import random
import math
import json
import os

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
BALL_RADIUS = 30
BASE_SPEED = 3
MAX_SPEED = 12
SPEED_INCREMENT = 0.25
POWERUP_CHANCE = 0.04

COLORS = {
    'bg_menu': arcade.color.DARK_BLUE_GRAY,
    'bg_game': arcade.color.DARK_GRAY,
    'bg_settings': arcade.color.DARK_SLATE_GRAY,
    'ball_default': arcade.color.WHITE,
    'ball_highlight': arcade.color.AZURE,
    'text_primary': arcade.color.WHITE,
    'text_secondary': arcade.color.LIGHT_GRAY,
    'accent': arcade.color.NEON_GREEN,
    'danger': arcade.color.RED_ORANGE,
    'warning': arcade.color.ORANGE,
    'success': arcade.color.BRIGHT_GREEN,
    'powerup_slow': arcade.color.LAVENDER,
    'powerup_shield': arcade.color.GOLD,
    'powerup_bomb': arcade.color.ORANGE,
    'powerup_double': arcade.color.CYAN,
    'button': arcade.color.DARK_GREEN,
    'button_hover': arcade.color.BRIGHT_GREEN,
    'button_disabled': arcade.color.GRAY,
    'ui_panel': (*arcade.color.BLACK[:3], 180),
    'trail': (*arcade.color.AZURE[:3], 100),
}

DEFAULT_SETTINGS = {
    'volume': 0.7, 'difficulty': 'normal', 'show_tutorial': True,
    'fullscreen': False, 'ball_color': 'white',
}

class Star:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.size = random.uniform(1, 3)
        self.speed = random.uniform(0.2, 1)
        self.alpha = random.randint(100, 255)
        self.twinkle = random.uniform(0, 6.28)
    
    def update(self, dt):
        self.y -= self.speed
        self.twinkle += dt * 2
        if self.y < 0:
            self.y = SCREEN_HEIGHT
            self.x = random.randint(0, SCREEN_WIDTH)
    
    def draw(self):
        alpha = int(self.alpha * (0.7 + 0.3 * math.sin(self.twinkle)))
        arcade.draw_circle_filled(self.x, self.y, self.size, (*arcade.color.WHITE[:3], alpha))


class Particle:
    def __init__(self, x, y, color, size=None, speed=None, lifetime=None):
        self.x = x
        self.y = y
        self.color = color
        self.size = size if size else random.randint(2, 7)
        sp = speed if speed else 3
        self.speed_x = random.uniform(-sp, sp)
        self.speed_y = random.uniform(-sp, sp)
        self.lifetime = lifetime if lifetime else random.uniform(0.5, 1.2)
        self.max_lifetime = self.lifetime
        self.alpha = 255
        self.gravity = 0.1
    
    def update(self, dt):
        self.x += self.speed_x
        self.y += self.speed_y - self.gravity
        self.lifetime -= dt
        self.alpha = max(0, int(255 * (self.lifetime / self.max_lifetime)))
        self.speed_y -= 0.05
    
    def draw(self):
        if self.alpha > 0 and self.lifetime > 0:
            color = self.color if len(self.color) == 4 else (*self.color[:3], self.alpha)
            arcade.draw_circle_filled(self.x, self.y, self.size, color)
    
    def is_alive(self):
        return self.lifetime > 0 and self.alpha > 0

class PowerUp:
    TYPES = {
        'slow': {'symbol': '🐌', 'color': COLORS['powerup_slow'], 'desc': 'Замедление'},
        'shield': {'symbol': '🛡️', 'color': COLORS['powerup_shield'], 'desc': 'Щит'},
        'bomb': {'symbol': '💥', 'color': COLORS['powerup_bomb'], 'desc': 'Бомба'},
        'double': {'symbol': '⭐', 'color': COLORS['powerup_double'], 'desc': 'x2 очки'}
    }
    
    def __init__(self, x, y, p_type):
        self.x = x
        self.y = y
        self.type = p_type
        self.config = self.TYPES.get(p_type, self.TYPES['slow'])
        self.radius = 24
        self.pulse = 0
        self.active = True
        self.float_offset = 0
        self.float_speed = random.uniform(1, 2)
    
    def update(self, dt):
        self.pulse += dt * 5
        self.float_offset = math.sin(self.pulse * self.float_speed) * 5
        if not self.active:
            self.radius *= 0.9
            return self.radius < 1
        return False
    
    def draw(self):
        if not self.active:
            return
        y = self.y + self.float_offset
        for i in range(3):
            alpha = int(80 * (1 - i/3))
            arcade.draw_circle_filled(self.x, y, self.radius * (1 + i*0.3), 
                                     (*self.config['color'][:3], alpha))
        arcade.draw_circle_filled(self.x, y, self.radius, self.config['color'])
        arcade.draw_text(self.config['symbol'], self.x, y - 10,
                        arcade.color.BLACK, 20, anchor_x="center", bold=True)
    
    def check_collection(self, mx, my):
        dist = math.hypot(mx - self.x, my - (self.y + self.float_offset))
        if dist < self.radius + 12 and self.active:
            self.active = False
            return self.type
        return None
    
    def collect_effect(self, game):
        game.particles.extend([
            Particle(self.x + random.uniform(-20, 20), self.y + random.uniform(-20, 20),
                    self.config['color'], size=4, speed=2) for _ in range(20)
        ])


class Ball(arcade.Sprite):
    COLOR_OPTIONS = {
        'white': COLORS['ball_default'], 'azure': arcade.color.AZURE,
        'cyan': arcade.color.CYAN, 'pink': arcade.color.PINK, 'gold': arcade.color.GOLD,
    }
    
    def __init__(self, x, y, speed_mult=1.0, color_name='white'):
        super().__init__()
        self.color_name = color_name
        self.base_color = self.COLOR_OPTIONS.get(color_name, COLORS['ball_default'])
        self.texture = arcade.make_circle_texture(BALL_RADIUS * 2, color=self.base_color)
        self.center_x = x
        self.center_y = y
        self.radius = BALL_RADIUS
        angle = random.uniform(0, 360)
        speed = BASE_SPEED * speed_mult
        self.change_x = speed * math.cos(math.radians(angle))
        self.change_y = speed * math.sin(math.radians(angle))
        self.trail = []
        self.max_trail = 12
        self.glow_intensity = 0
        self.shielded = False
        self.slowed = False
    
    def update(self, delta_time):
        self.trail.append((self.center_x, self.center_y))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)
        self.center_x += self.change_x
        self.center_y += self.change_y
        bounced = False
        if self.center_x - self.radius < 0:
            self.center_x = self.radius
            self.change_x *= -1
            bounced = True
        elif self.center_x + self.radius > SCREEN_WIDTH:
            self.center_x = SCREEN_WIDTH - self.radius
            self.change_x *= -1
            bounced = True
        if self.center_y - self.radius < 0:
            self.center_y = self.radius
            self.change_y *= -1
            bounced = True
        elif self.center_y + self.radius > SCREEN_HEIGHT:
            self.center_y = SCREEN_HEIGHT - self.radius
            self.change_y *= -1
            bounced = True
        if bounced:
            self.glow_intensity = 1.0
        if self.glow_intensity > 0:
            self.glow_intensity -= delta_time * 2.5
    
    def draw(self):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(120 * i / len(self.trail))
            size = self.radius * (0.3 + 0.5 * i / len(self.trail))
            arcade.draw_circle_filled(tx, ty, size, (*COLORS['trail'][:3], alpha))
        if self.glow_intensity > 0:
            glow_size = self.radius * (1 + self.glow_intensity * 0.6)
            arcade.draw_circle_filled(self.center_x, self.center_y, glow_size,
                                     (*COLORS['ball_highlight'][:3], int(100 * self.glow_intensity)))
        if self.shielded:
            arcade.draw_circle_outline(self.center_x, self.center_y, self.radius + 8,
                                      COLORS['powerup_shield'], 3)
        arcade.draw_circle_filled(self.center_x, self.center_y, self.radius, self.base_color)
        arcade.draw_circle_filled(self.center_x - 9, self.center_y + 9, 6,
                                 (*COLORS['ball_highlight'][:3], 150))
        if self.slowed:
            arcade.draw_text('🐌', self.center_x, self.center_y - 12, 
                           COLORS['powerup_slow'], 14, anchor_x="center")
    
    def apply_slow(self, factor=0.4):
        self.change_x *= factor
        self.change_y *= factor
        self.slowed = True
    
    def restore_speed(self):
        if self.slowed:
            self.change_x /= 0.4
            self.change_y /= 0.4
            self.slowed = False


class Button:
    def __init__(self, x, y, w, h, text, callback, enabled=True):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.text = text
        self.callback = callback
        self.enabled = enabled
        self.hover = False
        self.pulse = 0
        self.click_scale = 1.0
    
    def check_hover(self, mx, my):
        return (self.enabled and self.x - self.w/2 < mx < self.x + self.w/2 and 
                self.y - self.h/2 < my < self.y + self.h/2)
    
    def on_press(self, x, y):
        if self.enabled and self.check_hover(x, y):
            self.click_scale = 0.95
            self.callback()
            return True
        return False
    
    def on_release(self):
        self.click_scale = 1.0
    
    def update(self, dt):
        self.pulse += dt * 3
        if self.click_scale < 1.0:
            self.click_scale += dt * 5
            if self.click_scale > 1.0:
                self.click_scale = 1.0
    
    def draw(self):
        color = COLORS['button_disabled'] if not self.enabled else (COLORS['button_hover'] if self.hover else COLORS['button'])
        scale = self.click_scale * (1.02 if self.hover else 1)
        arcade.draw_lrbt_rectangle_filled(self.x - self.w/2 * scale, self.x + self.w/2 * scale,
                                         self.y - self.h/2 * scale, self.y + self.h/2 * scale, color)
        arcade.draw_lrbt_rectangle_outline(self.x - self.w/2 * scale, self.x + self.w/2 * scale,
                                          self.y - self.h/2 * scale, self.y + self.h/2 * scale,
                                          COLORS['text_primary'] if self.enabled else COLORS['text_secondary'], 2)
        arcade.draw_text(self.text, self.x, self.y - 5,
                        arcade.color.BLACK if self.enabled else COLORS['text_secondary'], 18, anchor_x="center", bold=True)
        if self.hover and self.enabled:
            arcade.draw_circle_filled(self.x + random.uniform(-self.w/3, self.w/3),
                                     self.y + random.uniform(-self.h/3, self.h/3),
                                     3, (*COLORS['accent'][:3], 100))


class GameOverView(arcade.View):
    def __init__(self, final_time, final_score, combo, balls_count):
        super().__init__()
        self.stats = {'time': final_time, 'score': final_score, 'combo': combo, 'balls': balls_count}
        self.buttons = []
        self.confetti = [Particle(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + random.randint(0, 100),
                                 random.choice([COLORS['accent'], COLORS['powerup_shield'], COLORS['danger']]),
                                 size=5, speed=4, lifetime=3) for _ in range(60)]
        self._setup_buttons()
        self._save_records()
    
    def _setup_buttons(self):
        y = 150
        self.buttons = [
            Button(SCREEN_WIDTH/2, y + 80, 250, 50, "🔄 Рестарт", lambda: self.window.show_view(MyGame())),
            Button(SCREEN_WIDTH/2, y + 20, 250, 50, "🏠 В меню", lambda: self.window.show_view(MenuView())),
            Button(SCREEN_WIDTH/2, y - 40, 250, 50, "⚙️ Настройки", lambda: self.window.show_view(SettingsView(self))),
        ]
    
    def _save_records(self):
        records_file = 'records.json'
        records = {}
        if os.path.exists(records_file):
            try:
                with open(records_file, 'r') as f:
                    records = json.load(f)
            except: pass
        if not records.get('best_time') or self.stats['time'] > records['best_time']:
            records['best_time'] = self.stats['time']
        if not records.get('best_score') or self.stats['score'] > records['best_score']:
            records['best_score'] = self.stats['score']
        if not records.get('best_combo') or self.stats['combo'] > records['best_combo']:
            records['best_combo'] = self.stats['combo']
        records['games_played'] = records.get('games_played', 0) + 1
        with open(records_file, 'w') as f: json.dump(records, f, indent=2)
        self.window.best_time = records.get('best_time', 0)
        self.window.best_score = records.get('best_score', 0)
        self.window.best_combo = records.get('best_combo', 0)
    
    def on_draw(self):
        self.clear()
        for p in self.confetti: p.update(1/60); p.draw()
        self.confetti = [p for p in self.confetti if p.is_alive()]
        arcade.draw_text("💥 ИГРА ОКОНЧЕНА 💥", SCREEN_WIDTH/2, SCREEN_HEIGHT - 70, COLORS['danger'], 38, anchor_x="center", bold=True)
        y = SCREEN_HEIGHT - 140
        for s in [f"⏱️ Время: {self.stats['time']:.1f} сек", f"🎯 Очки: {self.stats['score']:,}", f"🔥 Макс. комбо: х{self.stats['combo']}", f"⚪ Шариков: {self.stats['balls']}"]:
            arcade.draw_text(s, SCREEN_WIDTH/2, y, COLORS['text_primary'], 22, anchor_x="center"); y -= 35
        arcade.draw_text(f"🏆 Рекорд: {self.window.best_score:,} очков", SCREEN_WIDTH/2, 280, COLORS['text_secondary'], 16, anchor_x="center")
        for btn in self.buttons: btn.draw()
        arcade.draw_text("Нажми R для рестарта", SCREEN_WIDTH/2, 25, COLORS['text_secondary'], 14, anchor_x="center")
    
    def on_update(self, dt):
        for btn in self.buttons: btn.update(dt)
    def on_mouse_motion(self, x, y, dx, dy):
        for btn in self.buttons: btn.hover = btn.check_hover(x, y)
    def on_mouse_press(self, x, y, btn, mod):
        for b in self.buttons:
            if b.on_press(x, y): return
    def on_mouse_release(self, x, y, btn, mod):
        for b in self.buttons: b.on_release()
    def on_key_press(self, key, mod):
        if key == arcade.key.R: self.window.show_view(MyGame())
        elif key == arcade.key.M: self.window.show_view(MenuView())
        elif key == arcade.key.S: self.window.show_view(SettingsView(self))


class SettingsView(arcade.View):
    def __init__(self, return_view):
        super().__init__()
        self.return_view = return_view
        self.settings = DEFAULT_SETTINGS.copy()
        self._load_settings()
        self.buttons = []
        self._setup_ui()
    
    def _load_settings(self):
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r') as f: self.settings.update(json.load(f))
            except: pass
    
    def _save_settings(self):
        with open('settings.json', 'w') as f: json.dump(self.settings, f, indent=2)
    
    def _setup_ui(self):
        self.title = arcade.Text("⚙️ НАСТРОЙКИ", SCREEN_WIDTH/2, SCREEN_HEIGHT - 60, COLORS['text_primary'], 32, anchor_x="center")
        self.buttons = [Button(SCREEN_WIDTH/2, 400, 300, 50, "↩️ Назад", lambda: self.window.show_view(self.return_view))]
        self.volume = self.settings['volume']
        self.difficulty = self.settings['difficulty']
    
    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, COLORS['bg_settings'])
        self.title.draw()
        y = 320
        arcade.draw_text(f"🔊 Громкость: {int(self.volume * 100)}%", 100, y, COLORS['text_primary'], 20)
        arcade.draw_lrbt_rectangle_filled(100, 400, y-35, y-25, arcade.color.DARK_GRAY)
        arcade.draw_lrbt_rectangle_filled(100, 100 + 300 * self.volume, y-35, y-25, COLORS['accent'])
        arcade.draw_text("🎮 Сложность: ", 100, y - 70, COLORS['text_primary'], 20)
        for i, diff in enumerate(['easy', 'normal', 'hard']):
            x = 100 + i * 180
            active = diff == self.difficulty
            arcade.draw_lrbt_rectangle_filled(x-60, x+60, y-135, y-105, COLORS['accent'] if active else COLORS['button'])
            arcade.draw_text(diff.upper(), x, y-125, arcade.color.BLACK if active else COLORS['text_primary'], 16, anchor_x="center", bold=active)
        arcade.draw_text("🎨 Цвет шарика: ", 100, y - 170, COLORS['text_primary'], 20)
        for i, cname in enumerate(Ball.COLOR_OPTIONS.keys()):
            x = 100 + i * 130
            active = cname == self.settings['ball_color']
            arcade.draw_circle_filled(x, y - 195, 20, Ball.COLOR_OPTIONS[cname])
            if active: arcade.draw_circle_outline(x, y - 195, 24, COLORS['accent'], 2)
        for btn in self.buttons: btn.draw()
        arcade.draw_text("ESC — выход", SCREEN_WIDTH/2, 30, COLORS['text_secondary'], 14, anchor_x="center")
    
    def on_update(self, dt):
        for btn in self.buttons: btn.update(dt)
    def on_mouse_motion(self, x, y, dx, dy):
        for btn in self.buttons: btn.hover = btn.check_hover(x, y)
    def on_mouse_press(self, x, y, btn, mod):
        if 100 <= x <= 400 and 285 <= y <= 295:
            self.volume = max(0, min(1, (x - 100) / 300))
            self.settings['volume'] = self.volume
            self._save_settings()
        for i, diff in enumerate(['easy', 'normal', 'hard']):
            if 100 + i*180 - 60 <= x <= 100 + i*180 + 60 and 165 <= y <= 195:
                self.difficulty = diff
                self.settings['difficulty'] = diff
                self._save_settings()
                break
        for i, cname in enumerate(Ball.COLOR_OPTIONS.keys()):
            if 100 + i*130 - 25 <= x <= 100 + i*130 + 25 and 95 <= y <= 135:
                self.settings['ball_color'] = cname
                self._save_settings()
                break
        for b in self.buttons:
            if b.on_press(x, y): return
    def on_mouse_release(self, x, y, btn, mod):
        for b in self.buttons: b.on_release()
    def on_key_press(self, key, mod):
        if key == arcade.key.ESCAPE: self.window.show_view(self.return_view)


class PauseView(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view
        self.buttons = [
            Button(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 40, 280, 55, "▶️ Продолжить", lambda: self.window.show_view(self.game_view)),
            Button(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 30, 280, 55, "🏠 В меню", lambda: self.window.show_view(MenuView())),
        ]
    def on_draw(self):
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (*arcade.color.BLACK[:3], 200))
        arcade.draw_text("⏸️ ПАУЗА", SCREEN_WIDTH/2, SCREEN_HEIGHT - 100, COLORS['accent'], 44, anchor_x="center", bold=True)
        for btn in self.buttons: btn.draw()
        arcade.draw_text("P или ESC — продолжить", SCREEN_WIDTH/2, 40, COLORS['text_secondary'], 16, anchor_x="center")
    def on_update(self, dt):
        for btn in self.buttons: btn.update(dt)
    def on_mouse_motion(self, x, y, dx, dy):
        for btn in self.buttons: btn.hover = btn.check_hover(x, y)
    def on_mouse_press(self, x, y, btn, mod):
        for b in self.buttons:
            if b.on_press(x, y): return
    def on_mouse_release(self, x, y, btn, mod):
        for b in self.buttons: b.on_release()
    def on_key_press(self, key, mod):
        if key in [arcade.key.P, arcade.key.ESCAPE]: self.window.show_view(self.game_view)


class TutorialView(arcade.View):
    def __init__(self, next_view):
        super().__init__()
        self.next_view = next_view
        self.step = 0
        self.steps = [
            {'title': '🎮 Добро пожаловать!', 'text': 'Ball Chaos — аркада, где ты добавляешь шарики,\nно не даёшь им столкнуться!', 'hint': 'Нажми ЛКМ или SPACE'},
            {'title': '⚡ Как играть', 'text': '• Кликни ЛКМ, чтобы добавить шарик\n• Шарики летают и отскакивают\n• Столкновение = конец игры!', 'hint': 'Кликни в любом месте!'},
            {'title': '🎁 Бонусы', 'text': '🐌 Замедление на 10 сек\n🛡️ Щит от столкновения\n💥 Бомба — удаляет шарики', 'hint': 'Кликни по бонусу!'},
            {'title': '🏆 Цель', 'text': 'Набери больше очков!\n• +10 за шарик • Комбо-множитель • Бонусы', 'hint': 'Нажми SPACE для старта!'}
        ]
    def on_draw(self):
        self.clear()
        step = self.steps[self.step]
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, COLORS['bg_menu'])
        arcade.draw_lrbt_rectangle_filled(100, SCREEN_WIDTH - 100, 120, SCREEN_HEIGHT - 120, COLORS['ui_panel'])
        arcade.draw_lrbt_rectangle_outline(100, SCREEN_WIDTH - 100, 120, SCREEN_HEIGHT - 120, COLORS['accent'], 3)
        arcade.draw_text(step['title'], SCREEN_WIDTH/2, SCREEN_HEIGHT - 180, COLORS['accent'], 32, anchor_x="center", bold=True)
        for i, line in enumerate(step['text'].split('\n')): arcade.draw_text(line, SCREEN_WIDTH/2, SCREEN_HEIGHT - 260 - i*30, COLORS['text_primary'], 20, anchor_x="center")
        for i in range(len(self.steps)):
            x = SCREEN_WIDTH/2 - 60 + i * 30
            arcade.draw_circle_filled(x, SCREEN_HEIGHT - 380, 8 if i == self.step else 6, COLORS['accent'] if i == self.step else COLORS['text_secondary'])
        arcade.draw_text(step['hint'], SCREEN_WIDTH/2, 150, COLORS['text_secondary'], 18, anchor_x="center", italic=True)
        arcade.draw_text("← → — переключение | ESC — пропустить", SCREEN_WIDTH/2, 50, COLORS['text_secondary'], 14, anchor_x="center")
    def on_key_press(self, key, mod):
        if key == arcade.key.RIGHT: self.step = min(self.step + 1, len(self.steps) - 1)
        elif key == arcade.key.LEFT: self.step = max(self.step - 1, 0)
        elif key == arcade.key.SPACE and self.step == len(self.steps) - 1: self.window.show_view(self.next_view)
        elif key == arcade.key.ESCAPE: self.window.show_view(self.next_view)
    def on_mouse_press(self, x, y, btn, mod):
        if self.step < len(self.steps) - 1: self.step += 1
        else: self.window.show_view(self.next_view)


class MenuView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = COLORS['bg_menu']
        self.stars = [Star() for _ in range(50)]
        self.buttons = []
        self.title_y = SCREEN_HEIGHT / 2 + 110
        self.title_velocity = 0.6
        self.pulse = 0
        self._setup_buttons()
        self._load_records()
    def _load_records(self):
        if os.path.exists('records.json'):
            try:
                with open('records.json', 'r') as f:
                    records = json.load(f)
                    self.window.best_time = records.get('best_time', 0)
                    self.window.best_score = records.get('best_score', 0)
                    self.window.best_combo = records.get('best_combo', 0)
            except: pass
    def _setup_buttons(self):
        y = SCREEN_HEIGHT / 2
        self.buttons = [
            Button(SCREEN_WIDTH/2, y, 300, 60, "▶️ ИГРАТЬ", lambda: self._start_game()),
            Button(SCREEN_WIDTH/2, y - 75, 300, 60, "⚙️ НАСТРОЙКИ", lambda: self.window.show_view(SettingsView(self))),
            Button(SCREEN_WIDTH/2, y - 150, 300, 60, "❌ ВЫХОД", lambda: arcade.close_window()),
        ]
    def _start_game(self):
        if self.window.settings.get('show_tutorial', True): self.window.show_view(TutorialView(MyGame()))
        else: self.window.show_view(MyGame())
    def on_draw(self):
        self.clear()
        for star in self.stars: star.draw()
        scale = 1 + 0.03 * math.sin(self.pulse)
        arcade.draw_text("🎮 BALL CHAOS 🎮", SCREEN_WIDTH/2, self.title_y, COLORS['accent'], int(48 * scale), anchor_x="center", bold=True)
        arcade.draw_text(f"🏆 Рекорды: {getattr(self.window, 'best_time', 0):.1f} сек | {getattr(self.window, 'best_score', 0):,} очков", SCREEN_WIDTH/2, 55, COLORS['text_secondary'], 17, anchor_x="center")
        for btn in self.buttons: btn.draw()
        arcade.draw_text("v3.0", SCREEN_WIDTH - 50, 20, COLORS['text_secondary'], 12, anchor_x="right")
    def on_update(self, dt):
        self.pulse += dt * 2
        self.title_y += self.title_velocity
        if self.title_y > SCREEN_HEIGHT/2 + 120 or self.title_y < SCREEN_HEIGHT/2 + 100: self.title_velocity *= -1
        for star in self.stars: star.update(dt)
        for btn in self.buttons: btn.update(dt)
    def on_mouse_motion(self, x, y, dx, dy):
        for btn in self.buttons: btn.hover = btn.check_hover(x, y)
    def on_mouse_press(self, x, y, btn, mod):
        for b in self.buttons:
            if b.on_press(x, y): return
    def on_mouse_release(self, x, y, btn, mod):
        for b in self.buttons: b.on_release()
    def on_key_press(self, key, mod):
        if key == arcade.key.SPACE: self._start_game()
        elif key == arcade.key.ESCAPE: arcade.close_window()

class MyGame(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = COLORS['bg_game']
        self.balls = arcade.SpriteList()
        self.powerups = []
        self.particles = []
        self.stars = [Star() for _ in range(30)]
        self.time = 0.0
        self.score = 0
        self.combo = 1
        self.max_combo = 1
        self.game_over = False
        self.paused = False
        self.speed_mult = 1.0
        self.double_points = False
        self.double_timer = 0
        self.shield_active = False
        self.slow_active = False
        self.slow_timer = 0
        self.screen_shake = 0
        self.shake_intensity = 0
        self.settings = DEFAULT_SETTINGS.copy()
        self._load_settings()
        self.ball_color = self.settings.get('ball_color', 'white')
        self.ui_time = arcade.Text("", 20, SCREEN_HEIGHT - 35, COLORS['text_primary'], 20)
        self.ui_score = arcade.Text("", 150, SCREEN_HEIGHT - 35, COLORS['accent'], 20, bold=True)
        self.ui_combo = arcade.Text("", 280, SCREEN_HEIGHT - 35, COLORS['powerup_bomb'], 20)
        self.ui_status = arcade.Text("", 400, SCREEN_HEIGHT - 35, COLORS['text_primary'], 18)
        self.tutorial_shown = not self.settings.get('show_tutorial', True)
        self.tutorial_step = 0
    
    def _load_settings(self):
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r') as f: self.settings.update(json.load(f))
            except: pass
    
    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, COLORS['bg_game'])
        for star in self.stars: star.draw()
        self.balls.draw()
        for p in self.powerups:
            if p.active: p.draw()
        for p in self.particles: p.draw()
        self._draw_ui()
        if self.paused:
            arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT, (*arcade.color.BLACK[:3], 200))
            arcade.draw_text("⏸️ ПАУЗА", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, COLORS['accent'], 48, anchor_x="center", bold=True)
            arcade.draw_text("P или ESC — продолжить", SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 60, COLORS['text_secondary'], 22, anchor_x="center")
        if not self.tutorial_shown: self._draw_tutorial()
    
    def _draw_ui(self):
        arcade.draw_lrbt_rectangle_filled(0, SCREEN_WIDTH, SCREEN_HEIGHT - 50, SCREEN_HEIGHT, COLORS['ui_panel'])
        self.ui_time.text = f"⏱️ {self.time:.1f}"
        self.ui_score.text = f"🎯 {self.score:,}"
        self.ui_time.draw()
        self.ui_score.draw()
        if self.combo > 1:
            self.ui_combo.text = f"🔥 x{self.combo}"
            self.ui_combo.draw()
        statuses = []
        if self.shield_active: statuses.append("🛡️")
        if self.slow_active: statuses.append(f"🐌 {max(0, self.slow_timer):.1f}")
        if self.double_points: statuses.append(f"⭐ {max(0, self.double_timer):.1f}")
        if statuses:
            self.ui_status.text = "   ".join(statuses)
            self.ui_status.position = (400, SCREEN_HEIGHT - 35)
            self.ui_status.draw()
        prog = min(1, (self.speed_mult - 1) / (MAX_SPEED / BASE_SPEED - 1))
        arcade.draw_lrbt_rectangle_filled(SCREEN_WIDTH - 220, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 50, SCREEN_HEIGHT - 45, arcade.color.DARK_GRAY)
        arcade.draw_lrbt_rectangle_filled(SCREEN_WIDTH - 220, SCREEN_WIDTH - 220 + 200 * prog, SCREEN_HEIGHT - 50, SCREEN_HEIGHT - 45, COLORS['danger'])
    
    def _draw_tutorial(self):
        hints = ["👆 Кликни, чтобы добавить шарик!", "🎁 Собирай бонусы!", "⚠️ Не дай шарикам столкнуться!"]
        if self.tutorial_step < len(hints):
            arcade.draw_lrbt_rectangle_filled(SCREEN_WIDTH/2 - 200, SCREEN_WIDTH/2 + 200, 100, 180, COLORS['ui_panel'])
            arcade.draw_text(hints[self.tutorial_step], SCREEN_WIDTH/2, 140, COLORS['accent'], 18, anchor_x="center")
            if self.time > 3 + self.tutorial_step * 5: self.tutorial_step += 1
        else: self.tutorial_shown = True
    
    def on_update(self, delta_time):
        if self.paused or self.game_over: return
        self.time += delta_time
        if int(self.time) % 15 == 0 and self.speed_mult < MAX_SPEED / BASE_SPEED:
            self.speed_mult = min(MAX_SPEED / BASE_SPEED, self.speed_mult + SPEED_INCREMENT / 10)
            self.particles.extend([Particle(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT/2, COLORS['warning'], size=3, speed=2, lifetime=0.8) for _ in range(10)])
        eff_dt = delta_time
        if self.slow_active:
            eff_dt *= 0.3
            self.slow_timer -= delta_time
            if self.slow_timer <= 0:
                self.slow_active = False
                for b in self.balls: b.restore_speed()
        if self.double_points:
            self.double_timer -= delta_time
            if self.double_timer <= 0: self.double_points = False
        self.balls.update(eff_dt)
        for p in self.particles: p.update(delta_time)
        self.particles = [p for p in self.particles if p.is_alive()]
        for p in self.powerups: p.update(delta_time)
        self.powerups = [p for p in self.powerups if p.active]
        for star in self.stars: star.update(delta_time)
        self._check_collisions()
        if self.balls and self.time > 0.5:
            base = len(self.balls) * self.combo
            if self.double_points: base *= 2
            self.score += int(base * delta_time * 10)
    
    def _check_collisions(self):
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                b1, b2 = self.balls[i], self.balls[j]
                dist = math.hypot(b1.center_x - b2.center_x, b1.center_y - b2.center_y)
                if dist < b1.radius + b2.radius:
                    if self.shield_active:
                        self.shield_active = False
                        b1.change_x, b2.change_x = b2.change_x, b1.change_x
                        b1.change_y, b2.change_y = b2.change_y, b1.change_y
                        self.particles.extend([Particle(b1.center_x, b1.center_y, COLORS['powerup_shield'], size=5, speed=3, lifetime=0.6) for _ in range(25)])
                        self.screen_shake = 10
                        self.shake_intensity = 3
                    else: self._game_over()
                    return
    
    def _game_over(self):
        self.game_over = True
        self.window.show_view(GameOverView(self.time, self.score, self.max_combo, len(self.balls)))
    
    def on_mouse_press(self, x, y, button, modifiers):
        if self.paused or self.game_over: return
        for p in self.powerups:
            if p.active:
                result = p.check_collection(x, y)
                if result:
                    self._apply_powerup(result)
                    p.collect_effect(self)
                    return
        self.balls.append(Ball(x, y, self.speed_mult, self.ball_color))
        self.particles.extend([Particle(x + random.uniform(-15, 15), y + random.uniform(-15, 15), COLORS['ball_highlight'], size=4, speed=2, lifetime=0.7) for _ in range(12)])
        if random.random() < POWERUP_CHANCE:
            p_type = random.choice(list(PowerUp.TYPES.keys()))
            self.powerups.append(PowerUp(x, y + 50, p_type))
        base_score = 10 * self.combo
        if self.double_points: base_score *= 2
        self.score += base_score
        self.combo = min(self.combo + 1, 15)
        self.max_combo = max(self.max_combo, self.combo)
    
    def _apply_powerup(self, p_type):
        if p_type == 'slow':
            self.slow_active = True
            self.slow_timer = 10.0
            for b in self.balls: b.apply_slow()
        elif p_type == 'shield':
            self.shield_active = True
            for b in self.balls: b.shielded = True
        elif p_type == 'bomb':
            if len(self.balls) > 1:
                for _ in range(len(self.balls) - 1):
                    b = self.balls.pop()
                    self.particles.extend([Particle(b.center_x, b.center_y, COLORS['powerup_bomb'], size=5, speed=3, lifetime=0.8) for _ in range(15)])
                self.score += 100 * self.combo
        elif p_type == 'double':
            self.double_points = True
            self.double_timer = 15.0
    
    def on_key_press(self, key, modifiers):
        if key == arcade.key.P and not self.game_over:
            self.paused = not self.paused
            if self.paused: self.window.show_view(PauseView(self))
        elif key == arcade.key.ESCAPE and self.paused:
            self.paused = False
            self.window.show_view(self)
        elif not self.tutorial_shown: self.tutorial_shown = True
        elif self.game_over:
            if key == arcade.key.R: self.window.show_view(MyGame())
            elif key == arcade.key.M: self.window.show_view(MenuView())


def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "🎮 Ball Chaos 🎮", fullscreen=False)
    window.best_time = 0.0
    window.best_score = 0
    window.best_combo = 0
    window.settings = DEFAULT_SETTINGS.copy()
    if os.path.exists('records.json'):
        try:
            with open('records.json', 'r') as f:
                records = json.load(f)
                window.best_time = records.get('best_time', 0)
                window.best_score = records.get('best_score', 0)
                window.best_combo = records.get('best_combo', 0)
        except Exception as e: print(f"Warning: Could not load records: {e}")
    window.show_view(MenuView())
    print("🎮 Ball Chaos запущен! ЛКМ — шарик, P — пауза, ESC — меню")
    arcade.run()


if __name__ == "__main__":
    main()