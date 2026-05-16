import os, sys
from kivy.resources import resource_add_path
from plyer import accelerometer
if hasattr(sys, '_MEIPASS'):
    resource_add_path(os.path.join(sys._MEIPASS))

from kivy.config import Config
from kivy.core.audio import SoundLoader
Config.set('graphics', 'resizable', '1') 
Config.set('graphics', 'fullscreen', 'auto')

from kivy.lang import Builder
Builder.load_file("menu.kv")
from kivy.app import App
from kivy.graphics import Line, Quad, Triangle, Rectangle, InstructionGroup
from kivy.graphics.context_instructions import Color
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.clock import Clock
from kivy.uix.relativelayout import RelativeLayout
from kivy.core.window import Window
from kivy import platform
from transforms import transform, transform_perspective, transform_2d
from user_actions import on_keyboard_up, on_keyboard_down, on_touch_down, on_touch_up, keyboard_closed
import types
import random

# =====================================================================
# ⚙️ BẢNG ĐIỀU KHIỂN THÔNG SỐ GAME (TÙY CHỈNH MỌI THỨ Ở ĐÂY) ⚙️
# =====================================================================

# 1. HÌNH ẢNH & KÍCH THƯỚC
CONF_TOP_NARROW = 0.8       # Độ hẹp đỉnh hình thang (0.65 = Đỉnh túm lại nhỏ)
CONF_SHIP_SCALE = 50        # Kích thước nhân vật (120 = To và rõ ràng)
# --- THÊM 2 DÒNG NÀY ĐỂ CHỈNH VỊ TRÍ LÊN/XUỐNG ---
CONF_SHIP_OFFSET_Y = -0.1   # Chỉnh ảnh nhân vật LÊN/XUỐNG (Số dương là nhích lên, âm là nhích xuống. VD: 0.05)
CONF_OBS_OFFSET_Y = 0.0    # Chỉnh ảnh rào chắn LÊN/XUỐNG (Số dương là nhích lên. VD: 0.02)
# 2. TỐC ĐỘ CHẠY
CONF_START_SPEED = 0.3       # Tốc độ lúc mới bắt đầu
CONF_MAX_SPEED = 1.5         # Tốc độ tối đa giới hạn
CONF_SCORE_TO_SPEED_UP = 100  # Cứ đủ bao nhiêu điểm thì Lên Level? (Tăng tốc + Thêm khối đỏ)
CONF_SPEED_INC_VALUE = 0.05   # Mỗi Level cộng thêm bao nhiêu tốc độ?

# 3. VẬT LÝ & KỸ NĂNG
CONF_INVINCIBLE_TIME = 0.2   # Thời gian bất tử (giây) sau khi bấm nhảy

# 4. CHƯỚNG NGẠI VẬT (NEW)
CONF_START_OBSTACLES = 10     # Bắt đầu với 5 ô đỏ (Ít đi cho dễ thở)
CONF_OBS_INC_PER_LEVEL = 2   # Cứ lên 1 Level thì cộng thêm 2 ô đỏ xuất hiện
CONF_OBS_SPACING_MIN = 2     # Khoảng cách gần nhất giữa 2 ô đỏ (theo ô lưới)
CONF_OBS_SPACING_MAX = 4     # Khoảng cách xa nhất giữa 2 ô đỏ
# =====================================================================
# 4. CẢM BIẾN CHUYỂN ĐỘNG (CHƠI BẰNG ĐIỆN THOẠI)
# =====================================================================
CONF_ACCEL_JUMP_FORCE = 15.0  # Lực bật nhảy (Trọng lực bình thường là 9.8. Nhảy lên sẽ > 15)
CONF_ACCEL_DEADZONE = 4.0     # Sai số ngang: Nếu lực nghiêng < 4 thì coi là nhảy tại chỗ
CONF_ACCEL_COOLDOWN = 0.8     # Giây chờ: Ngăn việc 1 cú nhảy bị nhận diện thành 2-3 cú
CONF_INVERT_LEFT_RIGHT = False # Đổi thành True nếu bạn nhảy trái mà nhân vật sang phải
# =====================================================================
# =====================================================================


class MainWidget(RelativeLayout):
    current_lane = 0 

    is_jumping = False
    ship_jump_offset = 0
    jump_velocity = 0

    perspective_ponit_x = NumericProperty(0)
    perspective_ponit_y = NumericProperty(0)
    menu_widget = ObjectProperty(None)
    menu_title = StringProperty("S U B W A Y    G A L A X Y")
    menu_button_title = StringProperty("START")
    score_txt = StringProperty("SCORE : 0")

    V_NB_LINES = 4 
    V_LINES_SPACING = 0.35 # <--- BẠN CHỈNH SỐ NÀY ĐỂ THU HẸP ĐÁY HÌNH THANG
    vertical_lines =[]
    track_floor = None  # <---  (Biến lưu tấm thảm nền)
    H_NB_LINES = 15
    H_LINES_SPACING = 0.2
    horizontal_lines =[]

    current_offset_y = 0
    current_y_loop = 0
    current_offset_x = 0 

    current_nb_obstacles = CONF_START_OBSTACLES
    obstacles =[]
    obstacles_coordinates =[]

    SHIP_WIDTH = 0.1
    SHIP_HEIGHT = 0.035
    SHIP_BASE_Y = 0.15
    ship = None
    ship_coordinates =[(0,0),(0,0),(0,0)]
    SHIP_BASE_Y = 0.15
    ship = None
    ship_coordinates =[(0,0),(0,0),(0,0)]

    # --- THÊM CÁC BIẾN CHO ANIMATION NHÂN VẬT ---
    ship_frames =["images/run1.png", "images/run2.png", "images/run3.png", 
                   "images/run4.png", "images/run5.png", "images/run6.png", "images/run7.png"]
    current_frame_index = 0
    frame_timer = 0
    FRAME_RATE = 0.1  # Tốc độ chuyển ảnh (0.1 giây đổi 1 ảnh)
    # ---------------------------------------------
    state_game_over = False
    state_game_has_started = False

    sound_begin = None
    sound_galaxy = None
    sound_gameover_impact = None
    sound_gameover_voice = None
    sound_music1 = None
    sound_restart = None

    def __init__(self, **kwargs):
        super(MainWidget, self).__init__(**kwargs)
        self.transform = types.MethodType(transform, self)
        self.transform_perspective = types.MethodType(transform_perspective, self)
        self.transform_2d = types.MethodType(transform_2d, self)
        self.on_keyboard_up = types.MethodType(on_keyboard_up, self)
        self.on_keyboard_down = types.MethodType(on_keyboard_down, self)
        self.on_touch_down = types.MethodType(on_touch_down, self)
        self.on_touch_up = types.MethodType(on_touch_up, self)
        self.keyboard_closed = types.MethodType(keyboard_closed, self)

        self.init_vertical_lines()
        self.init_horizontal_lines()
        self.init_obstacles()
        self.init_ship()
        self.init_audio()

        if self.is_desktop():
            self._keyboard = Window.request_keyboard(self.keyboard_closed, self)
            self._keyboard.bind(on_key_down=self.on_keyboard_down)
            self._keyboard.bind(on_key_up=self.on_keyboard_up)

        Clock.schedule_interval(self.update, 1/60.0)
        if self.sound_galaxy: self.sound_galaxy.play()

        # --- KHỞI ĐỘNG CẢM BIẾN ---
        self.motion_cooldown = 0
        try:
            accelerometer.enable()
        except:
            print("Khong tim thay cam bien gia toc (Dang chay tren PC)")

    def reset_game(self):
        self.current_offset_y = 0
        self.current_y_loop = 0
        self.current_lane = 0
        self.current_offset_x = 0
        self.is_jumping = False
        self.ship_jump_offset = 0
        self.invincible_timer = 0
        
        self.current_nb_obstacles = CONF_START_OBSTACLES
        self.obstacles_coordinates =[]
        self.score_txt = "SCORE: 0"
        self.generate_obstacles()
        self.state_game_over = False

    @staticmethod
    def is_desktop():
        return platform in ('linux', 'win', "macosx")

    def init_audio(self):
        self.sound_begin = SoundLoader.load("audio/begin.wav")
        self.sound_galaxy = SoundLoader.load("audio/galaxy.wav")
        self.sound_gameover_impact = SoundLoader.load("audio/gameover_impact.wav")
        self.sound_gameover_voice = SoundLoader.load("audio/gameover_voice.wav")
        self.sound_music1 = SoundLoader.load("audio/music1.wav")
        self.sound_restart = SoundLoader.load("audio/restart.wav")

        if self.sound_music1: self.sound_music1.volume = 1
        if self.sound_galaxy: self.sound_galaxy.volume = .25
        if self.sound_gameover_impact: self.sound_gameover_impact.volume = .3
        if self.sound_gameover_voice: self.sound_gameover_voice.volume = .25
        if self.sound_restart: self.sound_restart.volume = .25
        if self.sound_begin: self.sound_begin.volume = .25

    def init_vertical_lines(self):
        with self.canvas:
            # 1. TRẢI TẤM THẢM NỀN MÀU ĐỎ GẠCH NẰM DƯỚI CÙNG
            Color(0.75, 0.25, 0.25) 
            self.track_floor = Quad()
            
            # 2. VẼ CÁC ĐƯỜNG KẺ DỌC MÀU TRẮNG ĐÈ LÊN TRÊN (DÀY HƠN)
            Color(1, 1, 1) 
            for i in range(self.V_NB_LINES):
                self.vertical_lines.append(Line(width=2.5))  # <-- Thêm width=2.5 ở đây

    def init_horizontal_lines(self):
        with self.canvas:
            Color(1, 1, 1)
            for i in range(self.H_NB_LINES):
                self.horizontal_lines.append(Line(width=0.5))  # <-- Thêm width=2.5 ở đây

    def init_obstacles(self):
        # Tạo 2 lớp chứa rào chắn: Đằng sau và Đằng trước nhân vật
        self.obs_behind_group = InstructionGroup()
        self.obs_front_group = InstructionGroup()
        
        with self.canvas:
            # Lớp rào chắn ở xa phải được thêm vào Canvas TRƯỚC nhân vật
            self.canvas.add(self.obs_behind_group)
    def init_ship(self):
        with self.canvas:
            Color(1, 1, 1) 
            self.ship = Rectangle(source=self.ship_frames[0])
            
        # Lớp rào chắn ở gần phải được thêm vào Canvas SAU nhân vật
        self.canvas.add(self.obs_front_group)

    def generate_obstacles(self):
        # Xóa các ô đỏ đã bị trôi lại phía sau màn hình
        for i in range(len(self.obstacles_coordinates)-1, -1, -1):
            if self.obstacles_coordinates[i][1] < self.current_y_loop:
                del self.obstacles_coordinates[i]

        if len(self.obstacles_coordinates) > 0:
            last_y = self.obstacles_coordinates[-1][1]
        else:
            last_y = self.current_y_loop + 3 

        # Liên tục sinh thêm ô đỏ cho đến khi đủ số lượng hiện tại
        while len(self.obstacles_coordinates) < self.current_nb_obstacles:
            lane = random.randint(-1, 1) 
            # Khoảng cách giữa các ô đỏ được quy định trong Bảng điều khiển
            last_y += random.randint(CONF_OBS_SPACING_MIN, CONF_OBS_SPACING_MAX) 
            self.obstacles_coordinates.append((lane, last_y))

    def update(self, dt):
        self.check_motion(dt)
        time_factor = dt * 60

        if getattr(self, 'invincible_timer', 0) > 0:
            self.invincible_timer -= dt

        if self.is_jumping:
            self.invincible_timer = CONF_INVINCIBLE_TIME  
            self.ship_jump_offset += self.jump_velocity * time_factor
            self.jump_velocity -= 0.004 * time_factor 
            if self.ship_jump_offset <= 0:
                self.ship_jump_offset = 0
                self.is_jumping = False

        target_offset_x = -self.current_lane * self.V_LINES_SPACING * self.width
        self.current_offset_x += (target_offset_x - self.current_offset_x) * 0.2 * time_factor

        self.update_vertical_lines()
        self.update_horizontal_lines()
        self.update_obstacles()
        self.update_obstacles()
        self.update_ship(dt) # <--- Thêm dt vào đây

        if not self.state_game_over and self.state_game_has_started:
            
            # --- TÍNH TOÁN LEVEL, TỐC ĐỘ, SỐ KHỐI ĐỎ TỪ BẢNG ĐIỀU KHIỂN ---
            current_score = self.current_y_loop * 10
            speed_level = current_score // CONF_SCORE_TO_SPEED_UP  
            
            speed_multiplier = CONF_START_SPEED + (speed_level * CONF_SPEED_INC_VALUE)
            if speed_multiplier > CONF_MAX_SPEED:
                speed_multiplier = CONF_MAX_SPEED
                
            # LEVEL CÀNG CAO -> CỘNG THÊM CÀNG NHIỀU KHỐI ĐỎ
            self.current_nb_obstacles = CONF_START_OBSTACLES + (speed_level * CONF_OBS_INC_PER_LEVEL)
            # ------------------------------------------------------------------
                
            self.current_offset_y += (speed_multiplier * self.height) / 100 * time_factor

            spacing_y = self.H_LINES_SPACING * self.height
            while self.current_offset_y >= spacing_y:
                self.current_offset_y -= spacing_y
                self.current_y_loop += 1
                self.score_txt = f"SCORE: {self.current_y_loop * 10}"
                self.generate_obstacles()

        if not self.state_game_over and self.check_ship_collision():
            self.state_game_over = True
            self.menu_title = "B I  D U N G !   G A M E   O V E R"
            self.menu_button_title = "CHOI LAI"
            if self.sound_music1: self.sound_music1.stop()
            if self.sound_gameover_impact: self.sound_gameover_impact.play()
            Clock.schedule_once(self.play_game_over_sound, 1)
            self.menu_widget.opacity = 1

    def check_ship_collision(self):
        if getattr(self, 'invincible_timer', 0) > 0:
            return False

        # --- ĐỒNG BỘ: Cảm biến va chạm vô hình cũng phải dịch chuyển theo ảnh ---
        ship_y = (self.SHIP_BASE_Y + CONF_SHIP_OFFSET_Y) * self.height

        for (obs_x, obs_y) in self.obstacles_coordinates:
            if obs_y < self.current_y_loop:
                continue

            if self.current_lane == obs_x:
                spacing_y = self.H_LINES_SPACING * self.height
                
                # Tính tọa độ của đường kẻ ngang rào chắn
                obs_bottom_y = (obs_y - self.current_y_loop) * spacing_y - self.current_offset_y
                obs_top_y = obs_bottom_y + (spacing_y * 0.15)

                if obs_bottom_y <= ship_y <= obs_top_y:
                    return True
        return False


    def update_obstacles(self):
        # Đảm bảo luôn có đủ ảnh rào chắn trong bộ nhớ
        while len(self.obstacles) < len(self.obstacles_coordinates):
            self.obstacles.append(Rectangle(source="images/rao_chan.png"))

        # Xóa sạch 2 lớp hiển thị mỗi khung hình để sắp xếp lại từ đầu
        self.obs_behind_group.clear()
        self.obs_front_group.clear()
        
        # Thêm màu trắng vào đầu 2 nhóm để ảnh rào chắn không bị ám màu
        self.obs_behind_group.add(Color(1, 1, 1))
        self.obs_front_group.add(Color(1, 1, 1))

        # Lấy mốc tọa độ va chạm (đã tính bù trừ Offset) làm ranh giới phân lớp
        ship_y = (self.SHIP_BASE_Y + CONF_SHIP_OFFSET_Y) * self.height

        # LẶP NGƯỢC DANH SÁCH: Tính rào chắn ở XA nhất trước, GẦN nhất sau
        for i in range(len(self.obstacles_coordinates) - 1, -1, -1):
            obs_x, obs_y = self.obstacles_coordinates[i]
            
            x_min, y_min = self.get_tile_coordinates(obs_x, obs_y)
            x_max, _ = self.get_tile_coordinates(obs_x + 1, obs_y)
            center_x = (x_min + x_max) / 2
            
            screen_x, screen_y = self.custom_transform(center_x, y_min)
            px_left, _ = self.custom_transform(x_min, y_min)
            px_right, _ = self.custom_transform(x_max, y_min)
            
            lane_width = px_right - px_left
            obs_w = lane_width * 0.7 
            obs_h = obs_w * 0.2  
            
            visual_obs_y = screen_y + (self.height * CONF_OBS_OFFSET_Y)
            
            # Cập nhật kích thước và vị trí rào chắn
            self.obstacles[i].size = (obs_w, obs_h)
            self.obstacles[i].pos = (screen_x - obs_w / 2, visual_obs_y)
            
            # --- KIỂM TRA ĐỘ SÂU ĐỂ PHÂN LỚP HIỂN THỊ ---
            spacing_y = self.H_LINES_SPACING * self.height
            obs_bottom_y = (obs_y - self.current_y_loop) * spacing_y - self.current_offset_y
            
            if obs_bottom_y > ship_y:
                # Nếu rào chắn vẫn ở xa ranh giới -> Ném vào lớp đằng sau
                self.obs_behind_group.add(self.obstacles[i])
            else:
                # Nếu rào chắn đã lướt qua ranh giới -> Ném vào lớp đằng trước (đè lên nhân vật)
                self.obs_front_group.add(self.obstacles[i])

    def update_ship(self, dt):
        center_x = self.width / 2
        
        # --- ĐỒNG BỘ: Cộng offset vào ngay tọa độ logic trước khi biến đổi 3D ---
        base_y = self.height * (self.SHIP_BASE_Y + CONF_SHIP_OFFSET_Y + getattr(self, 'ship_jump_offset', 0))
        
        screen_x, screen_y = self.custom_transform(center_x, base_y)
        
        scale_factor = CONF_SHIP_SCALE / 100.0  
        ship_width = self.width * 0.08 * scale_factor
        ship_height = ship_width * 2.5 

        # Cập nhật vị trí và kích thước cho ảnh
        self.ship.size = (ship_width, ship_height)
        self.ship.pos = (screen_x - ship_width / 2, screen_y)

        # --- LOGIC ANIMATION CHẠY ---
        if not self.state_game_over and self.state_game_has_started and not self.is_jumping:
            self.frame_timer += dt
            if self.frame_timer >= self.FRAME_RATE:
                self.frame_timer = 0
                self.current_frame_index += 1
                if self.current_frame_index >= len(self.ship_frames):
                    self.current_frame_index = 0
                self.ship.source = self.ship_frames[self.current_frame_index]
        elif self.is_jumping:
            self.ship.source = self.ship_frames[2]

    def update_vertical_lines(self):
        # --- CẬP NHẬT TỌA ĐỘ TẤM THẢM NỀN ---
        xmin = self.get_line_x_from_index(-1)  # Mép trái
        xmax = self.get_line_x_from_index(2)   # Mép phải
        
        # Lấy 4 góc của con đường
        px1, py1 = self.custom_transform(xmin, 0)
        px2, py2 = self.custom_transform(xmax, 0)
        px3, py3 = self.custom_transform(xmax, self.height * 2.0)
        px4, py4 = self.custom_transform(xmin, self.height * 2.0)
        
        self.track_floor.points =[px1, py1, px2, py2, px3, py3, px4, py4]

        # --- CẬP NHẬT CÁC ĐƯỜNG KẺ TRẮNG ---
        for i, idx in enumerate([-1, 0, 1, 2]):
            line_x = self.get_line_x_from_index(idx)
            x1, y1 = self.custom_transform(line_x, 0)
            x2, y2 = self.custom_transform(line_x, self.height * 2.0) 
            self.vertical_lines[i].points =[x1, y1, x2, y2]

    def update_horizontal_lines(self):
        xmin = self.get_line_x_from_index(-1)
        xmax = self.get_line_x_from_index(2)

        for i in range(self.H_NB_LINES):
            line_y = self.get_line_y_from_index(i)
            x1, y1 = self.custom_transform(xmin, line_y)
            x2, y2 = self.custom_transform(xmax, line_y)
            self.horizontal_lines[i].points =[x1, y1, x2, y2]
    def check_motion(self, dt):
        # Trừ thời gian chờ để không bị nhận diện 1 cú nhảy nhiều lần
        if getattr(self, 'motion_cooldown', 0) > 0:
            self.motion_cooldown -= dt
            return

        try:
            val = accelerometer.acceleration
            if not val or val == (None, None, None):
                return
            x, y, z = val
        except:
            return

        # KHI CẦM ĐIỆN THOẠI NẰM NGANG TRƯỚC NGỰC:
        # X: là trục dọc (nhảy lên / rớt xuống)
        # Y: là trục ngang (nghiêng/nhảy sang trái, phải)
        
        # Nếu tổng lực dọc (X) vượt qua ngưỡng nhảy (impact)
        if abs(x) > CONF_ACCEL_JUMP_FORCE:
            
            # 1. BẮT ĐẦU GAME BẰNG CÁCH NHẢY LÊN
            if self.state_game_over or not self.state_game_has_started:
                self.on_menu_button_press()
                self.motion_cooldown = CONF_ACCEL_COOLDOWN
                return

            # 2. ĐANG CHƠI: PHÂN LOẠI HƯỚNG NHẢY
            # Kiểm tra xem lực ngang (Y) có vượt qua sai số (Deadzone) không
            if y > CONF_ACCEL_DEADZONE:
                # Nhảy sang ngang
                if CONF_INVERT_LEFT_RIGHT:
                    if self.current_lane > -1: self.current_lane -= 1
                else:
                    if self.current_lane < 1: self.current_lane += 1
                    
            elif y < -CONF_ACCEL_DEADZONE:
                # Nhảy sang ngang
                if CONF_INVERT_LEFT_RIGHT:
                    if self.current_lane < 1: self.current_lane += 1
                else:
                    if self.current_lane > -1: self.current_lane -= 1
                    
            else:
                # Lực ngang nằm trong sai số an toàn -> ĐỨNG YÊN NHẢY TẠI CHỖ
                if not getattr(self, 'is_jumping', False):
                    self.is_jumping = True
                    self.jump_velocity = 0.05

            # Reset thời gian chờ
            self.motion_cooldown = CONF_ACCEL_COOLDOWN    
    def get_line_x_from_index(self, index):
        center_line_x = self.perspective_ponit_x
        spacing = self.V_LINES_SPACING * self.width
        offset = index - 0.5
        line_x = center_line_x + (offset * spacing) + self.current_offset_x
        return line_x

    def get_line_y_from_index(self, index):
        spacing_y = self.H_LINES_SPACING * self.height
        line_y = index *spacing_y - self.current_offset_y
        return line_y

    def get_tile_coordinates(self, ti_x, ti_y):
        ti_y = ti_y - self.current_y_loop
        x = self.get_line_x_from_index(ti_x)
        y = self.get_line_y_from_index(ti_y)
        return x, y

    def play_game_over_sound(self, dt):
        if self.state_game_over and self.sound_gameover_voice:
            self.sound_gameover_voice.play()

    def on_menu_button_press(self):
        if self.state_game_over:
            if self.sound_restart: self.sound_restart.play()
        else :
            if self.sound_begin: self.sound_begin.play()
        if self.sound_music1: self.sound_music1.play()
        self.reset_game()
        self.state_game_has_started = True
        self.menu_widget.opacity = 0
        
    def custom_transform(self, x, y):
        center_x = self.width / 2
        
        horizon_y = self.height * 1.1 
        if y > horizon_y:
            y = horizon_y
            
        dist = horizon_y - y
        factor_y = (dist / horizon_y) ** 2 
        tr_y = horizon_y - (factor_y * horizon_y)
        
        factor_x = 1.0 - (CONF_TOP_NARROW * (tr_y / self.height))
        tr_x = center_x + (x - center_x) * factor_x
        
        return tr_x, tr_y

class GalaxyApp(App):
    pass

if __name__ == '__main__':
    GalaxyApp().run()
