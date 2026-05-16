from kivy.uix.relativelayout import RelativeLayout

def keyboard_closed(self):
    self._keyboard.unbind(on_key_down=self._on_keyboard_down)
    self._keyboard.bind(on_key_up=self.on_keyboard_up)
    self._keyboard = None

def on_keyboard_down(self, keyboard, keycode, text, modifiers):
    # Lách sang trái
    if keycode[1] == 'a' or keycode[1] == 'left':
        if self.current_lane > -1:
            self.current_lane -= 1
            
    # Lách sang phải
    elif keycode[1] == 'd' or keycode[1] == 'right':
        if self.current_lane < 1:
            self.current_lane += 1
            
    # Nhảy qua chướng ngại vật
    elif keycode[1] == 'spacebar' or keycode[1] == 'w' or keycode[1] == 'up':
        if not getattr(self, 'is_jumping', False):
            self.is_jumping = True
            self.jump_velocity = 0.05  # Lực nhảy
            
    return True

def on_keyboard_up(self, keyboard, keycode):
    pass

def on_touch_down(self, touch):
    if not self.state_game_over and self.state_game_has_started:
        if touch.x < self.width / 2:
            if self.current_lane > -1:
                self.current_lane -= 1
        else:
            if self.current_lane < 1:
                self.current_lane += 1
    return super(RelativeLayout, self).on_touch_down(touch)

def on_touch_up(self, touch):
    pass