import os
import sys
import signal
import json 
import uuid
from functools import partial

# --- 0. PRE-LOAD WINDOW SETTINGS ---
def find_data_dir():
    home = os.path.expanduser("~")
    path = os.path.join(home, "batchflow-data")
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError: pass
    return path

DATA_DIR = find_data_dir()
SETTINGS_FILE = os.path.join(DATA_DIR, "batchflow_settings.json")

# TARGET MINIMUMS
MIN_WIDTH = 800
MIN_HEIGHT = 418

# Defaults
init_width = 800
init_height = 418
init_left = None
init_top = None

try:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            full_data = json.load(f)
            w_data = full_data.get('window', {})
            loaded_w = w_data.get('width', 800)
            loaded_h = w_data.get('height', 418)
            init_width = max(loaded_w, MIN_WIDTH)
            init_height = max(loaded_h, MIN_HEIGHT)
            init_left = w_data.get('left', None)
            init_top = w_data.get('top', None)
            print(f"[System] Loaded settings: {init_width}x{init_height}")
except Exception as e:
    print(f"[System] Could not load window settings: {e}")

# --- 1. CONFIG ---
os.environ['SDL_VIDEO_X11_WMCLASS'] = "BatchFlow"
# os.environ['KIVY_NO_CONSOLELOG'] = '1'

from kivy.config import Config

# Icon Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(current_dir, 'assets', 'batchflow.png')
Config.set('kivy', 'window_icon', icon_path)

Config.set('graphics', 'width', str(init_width))
Config.set('graphics', 'height', str(init_height))
Config.set('graphics', 'min_width', '800')
Config.set('graphics', 'min_height', '418')
Config.set('graphics', 'resizable', '1') 

if init_left is not None and init_top is not None:
    Config.set('graphics', 'position', 'custom')
    Config.set('graphics', 'left', str(init_left))
    Config.set('graphics', 'top', str(init_top))

Config.set('input', 'mouse', 'mouse,disable_multitouch')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.properties import ObjectProperty, StringProperty, ListProperty, BooleanProperty, DictProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.core.window import Window

# --- IMPORT LOGIC ---
from batchflow_logic import BatchManager

# --- SIGNAL HANDLING ---
def handle_signal(signum, frame):
    os._exit(0)
signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# --- LOAD KV ---
kv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'batchflow_ui.kv')
try:
    Builder.load_file(kv_path)
except Exception as e:
    print(f"CRITICAL: Could not load KV file: {e}")
    sys.exit(1)

# --- WIDGET CLASSES ---

class HeaderButton(Button):
    column_ref = ObjectProperty(None)
    _click_event = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.is_double_tap:
                if self._click_event:
                    self._click_event.cancel()
                    self._click_event = None
                if self.column_ref:
                    self.column_ref.open_rename_popup()
            else:
                self._click_event = Clock.schedule_once(self.do_single_click, 0.25)
            return True
        return super().on_touch_down(touch)

    def do_single_click(self, dt):
        if self.column_ref:
            self.column_ref.toggle_collapse()

class TrashDock(BoxLayout):
    pass

class ConfirmPopupContent(BoxLayout):
    cancel_func = ObjectProperty(None)
    confirm_func = ObjectProperty(None)

class RenamePopup(Popup):
    save_func = ObjectProperty(None)
    cancel_func = ObjectProperty(None)
    def on_text_change(self, instance, value):
        if len(value) > 24: instance.text = value[:24]

class SourceSelectPopup(Popup):
    use_local = BooleanProperty(True)
    use_lite = BooleanProperty(False)
    use_monitor = BooleanProperty(False)
    has_lite = BooleanProperty(False)
    has_monitor = BooleanProperty(False)

    def on_open(self):
        app = App.get_running_app()
        mgr = app.manager
        self.use_local = mgr.source_settings.get('use_local', True)
        self.use_lite = mgr.source_settings.get('use_lite', False)
        self.use_monitor = mgr.source_settings.get('use_monitor', False)
        self.has_lite = mgr.has_lite
        self.has_monitor = mgr.has_monitor

    def on_toggle(self, key, value):
        app = App.get_running_app()
        mgr = app.manager
        mgr.source_settings[key] = value
        mgr.save_workflow()
        mgr.load_library()
        app.refresh_ui()

# --- NEW: IN-COLUMN PANELS ---

class BeverageSelectRow(Button):
    pass

class StyleSelectRow(Button):
    pass

class BeverageSelectorPanel(BoxLayout):
    column_ref = ObjectProperty(None)
    
    def cancel(self):
        if self.column_ref:
            self.column_ref.show_cards()
            
    def create_new(self):
        if self.column_ref:
            self.column_ref.show_editor_new()

class BeverageStyleSelectorPanel(BoxLayout):
    column_ref = ObjectProperty(None)
    
    def cancel(self):
        if self.column_ref:
            self.column_ref.return_to_editor()

class BeverageEditorPanel(BoxLayout):
    column_ref = ObjectProperty(None)
    bev_id = StringProperty("")
    bev_name = StringProperty("")
    bev_style = StringProperty("Select Style")
    bev_abv = NumericProperty(0.0)
    bev_ibu = NumericProperty(0)
    
    def reset_fields(self):
        self.bev_id = ""
        self.bev_name = ""
        self.bev_style = "Select Style"
        self.bev_abv = 0.0
        self.bev_ibu = 0
        if 'sm_delete' in self.ids:
            self.ids.sm_delete.current = 'btn_delete'

    def cancel(self):
        if self.column_ref:
            if self.bev_id:
                self.column_ref.show_cards()
            else:
                self.column_ref.show_selector()
            
    def open_style_selector(self):
        if self.column_ref:
            self.column_ref.open_style_selector()

    def toggle_delete_mode(self, confirm_state):
        if 'sm_delete' in self.ids:
            self.ids.sm_delete.transition.direction = 'left' if confirm_state else 'right'
            self.ids.sm_delete.current = 'confirm_delete' if confirm_state else 'btn_delete'

    def confirm_delete(self):
        app = App.get_running_app()
        if app.manager.delete_local_beverage(self.bev_id):
            app.manager.remove_batch_globally(self.bev_id)
            if self.column_ref:
                self.column_ref.show_cards()
            app.refresh_ui()

    def save(self):
        name = self.bev_name.strip()
        if not name: return 

        target_id = self.bev_id if self.bev_id else str(uuid.uuid4())

        new_bev = {
            "id": target_id,
            "name": name,
            "bjcp": self.bev_style if self.bev_style != "Select Style" else "",
            "abv": "{:.1f}".format(self.bev_abv) if self.bev_abv > 0 else "",
            "ibu": int(self.bev_ibu) if self.bev_ibu > 0 else "",
            "srm": 5, 
            "description": ""
        }

        app = App.get_running_app()
        if app.manager:
            success = app.manager.save_local_beverage(new_bev)
            if success:
                if self.column_ref and not self.bev_id:
                    app.manager.add_batch(name, self.column_ref.stage_key)
                app.refresh_ui()
                if self.column_ref:
                    self.column_ref.show_cards()

class BatchCard(BoxLayout):
    batch_id = StringProperty("")
    stage_key = StringProperty("")
    bv_name = StringProperty("")
    bv_style = StringProperty("")
    bv_abv = StringProperty("--")
    bv_ibu = StringProperty("--")
    bv_name_color = ListProperty([1, 1, 1, 1])
    background_color = ListProperty([0.2, 0.2, 0.2, 1])
    is_dragging = BooleanProperty(False)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.is_double_tap:
                app = App.get_running_app()
                data = app.manager.beverage_map.get(self.batch_id)
                if data and data.get('_source') == 'local':
                    if self.stage_key in app.columns:
                        app.columns[self.stage_key].open_editor_existing(self.batch_id)
                return True
            touch.grab(self)
            self._drag_touch_offset = (self.x - touch.x, self.y - touch.y)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if not self.is_dragging:
                self.start_dragging(touch)
            if self.parent == App.get_running_app().root:
                self.pos = (touch.x + self._drag_touch_offset[0], 
                            touch.y + self._drag_touch_offset[1])
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self.is_dragging:
                self.stop_dragging(touch)
            return True
        return super().on_touch_up(touch)

    def start_dragging(self, touch):
        self.is_dragging = True
        self.opacity = 0.8
        app = App.get_running_app()
        if app.trash_dock:
            app.trash_dock.opacity = 1
        win_pos = self.to_window(*self.pos)
        if self.parent:
            self.parent.remove_widget(self)
        app.root.add_widget(self)
        self.size_hint = (None, None)
        self.width = 260
        self.height = 110
        self.pos = win_pos

    def stop_dragging(self, touch=None):
        self.is_dragging = False
        self.opacity = 1.0 
        app = App.get_running_app()
        if app.trash_dock:
            app.trash_dock.opacity = 0
        self._handle_drop(touch)
        if self.parent:
            self.parent.remove_widget(self)

    def _handle_drop(self, touch=None):
        app = App.get_running_app()
        if not app: return

        if touch: cx, cy = touch.pos
        else: cx, cy = self.center
        
        target_col = None
        if app.trash_dock.collide_point(cx, cy):
            self.show_delete_confirmation()
            return

        for key, col_widget in app.columns.items():
            if col_widget.collide_point(cx, cy):
                target_col = col_widget
                break
        
        if target_col:
            if target_col.is_collapsed:
                container = target_col.ids.card_container
                insert_idx = len(container.children)
            else:
                container = target_col.ids.card_container
                existing_cards = container.children
                sorted_cards = sorted(
                    existing_cards, 
                    key=lambda c: c.to_window(c.x, c.y)[1], 
                    reverse=True
                )
                insert_idx = len(sorted_cards)
                for i, card in enumerate(sorted_cards):
                    _, card_y = card.to_window(card.x, card.y)
                    card_cy = card_y + (card.height / 2)
                    if cy > card_cy:
                        insert_idx = i
                        break
            
            success = app.manager.move_batch_drag(
                self.batch_id, self.stage_key, target_col.stage_key, target_index=insert_idx
            )
            if not success: app.refresh_ui()
        else:
            app.refresh_ui()

    def show_delete_confirmation(self):
        app = App.get_running_app()
        col_name = app.manager.column_titles.get(self.stage_key, "list")
        msg = f"Remove {self.bv_name} from the {col_name} list?"
        content = ConfirmPopupContent()
        content.ids.msg_label.text = msg
        popup = Popup(title="Confirmation", content=content, size_hint=(None, None), size=(500, 300), auto_dismiss=False)
        def do_cancel():
            popup.dismiss()
            app.refresh_ui()
        def do_delete():
            popup.dismiss()
            app.manager.remove_batch(self.batch_id, self.stage_key)
            app.refresh_ui()
        content.cancel_func = do_cancel
        content.confirm_func = do_delete
        popup.open()

class StageColumn(BoxLayout):
    title = StringProperty("")
    vertical_title = StringProperty("") 
    stage_key = StringProperty("")
    available_beverages = ListProperty([])
    is_collapsed = BooleanProperty(False)

    def on_title(self, instance, value):
        self.vertical_title = "\n".join(list(value))

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        app = App.get_running_app()
        if app and app.manager:
            app.manager.set_column_state(self.stage_key, self.is_collapsed)
    
    # --- MODE SWITCHING LOGIC ---
    def open_selector(self):
        app = App.get_running_app()
        all_bevs = []
        if app.manager:
            app.manager.load_library()
            all_bevs = app.manager.all_beverages_list
            self.available_beverages = [b['name'] for b in all_bevs]
        
        panel = self.ids.selector_panel
        data_list = []
        
        for bev in all_bevs:
            b_name = bev.get('name', 'Unknown')
            src = bev.get('_source', 'local')
            bg_col = [0.2, 0.2, 0.2, 1]
            if src == 'lite': bg_col = [0.15, 0.25, 0.15, 1]
            elif src == 'monitor': bg_col = [0.25, 0.15, 0.15, 1]
                
            data_list.append({
                'text': b_name,
                'background_color': bg_col,
                'on_release': partial(self._select_beverage, b_name)
            })
            
        panel.ids.rv_options.data = data_list
        self.ids.sm_col.transition.direction = 'down'
        self.ids.sm_col.current = 'view_select'

    def show_cards(self):
        self.ids.sm_col.transition.direction = 'up'
        self.ids.sm_col.current = 'view_cards'
        
    def show_editor_new(self):
        panel = self.ids.editor_panel
        panel.reset_fields()
        self.ids.sm_col.transition.direction = 'left'
        self.ids.sm_col.current = 'view_create'

    def open_editor_existing(self, bev_id):
        app = App.get_running_app()
        data = app.manager.beverage_map.get(bev_id)
        if not data: return 
        
        panel = self.ids.editor_panel
        panel.reset_fields()
        panel.bev_id = bev_id 
        panel.bev_name = data.get('name', '')
        panel.bev_style = data.get('bjcp', 'Select Style')
        
        try: panel.bev_abv = float(data.get('abv', 0))
        except: panel.bev_abv = 0.0
            
        try: panel.bev_ibu = int(data.get('ibu', 0))
        except: panel.bev_ibu = 0
            
        self.ids.sm_col.transition.direction = 'left'
        self.ids.sm_col.current = 'view_create'
        
    def show_selector(self):
        self.ids.sm_col.transition.direction = 'right'
        self.ids.sm_col.current = 'view_select'

    def open_style_selector(self):
        app = App.get_running_app()
        styles = app.manager.bjcp_styles
        
        panel = self.ids.style_panel
        data_list = []
        for s in styles:
            data_list.append({
                'text': s,
                'on_release': partial(self._select_style, s)
            })
        panel.ids.rv_styles.data = data_list
        
        self.ids.sm_col.transition.direction = 'left'
        self.ids.sm_col.current = 'view_style'

    def return_to_editor(self):
        self.ids.sm_col.transition.direction = 'right'
        self.ids.sm_col.current = 'view_create'

    def _select_beverage(self, bev_name):
        app = App.get_running_app()
        if app.manager:
            app.manager.add_batch(bev_name, self.stage_key)
        self.show_cards()

    def _select_style(self, style_name):
        editor = self.ids.editor_panel
        editor.bev_style = style_name
        self.return_to_editor()

    def open_rename_popup(self):
        if self.is_collapsed: return
        popup = RenamePopup(title="Rename Column")
        input_widget = popup.ids.name_input
        input_widget.text = self.title
        
        def do_save():
            new_name = input_widget.text.strip()
            if new_name:
                app = App.get_running_app()
                app.manager.rename_column(self.stage_key, new_name)
                self.title = new_name
            popup.dismiss()
        
        def do_cancel(): popup.dismiss()
        popup.save_func = do_save
        popup.cancel_func = do_cancel
        popup.open()
        Clock.schedule_once(lambda dt: setattr(input_widget, 'focus', True), 0.1)

    def update_cards(self, batch_ids_list):
        container = self.ids.card_container
        container.clear_widgets()
        app = App.get_running_app()
        if not app or not app.manager: return

        for b_id in batch_ids_list:
            data = app.manager.beverage_map.get(b_id)
            # CHANGED: Skip hidden items instead of creating "Unknown" cards
            if not data: continue 
            
            card = BatchCard()
            card.batch_id = b_id
            card.stage_key = self.stage_key
            
            card.bv_name = data.get('name', 'Unknown')
            card.bv_style = data.get('bjcp', '')
            card.bv_abv = str(data.get('abv', '--'))
            val_ibu = data.get('ibu')
            card.bv_ibu = str(val_ibu) if val_ibu is not None else "--"
            card.bv_name_color = [1, 1, 1, 1]
            
            src = data.get('_source', 'local')
            if src == 'lite': card.background_color = [0.15, 0.25, 0.15, 1]
            elif src == 'monitor': card.background_color = [0.25, 0.15, 0.15, 1]
            else: card.background_color = [0.2, 0.2, 0.2, 1]
                
            container.add_widget(card)

class DashboardScreen(Screen):
    pass

class BatchFlowApp(App):
    manager = ObjectProperty(None)
    status_text = StringProperty("Initializing...")
    col_theme_blue = ListProperty([0.2, 0.8, 1, 1])
    columns = {} 
    trash_dock = ObjectProperty(None)

    def build(self):
        self.title = "BatchFlow"
        self.root_layout = FloatLayout()
        self.sm = ScreenManager()
        self.dashboard = DashboardScreen(name='dashboard')
        self.sm.add_widget(self.dashboard)
        self.root_layout.add_widget(self.sm)
        self.trash_dock = TrashDock()
        self.root_layout.add_widget(self.trash_dock)
        Clock.schedule_once(self.start_backend, 0.2)
        return self.root_layout

    def start_backend(self, dt=None):
        try:
            self.manager = BatchManager()
            self.status_text = "System Ready"
            self.init_ui_columns()
            self.manager.bind(rotation_list=self.refresh_ui)
            self.manager.bind(deck_list=self.refresh_ui)
            self.manager.bind(fermenting_list=self.refresh_ui)
            self.manager.bind(finishing_list=self.refresh_ui)
            self.refresh_ui()
            Clock.schedule_once(self.dismiss_splash, 0.5)
        except Exception as e:
            self.status_text = f"Error: {e}"
            print(f"Backend Error: {e}")

    def init_ui_columns(self):
        container = self.dashboard.ids.columns_container
        container.clear_widgets()
        self.columns = {}
        keys = ["rotation", "deck", "fermenting", "finishing"]
        bevs = [b['name'] for b in self.manager.all_beverages_list]
        for key in keys:
            col = StageColumn()
            col.title = self.manager.column_titles.get(key, key.capitalize())
            col.is_collapsed = self.manager.column_states.get(key, False)
            col.stage_key = key
            col.available_beverages = bevs
            container.add_widget(col)
            self.columns[key] = col

    def refresh_ui(self, *args):
        if not self.columns: return
        self.columns['rotation'].update_cards(self.manager.rotation_list)
        self.columns['deck'].update_cards(self.manager.deck_list)
        self.columns['fermenting'].update_cards(self.manager.fermenting_list)
        self.columns['finishing'].update_cards(self.manager.finishing_list)

    def open_source_popup(self):
        self.manager.load_library() 
        popup = SourceSelectPopup()
        popup.open()
        
    def dismiss_splash(self, dt):
        if hasattr(self, 'splash_queue'):
            self.splash_queue.put("STOP")

    def on_stop(self):
        try:
            save_w = max(Window.width, MIN_WIDTH)
            save_h = max(Window.height, MIN_HEIGHT)
            full_data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    try: full_data = json.load(f)
                    except: pass
            full_data['window'] = {
                'width': save_w,
                'height': save_h,
                'left': Window.left,
                'top': Window.top
            }
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(full_data, f, indent=4)
            print(f"[System] Saved window settings: {full_data['window']}")
        except Exception as e:
            print(f"[System] Failed to save window settings: {e}")

# --- SPLASH SCREEN PROCESS ---
def run_splash_screen(queue):
    import tkinter as tk
    try:
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        width = 300
        height = 80
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        root.configure(bg='#222222')
        frame = tk.Frame(root, bg='#222222', highlightbackground='#33CCFF', highlightthickness=2)
        frame.pack(fill='both', expand=True)
        lbl = tk.Label(frame, text="BatchFlow App Loading...", font=("Arial", 16, "bold"), fg="#33CCFF", bg="#222222")
        lbl.pack(expand=True)
        root.update()
        def check_kill():
            if not queue.empty(): root.destroy()
            else: root.after(100, check_kill)
        root.after(100, check_kill)
        root.mainloop()
    except Exception as e:
        print(f"Splash screen error: {e}")

if __name__ == '__main__':
    import multiprocessing
    splash_queue = multiprocessing.Queue()
    splash_process = multiprocessing.Process(target=run_splash_screen, args=(splash_queue,))
    splash_process.start()
    try:
        app = BatchFlowApp()
        app.splash_queue = splash_queue
        app.run()
    except KeyboardInterrupt:
        print("\nBatchFlow interrupted by user.")
    finally:
        if splash_process.is_alive():
            splash_process.terminate()
