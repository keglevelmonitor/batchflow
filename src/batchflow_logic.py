import json
import os
import re
from kivy.event import EventDispatcher
from kivy.properties import ListProperty, DictProperty, BooleanProperty

class BatchManager(EventDispatcher):
    # Reactive Properties
    rotation_list = ListProperty([])
    deck_list = ListProperty([])
    fermenting_list = ListProperty([])
    finishing_list = ListProperty([])
    
    column_titles = DictProperty({
        'rotation': 'Rotation',
        'deck': 'On Deck',
        'fermenting': 'Fermenting',
        'finishing': 'Finishing'
    })

    column_states = DictProperty({
        'rotation': False,
        'deck': False,
        'fermenting': False,
        'finishing': False
    })
    
    beverage_map = DictProperty({})
    all_beverages_list = ListProperty([])
    
    # The list used by the dropdown
    bjcp_styles = ListProperty([])
    
    source_settings = DictProperty({
        'use_local': True,
        'use_lite': True,
        'use_monitor': True
    })

    has_lite = BooleanProperty(False)
    has_monitor = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_dir = self._find_data_dir()
        self.settings_file = os.path.join(self.data_dir, "batchflow_settings.json")
        
        self.load_workflow()
        self.load_library()
        self.load_bjcp_styles()

    def _find_data_dir(self):
        home = os.path.expanduser("~")
        path = os.path.join(home, "batchflow-data")
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError: pass
        return path

    def load_bjcp_styles(self):
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'bjcp_styles.json'),
            os.path.join(self.data_dir, 'bjcp_styles.json'),
            "assets/bjcp_styles.json"
        ]
        
        raw_data = []
        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        content = json.load(f)
                        if isinstance(content, list):
                            raw_data = content
                        elif isinstance(content, dict):
                            for k in ['styles', 'beverages', 'entries', 'class']:
                                if k in content and isinstance(content[k], list):
                                    raw_data = content[k]
                                    break
                        if raw_data: break
                except Exception as e:
                    print(f"[Logic] Error loading BJCP from {p}: {e}")

        clean_list = []
        if raw_data:
            for item in raw_data:
                if isinstance(item, dict):
                    s_id = None
                    for key in ['id', 'number', 'code', 'style_id', 'bjcp', 'category', 'category_id']:
                        if key in item and item[key]:
                            val = str(item[key]).strip()
                            if len(val) < 6 and any(c.isdigit() for c in val):
                                s_id = val
                                break
                    s_name = item.get('name', '') or item.get('style', '') or item.get('title', '')
                    
                    if s_id and s_name:
                        clean_list.append(f"{s_id} - {s_name}")
                    elif s_name:
                        clean_list.append(s_name)
                elif isinstance(item, str):
                    clean_list.append(item)
        
        def bjcp_sort_key(entry):
            parts = re.split(r'[\s\-]+', entry, 1) 
            code = parts[0]
            match = re.match(r"(\d+)([A-Za-z]*)", code)
            if match:
                return (int(match.group(1)), match.group(2))
            return (9999, code)

        if clean_list:
            self.bjcp_styles = sorted(clean_list, key=bjcp_sort_key)
        else:
            self.bjcp_styles = ["1A - American Light Lager", "1B - American Lager", "18B - American Pale Ale", "21A - American IPA"]

    def load_library(self):
        home = os.path.expanduser("~")
        path_local = os.path.join(self.data_dir, "beverages_library.json")
        path_lite = os.path.join(home, "keglevel_lite-data", "beverages_library.json")
        path_monitor = os.path.join(home, "keglevel-data", "beverages_library.json")
        
        self.has_lite = os.path.exists(path_lite)
        self.has_monitor = os.path.exists(path_monitor)
        
        temp_map = {}
        
        def merge_file(filepath, source_tag):
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        bevs = data.get('beverages', [])
                        for b in bevs:
                            if 'id' in b:
                                b['_source'] = source_tag 
                                temp_map[b['id']] = b
                except Exception as e:
                    print(f"[Logic] Error loading {source_tag}: {e}")

        # 1. Load Local (Only if enabled)
        if self.source_settings.get('use_local', True):
            merge_file(path_local, 'local')
        
        # 2. Load Lite (if enabled)
        if self.source_settings.get('use_lite', False) and self.has_lite:
            merge_file(path_lite, 'lite')
            
        # 3. Load Monitor (if enabled)
        if self.source_settings.get('use_monitor', False) and self.has_monitor:
            merge_file(path_monitor, 'monitor')

        self.beverage_map = temp_map
        self.all_beverages_list = sorted(temp_map.values(), key=lambda x: x.get('name', ''))

    def save_local_beverage(self, bev_data):
        path_local = os.path.join(self.data_dir, "beverages_library.json")
        data = {"beverages": []}
        
        if os.path.exists(path_local):
            try:
                with open(path_local, 'r') as f:
                    data = json.load(f)
            except Exception:
                data = {"beverages": []}
        
        if 'beverages' not in data:
            data['beverages'] = []
            
        existing_idx = -1
        for i, b in enumerate(data['beverages']):
            if b.get('id') == bev_data.get('id'):
                existing_idx = i
                break
        
        if existing_idx >= 0:
            data['beverages'][existing_idx] = bev_data
        else:
            data['beverages'].append(bev_data)
            
        try:
            with open(path_local, 'w') as f:
                json.dump(data, f, indent=4)
            self.load_library()
            return True
        except Exception as e:
            print(f"[Logic] Error saving beverage: {e}")
            return False

    def delete_local_beverage(self, bev_id):
        path_local = os.path.join(self.data_dir, "beverages_library.json")
        if not os.path.exists(path_local): return False
        
        try:
            with open(path_local, 'r') as f:
                data = json.load(f)
            
            original_len = len(data.get('beverages', []))
            data['beverages'] = [b for b in data.get('beverages', []) if b.get('id') != bev_id]
            
            if len(data['beverages']) < original_len:
                with open(path_local, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"[Logic] Deleted beverage {bev_id}")
                self.load_library()
                return True
        except Exception as e:
            print(f"[Logic] Delete Error: {e}")
        return False

    def remove_batch_globally(self, batch_id):
        changed = False
        for l in [self.rotation_list, self.deck_list, self.fermenting_list, self.finishing_list]:
            if batch_id in l:
                l.remove(batch_id)
                changed = True
        if changed:
            self.save_workflow()
            print(f"[Logic] Removed batch {batch_id} from all columns.")

    def load_workflow(self):
        defaults = {"on_rotation": [], "on_deck": [], "fermenting": [], "lagering_or_finishing": []}
        default_titles = {'rotation': 'Rotation', 'deck': 'On Deck', 'fermenting': 'Fermenting', 'finishing': 'Finishing'}
        default_states = {'rotation': False, 'deck': False, 'fermenting': False, 'finishing': False}
        default_sources = {'use_local': True, 'use_lite': True, 'use_monitor': True}

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    self.rotation_list = data.get('columns', defaults).get('on_rotation', [])
                    self.deck_list = data.get('columns', defaults).get('on_deck', [])
                    self.fermenting_list = data.get('columns', defaults).get('fermenting', [])
                    self.finishing_list = data.get('columns', defaults).get('lagering_or_finishing', [])
                    
                    self.column_titles = data.get('titles', default_titles)
                    self.column_states = data.get('states', default_states)
                    self.source_settings = data.get('library_sources', default_sources)
            except Exception:
                self._set_defaults(defaults, default_titles, default_states, default_sources)
        else:
            self._set_defaults(defaults, default_titles, default_states, default_sources)

    def _set_defaults(self, defaults, titles, states, sources):
        self.rotation_list = defaults['on_rotation']
        self.deck_list = defaults['on_deck']
        self.fermenting_list = defaults['fermenting']
        self.finishing_list = defaults['lagering_or_finishing']
        self.column_titles = titles
        self.column_states = states
        self.source_settings = sources

    def save_workflow(self):
        current_data = {}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    current_data = json.load(f)
            except Exception:
                current_data = {}

        current_data["columns"] = {
            "on_rotation": list(self.rotation_list),
            "on_deck": list(self.deck_list),
            "fermenting": list(self.fermenting_list),
            "lagering_or_finishing": list(self.finishing_list)
        }
        current_data["titles"] = dict(self.column_titles)
        current_data["states"] = dict(self.column_states)
        current_data["library_sources"] = dict(self.source_settings)

        try:
            with open(self.settings_file, 'w') as f:
                json.dump(current_data, f, indent=4)
        except Exception as e:
            print(f"[Logic] Save Error: {e}")

    def rename_column(self, key, new_title):
        if key in self.column_titles:
            self.column_titles[key] = new_title
            self.save_workflow()

    def set_column_state(self, key, is_collapsed):
        if key in self.column_states:
            self.column_states[key] = is_collapsed
            self.save_workflow()

    def add_batch(self, beverage_name, target_list_name):
        found_id = None
        for b in self.all_beverages_list:
            if b.get('name') == beverage_name:
                found_id = b.get('id'); break
        
        if not found_id: return

        if target_list_name == 'rotation': self.rotation_list.insert(0, found_id)
        elif target_list_name == 'deck': self.deck_list.insert(0, found_id)
        elif target_list_name == 'fermenting': self.fermenting_list.insert(0, found_id)
        elif target_list_name == 'finishing': self.finishing_list.insert(0, found_id)
        self.save_workflow()

    def remove_batch(self, batch_id, list_name):
        target = self._get_list_by_name(list_name)
        if target is not None and batch_id in target:
            target.remove(batch_id)
            self.save_workflow()

    def move_batch_drag(self, batch_id, source_name, dest_name, target_index=0):
        source = self._get_list_by_name(source_name)
        dest = self._get_list_by_name(dest_name)

        if source is not None and dest is not None:
            if batch_id in source:
                source.remove(batch_id)
                if target_index < 0: target_index = 0
                if target_index > len(dest): target_index = len(dest)
                dest.insert(target_index, batch_id)
                self.save_workflow()
                return True
        return False

    def _get_list_by_name(self, name):
        if name == 'rotation': return self.rotation_list
        elif name == 'deck': return self.deck_list
        elif name == 'fermenting': return self.fermenting_list
        elif name == 'finishing': return self.finishing_list
        return None
