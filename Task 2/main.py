import pygame
import sys
import json
from config import COLORS, FONTS_FALLBACK, CITY_RADIUS, HITBOX_RADIUS
from core import GameEngine

class UIController:
    def __init__(self):
        pygame.init()
        info = pygame.display.Info()
        self.width, self.height = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        
        self.font = self._load_font(20)
        self.large_font = self._load_font(32)
        self.title_font = self._load_font(56)
        
        self.strings = self._load_locales()
        self.lang = "zh"
        
        self.engine = GameEngine(self.width, self.height)
        self.state = "MENU"
        self.selected_city = None
        self.show_kruskal = False
        self.show_modal = False
        self.warning_msg = ""
        self.warning_timer = 0
        
        self._update_caption()

    def _load_locales(self):
        with open('locales.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_font(self, size):
        for font_name in FONTS_FALLBACK:
            try:
                f = pygame.font.SysFont(font_name, size, bold=True)
                if f: return f
            except: pass
        return pygame.font.Font(None, size + 4)

    def _update_caption(self):
        pygame.display.set_caption(self.strings[self.lang]['title'])

    def get_str(self, key):
        return self.strings[self.lang][key]

    def _draw_text(self, text, font, color, x, y, center=False):
        try:
            surface = font.render(text, True, color)
        except:
            surface = font.render(text.encode('utf-8', 'replace').decode('utf-8'), True, color)
        rect = surface.get_rect(center=(x, y) if center else (x, y))
        if not center: rect.topleft = (x, y)
        self.screen.blit(surface, rect)

    def _draw_button(self, rect, text, default_color, hover_color, text_color, is_active=False):
        current_color = hover_color if rect.collidepoint(pygame.mouse.get_pos()) or is_active else default_color
        shadow_rect = rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(self.screen, COLORS["DARK_GRAY"], shadow_rect, border_radius=8)
        pygame.draw.rect(self.screen, current_color, rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["BLACK"], rect, 2, border_radius=8)
        self._draw_text(text, self.font, text_color, rect.centerx, rect.centery, center=True)

    def handle_menu_click(self, pos):
        if pygame.Rect(self.width//2 - 160, self.height//2, 140, 50).collidepoint(pos):
            self.lang = 'en'
            self._update_caption()
        elif pygame.Rect(self.width//2 + 20, self.height//2, 140, 50).collidepoint(pos):
            self.lang = 'zh'
            self._update_caption()
        elif pygame.Rect(self.width//2 - 100, self.height//2 + 100, 200, 60).collidepoint(pos):
            self.engine.reset()
            self.state = "PLAYING"
            self.show_modal = False
            self.show_kruskal = False
        elif pygame.Rect(self.width//2 - 100, self.height//2 + 180, 200, 60).collidepoint(pos):
            pygame.quit()
            sys.exit()

    def handle_game_click(self, pos):
        if pygame.Rect(20, 20, 130, 35).collidepoint(pos):
            self.state = "MENU"
            return
        if pygame.Rect(self.width - 140, 20, 120, 35).collidepoint(pos):
            pygame.quit()
            sys.exit()
        if pygame.Rect(self.width - 260, 20, 110, 35).collidepoint(pos):
            self.engine.reset()
            self.show_modal = False
            self.show_kruskal = False
            return
        if pygame.Rect(self.width - 390, 20, 120, 35).collidepoint(pos):
            self.show_kruskal = not self.show_kruskal
            return

        if self.engine.is_game_over:
            if self.show_modal:
                m_y = self.height//2 - 200
                if pygame.Rect(self.width//2 - 210, m_y + 300, 130, 50).collidepoint(pos):
                    self.engine.reset()
                    self.show_modal = False
                    self.show_kruskal = False
                elif pygame.Rect(self.width//2 - 65, m_y + 300, 130, 50).collidepoint(pos):
                    self.state = "MENU"
                elif pygame.Rect(self.width//2 + 80, m_y + 300, 130, 50).collidepoint(pos):
                    self.show_modal = False
            else:
                if pygame.Rect(self.width//2 - 100, self.height - 80, 200, 50).collidepoint(pos):
                    self.show_modal = True
            return

        clicked = self.engine.get_clicked_city(pos, HITBOX_RADIUS)
        if clicked is not None:
            if self.selected_city is None:
                self.selected_city = clicked
            elif self.selected_city == clicked:
                self.selected_city = None
            else:
                success = self.engine.connect_cities(self.selected_city, clicked)
                if success:
                    if self.engine.is_game_over:
                        self.show_modal = True
                else:
                    self.warning_msg = self.get_str('already_connected')
                    self.warning_timer = 90
                self.selected_city = None

    def render_menu(self):
        self.screen.fill(COLORS["WHITE"])
        self._draw_text(self.get_str('start_title'), self.title_font, COLORS["BLACK"], self.width//2, self.height//3 - 50, True)
        self._draw_text(self.get_str('choose_lang'), self.font, COLORS["DARK_GRAY"], self.width//2, self.height//2 - 40, True)
        self._draw_button(pygame.Rect(self.width//2 - 160, self.height//2, 140, 50), "English", COLORS["GRAY"], COLORS["LIGHT_BLUE"], COLORS["BLACK"], self.lang == 'en')
        self._draw_button(pygame.Rect(self.width//2 + 20, self.height//2, 140, 50), "中文", COLORS["GRAY"], COLORS["LIGHT_BLUE"], COLORS["BLACK"], self.lang == 'zh')
        self._draw_button(pygame.Rect(self.width//2 - 100, self.height//2 + 100, 200, 60), self.get_str('start_game'), COLORS["GREEN"], (70, 220, 130), COLORS["WHITE"])
        self._draw_button(pygame.Rect(self.width//2 - 100, self.height//2 + 180, 200, 60), self.get_str('quit'), COLORS["RED"], (255, 100, 100), COLORS["WHITE"])

    def render_game(self):
        self.screen.fill(COLORS["WHITE"])
        
        if self.show_kruskal or self.engine.is_game_over:
            for u, v in self.engine.kruskal_edges:
                pygame.draw.line(self.screen, COLORS["ORANGE"], self.engine.cities[u], self.engine.cities[v], 12)
                
        for u, v in self.engine.player_edges:
            pygame.draw.line(self.screen, COLORS["BLUE"], self.engine.cities[u], self.engine.cities[v], 4)
            
        for i, city in enumerate(self.engine.cities):
            color = COLORS["GREEN"] if i == self.selected_city else COLORS["RED"]
            pygame.draw.circle(self.screen, COLORS["DARK_GRAY"], (city[0], city[1] + 3), CITY_RADIUS)
            pygame.draw.circle(self.screen, color, city, CITY_RADIUS)
            pygame.draw.circle(self.screen, COLORS["BLACK"], city, CITY_RADIUS, 2)
            self._draw_text(str(i+1), self.font, COLORS["WHITE"], city[0], city[1], True)

        self._draw_text(self.get_str('goal').format(self.engine.num_cities), self.font, COLORS["BLACK"], 20, 70)
        self._draw_text(self.get_str('current_cost').format(int(self.engine.player_cost)), self.font, COLORS["BLUE"], 20, 100)
        
        if self.show_kruskal or self.engine.is_game_over:
            self._draw_text(self.get_str('min_cost').format(int(self.engine.min_cost)), self.font, COLORS["ORANGE"], 20, 130)

        if self.warning_timer > 0:
            self._draw_text(self.warning_msg, self.large_font, COLORS["RED"], self.width // 2, 80, True)
            self.warning_timer -= 1

        self._draw_button(pygame.Rect(20, 20, 130, 35), self.get_str('back_menu'), COLORS["GRAY"], COLORS["LIGHT_BLUE"], COLORS["BLACK"])
        self._draw_button(pygame.Rect(self.width - 390, 20, 120, 35), self.get_str('hide_mst') if self.show_kruskal else self.get_str('show_mst'), COLORS["GRAY"], COLORS["LIGHT_BLUE"], COLORS["BLACK"], self.show_kruskal)
        self._draw_button(pygame.Rect(self.width - 260, 20, 110, 35), self.get_str('restart'), COLORS["GRAY"], COLORS["LIGHT_BLUE"], COLORS["BLACK"])
        self._draw_button(pygame.Rect(self.width - 140, 20, 120, 35), self.get_str('quit'), COLORS["RED"], (255, 100, 100), COLORS["WHITE"])

        if self.engine.is_game_over:
            if self.show_modal:
                self._render_modal()
            else:
                self._draw_button(pygame.Rect(self.width//2 - 100, self.height - 80, 200, 50), self.get_str('show_results'), COLORS["BLUE"], COLORS["LIGHT_BLUE"], COLORS["WHITE"])

    def _render_modal(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill(COLORS["OVERLAY"])
        self.screen.blit(overlay, (0, 0))
        
        w, h = 600, 400
        x, y = self.width//2 - w//2, self.height//2 - h//2
        pygame.draw.rect(self.screen, COLORS["MODAL_SHADOW"], (x, y+10, w, h), border_radius=20)
        pygame.draw.rect(self.screen, COLORS["WHITE"], (x, y, w, h), border_radius=20)
        pygame.draw.rect(self.screen, COLORS["BLUE"], (x, y, w, h), 4, border_radius=20)
        
        self._draw_text(self.get_str('game_over'), self.large_font, COLORS["GREEN"], self.width // 2, y + 50, True)
        
        score = (self.engine.min_cost / self.engine.player_cost) * 100 if self.engine.player_cost > 0 else 0
        self._draw_text(self.get_str('score').format(score), self.large_font, COLORS["BLACK"], self.width // 2, y + 120, True)
        
        is_perfect = int(self.engine.player_cost) <= int(self.engine.min_cost)
        eval_t = self.get_str('eval_perfect') if is_perfect else self.get_str('eval_high')
        color = COLORS["GREEN"] if is_perfect else COLORS["ORANGE"]
        self._draw_text(eval_t, self.font, color, self.width // 2, y + 180, True)

        self._draw_button(pygame.Rect(self.width//2 - 210, y + 300, 130, 50), self.get_str('restart'), COLORS["GREEN"], (70, 220, 130), COLORS["WHITE"])
        self._draw_button(pygame.Rect(self.width//2 - 65, y + 300, 130, 50), self.get_str('back_menu'), COLORS["GRAY"], COLORS["LIGHT_BLUE"], COLORS["BLACK"])
        self._draw_button(pygame.Rect(self.width//2 + 80, y + 300, 130, 50), self.get_str('view_board'), COLORS["BLUE"], COLORS["LIGHT_BLUE"], COLORS["WHITE"])

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "MENU":
                        self.handle_menu_click(pygame.mouse.get_pos())
                    else:
                        self.handle_game_click(pygame.mouse.get_pos())
            
            if self.state == "MENU":
                self.render_menu()
            else:
                self.render_game()
                
            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    app = UIController()
    app.run()