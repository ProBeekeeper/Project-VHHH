import pygame
import math
import random
import sys
from dsu import DSU

# Dictionary for translations
STRINGS = {
    'en': {
        'title': "Road Connector - Kruskal's MST",
        'start_title': "Road Connector",
        'btn_en': "English",
        'btn_zh': "中文",
        'goal': "Goal: Connect all {} cities",
        'current_cost': "Current Cost: {}",
        'min_cost': "Min Theoretical Cost: {}",
        'already_connected': "Already connected! No need to rebuild.",
        'hide_mst': "Hide MST",
        'show_mst': "Show MST",
        'restart': "Restart",
        'game_over': "All cities connected! Game Over",
        'score': "Performance Score: {:.1f}%",
        'eval_perfect': "Perfect! You found the Minimum Spanning Tree!",
        'eval_high': "Cost is high. Thick orange lines show the optimal path.",
        'back_menu': "Main Menu",
        'choose_lang': "Choose Language / 选择语言",
        'start_game': "Start Game",
        'quit': "Quit",
        'view_board': "View Board",
        'show_results': "Show Results",
    },
    'zh': {
        'title': "道路连接器 - Kruskal 最小生成树",
        'start_title': "道路连接器",
        'btn_en': "English",
        'btn_zh': "中文",
        'goal': "目标: 连接所有 {} 个城市",
        'current_cost': "当前建设成本: {}",
        'min_cost': "理论最低成本: {}",
        'already_connected': "已连通，无需重复建设！",
        'hide_mst': "隐藏 MST",
        'show_mst': "演示 MST",
        'restart': "重新开始",
        'game_over': "所有城市已连通！游戏结束",
        'score': "您的表现得分：{:.1f}%",
        'eval_perfect': "完美！您找到了最小生成树！",
        'eval_high': "成本偏高，橙色粗线为理论最低成本方案。",
        'back_menu': "返回菜单",
        'choose_lang': "Choose Language / 选择语言",
        'start_game': "开始游戏",
        'quit': "退出游戏",
        'view_board': "查看路线",
        'show_results': "显示结算",
    }
}

# ==========================================
# Core Game Class: Game
# ==========================================
class Game:
    """
    Road Connector Main Game Class
    Responsible for GUI rendering, event handling, player interaction, and Kruskal's algorithm demonstration.
    """
    def __init__(self):
        pygame.init()
        
        # Screen settings
        infoObject = pygame.display.Info()
        self.width = infoObject.current_w
        self.height = infoObject.current_h
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        
        # Color definitions for a more modern UI
        self.WHITE = (245, 247, 250)
        self.BLACK = (40, 40, 40)
        self.GRAY = (220, 225, 230)
        self.DARK_GRAY = (180, 185, 190)
        self.BLUE = (60, 130, 240)
        self.LIGHT_BLUE = (200, 220, 255)
        self.RED = (240, 80, 80)
        self.GREEN = (46, 204, 113)
        self.ORANGE = (243, 156, 18)
        
        # Attempt to load fonts that support both English and Chinese
        fonts_to_try = ['microsoftyahei', 'simhei', 'simsun', 'fangsong', 'arial']
        self.font = None
        self.large_font = None
        self.title_font = None
        
        for font_name in fonts_to_try:
            try:
                self.font = pygame.font.SysFont(font_name, 20, bold=True)
                self.large_font = pygame.font.SysFont(font_name, 32, bold=True)
                self.title_font = pygame.font.SysFont(font_name, 56, bold=True)
                if self.font:
                    break
            except:
                pass
                
        if not self.font:
            self.font = pygame.font.Font(None, 24)
            self.large_font = pygame.font.Font(None, 36)
            self.title_font = pygame.font.Font(None, 64)
            
        # UI State
        self.state = "MENU" # "MENU" or "PLAYING"
        self.lang = "en"
        pygame.display.set_caption(STRINGS[self.lang]['title'])
        
        # Initialize game state
        self.reset_game()

    def get_str(self, key):
        return STRINGS[self.lang][key]

    def reset_game(self):
        """Reset the game state and generate a new city distribution."""
        self.num_cities = random.randint(6, 8)  # Randomly generate 6-8 cities
        
        # Randomly generate city coordinates, keeping a margin to avoid edges
        margin = 60
        top_margin = 120 # Leave space at the top for info panel and buttons
        self.cities = []
        for _ in range(self.num_cities):
            valid = False
            while not valid:
                x = random.randint(margin, self.width - margin)
                y = random.randint(top_margin, self.height - margin)
                valid = True
                for cx, cy in self.cities:
                    if math.hypot(x - cx, y - cy) < 50: # If too close, regenerate
                        valid = False
                        break
            self.cities.append((x, y))
            
        # Player state
        self.player_dsu = DSU(self.num_cities) # Player's DSU
        self.player_edges = []                 # Edges connected by player [(u, v), ...]
        self.player_cost = 0.0                 # Player's cumulative construction cost
        self.selected_city = None              # Currently selected city index
        self.warning_msg = ""                  # Warning message
        self.warning_timer = 0                 # Timer for showing warning message
        
        # System Kruskal algorithm state
        self.show_kruskal = False              # Whether to show the theoretical minimum cost solution
        self.kruskal_edges = []                # Optimal connection edges [(u, v), ...]
        self.min_cost = 0.0                    # Theoretical minimum cost
        self.calculate_kruskal()               # Pre-calculate Kruskal's result
        
        self.game_over = False                 # Is the game over?
        self.show_modal = False

    def calculate_distance(self, p1, p2):
        """Calculate Euclidean distance between two points, used as construction cost."""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def calculate_kruskal(self):
        """
        Kruskal's algorithm to calculate the Minimum Spanning Tree (MST).
        """
        edges = []
        for i in range(self.num_cities):
            for j in range(i + 1, self.num_cities):
                dist = self.calculate_distance(self.cities[i], self.cities[j])
                edges.append((dist, i, j))
                
        edges.sort(key=lambda x: x[0])
        system_dsu = DSU(self.num_cities)
        
        for dist, u, v in edges:
            if system_dsu.union(u, v):
                self.kruskal_edges.append((u, v))
                self.min_cost += dist
                if len(self.kruskal_edges) == self.num_cities - 1:
                    break

    def handle_events(self):
        """Handle all Pygame events, including mouse clicks and window closing."""
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Left click
                if self.state == "MENU":
                    self.handle_menu_clicks(mouse_pos)
                elif self.state == "PLAYING":
                    self.handle_game_clicks(mouse_pos)

    def handle_menu_clicks(self, pos):
        """Handle clicks when in the start menu"""
        # Language buttons
        en_rect = pygame.Rect(self.width//2 - 160, self.height//2, 140, 50)
        zh_rect = pygame.Rect(self.width//2 + 20, self.height//2, 140, 50)
        
        if en_rect.collidepoint(pos):
            self.lang = 'en'
            pygame.display.set_caption(STRINGS[self.lang]['title'])
        elif zh_rect.collidepoint(pos):
            self.lang = 'zh'
            pygame.display.set_caption(STRINGS[self.lang]['title'])
            
        # Start button
        start_rect = pygame.Rect(self.width//2 - 100, self.height//2 + 100, 200, 60)
        if start_rect.collidepoint(pos):
            self.reset_game()
            self.state = "PLAYING"
            
        # Quit button
        quit_rect = pygame.Rect(self.width//2 - 100, self.height//2 + 180, 200, 60)
        if quit_rect.collidepoint(pos):
            pygame.quit()
            sys.exit()

    def handle_game_clicks(self, pos):
        """Handle clicks when playing the game"""
        # Back to Menu button
        menu_rect = pygame.Rect(20, 20, 130, 35)
        if menu_rect.collidepoint(pos):
            self.state = "MENU"
            return
            
        # Quit button
        quit_rect = pygame.Rect(self.width - 140, 20, 120, 35)
        if quit_rect.collidepoint(pos):
            pygame.quit()
            sys.exit()

        # Restart button
        reset_rect = pygame.Rect(self.width - 260, 20, 110, 35)
        if reset_rect.collidepoint(pos):
            self.reset_game()
            return

        # Show/Hide MST button
        kruskal_rect = pygame.Rect(self.width - 390, 20, 120, 35)
        if kruskal_rect.collidepoint(pos):
            self.show_kruskal = not self.show_kruskal
            return
        
        if self.game_over:
            if getattr(self, 'show_modal', False):
                modal_width = 600
                modal_height = 350
                modal_rect = pygame.Rect(self.width//2 - modal_width//2, self.height//2 - modal_height//2, modal_width, modal_height)
                
                restart_modal_rect = pygame.Rect(self.width//2 - 230, modal_rect.bottom - 90, 140, 50)
                menu_modal_rect = pygame.Rect(self.width//2 - 70, modal_rect.bottom - 90, 140, 50)
                view_board_modal_rect = pygame.Rect(self.width//2 + 90, modal_rect.bottom - 90, 140, 50)
                
                if restart_modal_rect.collidepoint(pos):
                    self.reset_game()
                elif menu_modal_rect.collidepoint(pos):
                    self.state = "MENU"
                elif view_board_modal_rect.collidepoint(pos):
                    self.show_modal = False
            else:
                show_results_rect = pygame.Rect(self.width//2 - 100, self.height - 80, 200, 50)
                if show_results_rect.collidepoint(pos):
                    self.show_modal = True
            return 
            
        # Check if a city point was clicked
        clicked_city = None
        for i, city in enumerate(self.cities):
            if math.hypot(pos[0] - city[0], pos[1] - city[1]) <= 25: # Slightly larger hit area
                clicked_city = i
                break
                
        if clicked_city is not None:
            if self.selected_city is None:
                self.selected_city = clicked_city
            else:
                if self.selected_city == clicked_city:
                    self.selected_city = None
                else:
                    u, v = self.selected_city, clicked_city
                    dist = self.calculate_distance(self.cities[u], self.cities[v])
                    
                    if self.player_dsu.union(u, v):
                        self.player_edges.append((u, v))
                        self.player_cost += dist
                        self.selected_city = None 
                        
                        if len(self.player_edges) == self.num_cities - 1:
                            self.game_over = True
                            self.show_modal = True
                    else:
                        self.warning_msg = self.get_str('already_connected')
                        self.warning_timer = 90 
                        self.selected_city = None

    def draw_text(self, text, font, color, x, y, center=False):
        """Helper method: Draw text on the screen."""
        try:
            surface = font.render(text, True, color)
        except pygame.error:
            surface = font.render(text.encode('utf-8', 'replace').decode('utf-8'), True, color)
        rect = surface.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surface, rect)

    def draw_button(self, rect, text, default_color, hover_color, text_color, is_active=False):
        """Helper method: Draw a beautiful interactive button."""
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = rect.collidepoint(mouse_pos)
        
        current_color = hover_color if is_hovered or is_active else default_color
        
        # Shadow effect
        shadow_rect = rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(self.screen, self.DARK_GRAY, shadow_rect, border_radius=8)
        
        # Button body
        pygame.draw.rect(self.screen, current_color, rect, border_radius=8)
        
        # Border
        pygame.draw.rect(self.screen, self.BLACK, rect, 2, border_radius=8)
        self.draw_text(text, self.font, text_color, rect.centerx, rect.centery, center=True)

    def draw_menu(self):
        """Render the Start Menu."""
        self.screen.fill(self.WHITE)
        
        # Title
        self.draw_text(self.get_str('start_title'), self.title_font, self.BLACK, self.width//2, self.height//3 - 50, center=True)
        
        # Language Selection Label
        self.draw_text(self.get_str('choose_lang'), self.font, self.DARK_GRAY, self.width//2, self.height//2 - 40, center=True)
        
        # Language Buttons
        en_rect = pygame.Rect(self.width//2 - 160, self.height//2, 140, 50)
        zh_rect = pygame.Rect(self.width//2 + 20, self.height//2, 140, 50)
        
        self.draw_button(en_rect, "English", self.GRAY, self.LIGHT_BLUE, self.BLACK, is_active=(self.lang == 'en'))
        self.draw_button(zh_rect, "中文", self.GRAY, self.LIGHT_BLUE, self.BLACK, is_active=(self.lang == 'zh'))
        
        # Start Game Button
        start_rect = pygame.Rect(self.width//2 - 100, self.height//2 + 100, 200, 60)
        self.draw_button(start_rect, self.get_str('start_game'), self.GREEN, (70, 220, 130), self.WHITE)

        # Quit Game Button
        quit_rect = pygame.Rect(self.width//2 - 100, self.height//2 + 180, 200, 60)
        self.draw_button(quit_rect, self.get_str('quit'), self.RED, (255, 100, 100), self.WHITE)

    def draw_game(self):
        """Render the main game screen."""
        self.screen.fill(self.WHITE)
        
        # 1. Draw theoretical minimum cost (Kruskal's solution) - Thick orange lines
        if self.show_kruskal or self.game_over:
            for u, v in self.kruskal_edges:
                pygame.draw.line(self.screen, self.ORANGE, self.cities[u], self.cities[v], 12)
                
        # 2. Draw player's connected lines - Standard blue lines
        for u, v in self.player_edges:
            pygame.draw.line(self.screen, self.BLUE, self.cities[u], self.cities[v], 4)
            
        # 3. Draw cities (nodes)
        for i, city in enumerate(self.cities):
            # Selected city is highlighted green
            color = self.GREEN if i == self.selected_city else self.RED
            # Draw shadow for depth
            pygame.draw.circle(self.screen, self.DARK_GRAY, (city[0], city[1] + 3), 16)
            pygame.draw.circle(self.screen, color, city, 16)
            pygame.draw.circle(self.screen, self.BLACK, city, 16, 2) # Border
            
            self.draw_text(str(i+1), self.font, self.WHITE, city[0], city[1], center=True)
            
        # 4. Draw UI Info Panel (Top Left)
        info_y = 70
        self.draw_text(self.get_str('goal').format(self.num_cities), self.font, self.BLACK, 20, info_y)
        self.draw_text(self.get_str('current_cost').format(int(self.player_cost)), self.font, self.BLUE, 20, info_y + 30)
        
        if self.show_kruskal or self.game_over:
            self.draw_text(self.get_str('min_cost').format(int(self.min_cost)), self.font, self.ORANGE, 20, info_y + 60)
            
        # 5. Draw warning message
        if self.warning_timer > 0:
            # Simple fade-in/out effect imitation via color
            self.draw_text(self.warning_msg, self.large_font, self.RED, self.width // 2, 80, center=True)
            self.warning_timer -= 1
            
        # 6. Draw top buttons
        menu_rect = pygame.Rect(20, 20, 130, 35)
        self.draw_button(menu_rect, self.get_str('back_menu'), self.GRAY, self.LIGHT_BLUE, self.BLACK)
        
        kruskal_rect = pygame.Rect(self.width - 390, 20, 120, 35)
        btn_text = self.get_str('hide_mst') if self.show_kruskal else self.get_str('show_mst')
        self.draw_button(kruskal_rect, btn_text, self.GRAY, self.LIGHT_BLUE, self.BLACK, is_active=self.show_kruskal)
        
        reset_rect = pygame.Rect(self.width - 260, 20, 110, 35)
        self.draw_button(reset_rect, self.get_str('restart'), self.GRAY, self.LIGHT_BLUE, self.BLACK)

        quit_rect = pygame.Rect(self.width - 140, 20, 120, 35)
        self.draw_button(quit_rect, self.get_str('quit'), self.RED, (255, 100, 100), self.WHITE)
        
        # 7. Draw Game Over screen Overlay
        if self.game_over and getattr(self, 'show_modal', False):
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            
            modal_width = 600
            modal_height = 350
            modal_rect = pygame.Rect(self.width//2 - modal_width//2, self.height//2 - modal_height//2, modal_width, modal_height)
            
            # Modal Shadow
            shadow_rect = modal_rect.copy()
            shadow_rect.y += 10
            pygame.draw.rect(self.screen, (0, 0, 0, 100), shadow_rect, border_radius=20)
            
            # Modal Body
            pygame.draw.rect(self.screen, self.WHITE, modal_rect, border_radius=20)
            pygame.draw.rect(self.screen, self.BLUE, modal_rect, 4, border_radius=20)
            
            self.draw_text(self.get_str('game_over'), self.large_font, self.GREEN, self.width // 2, modal_rect.y + 60, center=True)
            
            score = (int(self.min_cost) / int(self.player_cost)) * 100 if int(self.player_cost) > 0 else 0
            self.draw_text(self.get_str('score').format(score), self.large_font, self.BLACK, self.width // 2, modal_rect.y + 130, center=True)
            
            eval_text = self.get_str('eval_perfect') if int(self.player_cost) <= int(self.min_cost) else self.get_str('eval_high')
            color = self.GREEN if int(self.player_cost) <= int(self.min_cost) else self.ORANGE
            self.draw_text(eval_text, self.font, color, self.width // 2, modal_rect.y + 190, center=True)

            restart_modal_rect = pygame.Rect(self.width//2 - 230, modal_rect.bottom - 90, 140, 50)
            self.draw_button(restart_modal_rect, self.get_str('restart'), self.GREEN, (70, 220, 130), self.WHITE)
            
            menu_modal_rect = pygame.Rect(self.width//2 - 70, modal_rect.bottom - 90, 140, 50)
            self.draw_button(menu_modal_rect, self.get_str('back_menu'), self.GRAY, self.LIGHT_BLUE, self.BLACK)

            view_board_modal_rect = pygame.Rect(self.width//2 + 90, modal_rect.bottom - 90, 140, 50)
            self.draw_button(view_board_modal_rect, self.get_str('view_board'), self.BLUE, self.LIGHT_BLUE, self.WHITE)
        elif self.game_over and not getattr(self, 'show_modal', False):
            show_results_rect = pygame.Rect(self.width//2 - 100, self.height - 80, 200, 50)
            self.draw_button(show_results_rect, self.get_str('show_results'), self.BLUE, self.LIGHT_BLUE, self.WHITE)

    def draw(self):
        """Render the current frame."""
        if self.state == "MENU":
            self.draw_menu()
        elif self.state == "PLAYING":
            self.draw_game()
            
        pygame.display.flip()

    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        while True:
            self.handle_events()
            self.draw()
            clock.tick(60) # Limit to 60 FPS
