import os
import h5py
import sys
import tpc5
import tkinter as tk
import numpy as np
from numbers import Number
from tkinter import ttk
from tkinter import filedialog
from tkinter import simpledialog
from tkinter.messagebox import askokcancel, showinfo, WARNING
from views.simple_plot_view import SimplePlotView
from views.point_selector_view import PointsSelectorView
from views.index_picker_view import IndexPickerView
from views.slope_analyzer_view import SlopeAnalyzerView
from views.dynamic_strain_arrival_picker_view import DynamicStrainArrivalPickerView
from views.czm_fitter_view import CZMFitterView


class EventExplorer:
    # Class constants for configuration
    WINDOW_GAP = 100
    WINDOW_WIDTH = 300
    WINDOW_TITLE = "Event Explorer"
    
    def __init__(self, root):
        self.root = root
        self.root.title(self.WINDOW_TITLE)

        # Set up window close handlers
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Store references to child windows
        self.child_windows = []

        # Geometry
        screen_height = self.root.winfo_screenheight()
        window_height = screen_height - (self.WINDOW_GAP * 3)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.geometry(f"{self.WINDOW_WIDTH}x{window_height}+{self.WINDOW_GAP}+{self.WINDOW_GAP}")
        
        # Force window to front
        self.root.lift()
        self.root.focus_force()

        # Treeview
        self.data_tree = None
        self.init_data_tree()

        # Context menus
        self.run_menu = tk.Menu(root, tearoff=0)
        self.run_menu.add_command(label="Pick Events", command=self.pick_events)
        self.event_menu = tk.Menu(root, tearoff=0)
        self.event_menu.add_command(label="Pick Arrivals", command=self.pick_strain_array_arrivals)
        self.event_menu.add_command(label="Fit Cohesive Zone Model", command=self.fit_cohesive_zone_model)
        self.event_array_menu = tk.Menu(root, tearoff=0)
        self.event_array_menu.add_command(label="Min/Max", command=self.min_max)
        self.array_menu = tk.Menu(root, tearoff=0)
        self.array_menu.add_command(label="Pick Indicies", command=self.pick_indicies)
        self.array_menu.add_command(label="Extract Slopes", command=self.extract_slope)
        self.array_menu.add_command(label="Extract Run", command=self.pick_run)
        self.event_indices_menu = tk.Menu(root, tearoff=0)
        self.event_indices_menu.add_command(label="Extract Events", command=self.extract_events)
        self.string_menu =  tk.Menu(root, tearoff=0)
        self.string_menu.add_command(label="Edit String", command=self.edit_string)

        # Buttons
        self.open_button = tk.Button(root, text="Load", command=self.load_file)
        self.open_button.grid(row=1, column=0, padx=2, pady=2, sticky="w")

        self.plot_button = tk.Button(root, text="Refresh", command=self.refresh_tree)
        self.plot_button.grid(row=1, column=1, padx=2, pady=2, sticky="w")

        self.save_button = tk.Button(root, text="Save As", command=self.save_file, state="disabled")
        self.save_button.grid(row=1, column=3, padx=2, pady=2, sticky="e")

        # initialize
        self.data = None
        self.active_context_menu = None
        root.bind("<Delete>", self.on_delete)

    def on_closing(self):
        """Handle cleanup when the main window is closing"""
        try:
            # Close all child windows first
            for window in self.child_windows[:]:  # Create a copy of the list to avoid modification during iteration
                try:
                    if window.winfo_exists():
                        window.destroy()
                except Exception as e:
                    print(f"Error closing child window: {e}")
                self.child_windows.remove(window)
            
            # Clean up any open file handles
            if hasattr(self, 'data') and self.data is not None:
                # Close any open HDF5 files
                for key, value in self.data.items():
                    if isinstance(value, h5py.File):
                        try:
                            value.close()
                        except Exception as e:
                            print(f"Error closing HDF5 file: {e}")
            
            # Destroy the main window
            self.root.destroy()
            # Force Python to exit
            sys.exit(0)

        except Exception as e:
            print(f"Error during cleanup: {e}")
            # Ensure the window is destroyed even if there's an error
            self.root.destroy()
            sys.exit(1)

    def load_file(self):
        data_path = filedialog.askopenfilename(
            title="Select pre-processed file", 
            filetypes = (("NPZ File","*.npz"),("HDF5 File","*.h5 *.hdf5")))
        if data_path:
            if data_path.lower().endswith(".npz"):
                self.load_npz(data_path)
            elif data_path.lower().endswith(".h5"):
                self.load_hdf5(data_path)
            elif data_path.lower().endswith(".hdf5"):
                self.load_hdf5(data_path)
            else:
                print("File not supported.")
                return
            selection = self.data_tree.selection()
            for item in selection:
                self.data_tree.selection_remove(item)
            self.refresh_tree()
            self.data_path = data_path
            self.save_button.configure(state="normal")
            print(f"File loaded: {data_path}")
            # showinfo(title="Success", message=f"File \"{data_path}\" loaded.")

    
    def load_npz(self, data_path):
        self.data = np.load(data_path, allow_pickle=True)
        self.data = self.data["experiment"][()]


    def load_hdf5(self, data_path):
        h5data = h5py.File(data_path, 'r')
        self.data = dict()
        self.data["name"] = data_path.split("/")[-1].split(".")[0].split("_proc")[0].split("l")[0]
        for key in list(h5data.keys()):
            self.data[key] = np.array(h5data[key])


    def save_file(self):
        data_path = filedialog.asksaveasfilename(
            title="Save data file", 
            confirmoverwrite=True,
            defaultextension=".npz",
            filetypes = (("NPZ File","*.npz"), ("All Files", "*.*")))
        if data_path:
            # np.savez_compressed(data_path, exp=self.data)
            np.savez(data_path, experiment=self.data)
            print(f"File saved: {data_path}")
            showinfo(title="Success", message=f"File \"{data_path}\" saved.")


    def init_data_tree(self):
        if self.data_tree:
            self.data_tree.destroy()
        self.data_tree = ttk.Treeview(root)
        self.data_tree.grid(row=0, column=0, columnspan=4, padx=2, pady=2, sticky="nsew")
        self.data_tree.heading("#0", text="[Data File]", anchor="w")
        self.data_tree.bind("<Double-1>", self.on_double_click)
        self.data_tree.bind("<Button-1>", self.on_left_click)
        self.data_tree.bind("<Button-2>", self.on_right_click)
        self.data_tree.bind("<Button-3>", self.on_right_click)

    
    def refresh_tree(self):
        selected_item = self.data_tree.selection()[0] if self.data_tree.selection() else None
        if not self.data:
            print('No data loaded.')
            return
        self.init_data_tree()
        self.build_tree_dict(self.data, "")
        try:
            self.data_tree.focus(selected_item)
            self.data_tree.selection_set(selected_item)
            self.data_tree.see(selected_item)
        except:
            for item in self.data_tree.get_children(""):
                self.data_tree.item(item, open=True)
                # for lv2_item in self.data_tree.get_children(item):
                #     self.data_tree.item(lv2_item, open=True)
        

    def build_tree_dict(self, parent_dict, parent_iid):
        self.data_tree.heading("#0", text=self.data["name"], anchor="w")
        for item in parent_dict.keys():
            if type(parent_dict[item]) is str:
                label_text = '%s: %s' % (item, parent_dict[item])
            elif type(parent_dict[item]) is dict:
                label_text = item
            elif type(parent_dict[item]) is int or isinstance(parent_dict[item], np.integer):
                label_text = '%s: %d' % (item, parent_dict[item])
            elif isinstance(parent_dict[item], Number):
                label_text = '%s: %f' % (item, parent_dict[item])
            elif type(parent_dict[item]) is np.ndarray:
                label_text = '%s: array [%d]' % (item, len(parent_dict[item]))
            elif type(parent_dict[item]) is list:
                label_text = '%s: list [%d]' % (item, len(parent_dict[item]))
            elif type(parent_dict[item]) is range:
                label_text = '%s: range (%d:%d)' % (item, parent_dict[item].start, parent_dict[item].stop)
            else:
                label_text = '%s: %s' % (item, type(parent_dict[item]))
            iid = self.data_tree.insert(parent_iid, "end", text=label_text, open=False)
            if type(parent_dict[item]) is dict:
                self.build_tree_dict(parent_dict[item], iid)
            if type(parent_dict[item]) is np.ndarray or type(parent_dict[item]) is list:
                if len(parent_dict[item]) < 1000:
                    self.build_tree_array(parent_dict[item], iid)
    
    def build_tree_array(self, parent_array, parent_iid):
        for i in range(len(parent_array)):
            try:
                label_text ='[%d]: %s' % (i, parent_array[i]['name'])
            except:
                if type(parent_array[i]) is dict:
                    label_text = '[%d]: dict' % i
                elif type(parent_array[i]) is int or isinstance(parent_array[i], np.integer):
                    label_text = '[%d]: %d' % (i, parent_array[i])
                elif isinstance(parent_array[i], Number):
                    label_text = '[%d]: %f' % (i, parent_array[i])
                elif type(parent_array[i]) is np.ndarray or type(parent_array[i]) is list:
                    label_text = '[%d]: array [%d]' % (i, len(parent_array[i]))
                else:
                    label_text = '[%d]: %s' % (i, str(type(parent_array[i])))
            iid = self.data_tree.insert(parent_iid, "end", text=label_text, open=False)
            if type(parent_array[i]) is dict:
                self.build_tree_dict(parent_array[i], iid)
            if type(parent_array[i]) is np.ndarray or type(parent_array[i]) is list:
                if len(parent_array[i]) < 1000:
                    self.build_tree_array(parent_array[i], iid)

    def on_double_click(self, event):
        path, item = self.get_full_path()
        print(f"Double-clicked on item: {path}")
        data = self.get_data(self.data, path)
        if type(data) is np.ndarray:
            print(f"plotting {item}")
            view = SimplePlotView(self)
            view.ax.plot(data)
            view.ax.set_xlabel('index')
            view.ax.set_ylabel(item)
            view.ax.set_title(path.replace('/[', '['))
        elif type(data) is dict:
            print('dict')
        elif type(data) is list:
            print('list')
        else:
            print(data)

    def on_left_click(self, event):
        if self.active_context_menu:
            self.active_context_menu.unpost()

    def on_right_click(self, event):
        self.active_context_menu = None
        item = self.data_tree.selection()[0]
        if not item:
            return
        
        # data-structure-specific context menus
        item_label = self.data_tree.item(item)['text'].split(':')
        parent_name = self.data_tree.item(self.data_tree.parent(item))['text'].split(':')[0]
        grandparent_name = self.data_tree.item(self.data_tree.parent(self.data_tree.parent(item)))['text'].split(':')[0]
        if grandparent_name == "runs":
            if item_label[0] == "event_indices":
                self.active_context_menu = self.event_indices_menu
            elif len(item_label) > 1 and "array" in item_label[1]:
                self.active_context_menu = self.run_menu
        elif grandparent_name == "events":
            if len(item_label) > 1 and "array" in item_label[1]:
                self.active_context_menu = self.event_array_menu
            else:
                self.active_context_menu = self.event_menu
        elif parent_name == "events":
            self.active_context_menu = self.event_menu
        
        # general purpose context menus
        if not self.active_context_menu:
            path, *_ = self.get_full_path()
            data = self.get_data(self.data, path)
            if type(data) is str:
                self.active_context_menu = self.string_menu
            elif len(item_label) > 1 and "array" in item_label[1] and parent_name == "":
                self.active_context_menu = self.array_menu
        
        # post context menu
        if self.active_context_menu:
            self.active_context_menu.post(event.x_root, event.y_root)

    def has_child_name_contains(self, item_id, keyword):
        if not item_id:
            return False
        children = self.data_tree.get_children(item_id)
        for child_id in children:
            if keyword in self.data_tree.item(child_id, "text"):
                return True
        return False
    
    def has_child_named(self, item_id, name):
        if not item_id:
            return False
        children = self.data_tree.get_children(item_id)
        for child_id in children:
            if name == self.data_tree.item(child_id, "text").split(":")[0]:
                return True
        return False

    def get_full_path(self, item=None):
        if item is None:
            item = self.data_tree.selection()[0]
        parent_iid = self.data_tree.parent(item)
        node = []
        # go backward until reaching root
        while parent_iid != '':
            node.insert(0, self.clean_up_text(self.data_tree.item(parent_iid)['text']))
            parent_iid = self.data_tree.parent(parent_iid)
        i = self.clean_up_text(self.data_tree.item(item, "text"))
        return os.path.join(*node, i), i

    def clean_up_text(self, s):
        return s.split(':')[0].strip()

    def get_data(self, parent, path):
        paths = path.split('/')
        key = paths[0]
        if key[0] == '[' and key[-1] == ']':
            s = key.split(']')[0].split('[')[1]
            key = int(s)
        item = parent[key]
        if len(paths) == 1:
            return item
        else:
            return self.get_data(item, path[path.index('/')+1:])
    
    def set_data(self, parent, path, value, add_key=False):
        paths = path.split('/')
        key = paths[0]
        if key[0] == '[' and key[-1] == ']':
            s = key.split(']')[0].split('[')[1]
            key = int(s)
        if type(key) is int or key in parent:
            item = parent[key]
        elif add_key:
            parent[key] = None
            item = parent[key]
        else:
            raise Exception("key not found in data")
        
        if len(paths) == 1:
            parent[key] = value
        else:
            self.set_data(item, path[path.index('/')+1:], value, add_key)
        self.refresh_tree()
        
    def min_max(self):
        path, item = self.get_full_path()
        y = self.get_data(self.data, path)
        x = np.arange(len(y))
        idx_min = np.argmin(y)
        idx_max = np.argmax(y)
        picked_idx = [idx_max, idx_min]
        view = PointsSelectorView(self, x, y, picked_idx, add_remove_enabled=False,
                                 xlabel='index', ylabel=item, title=path)
        self.child_windows.append(view)
        
    def pick_events(self):
        path, item = self.get_full_path()
        y = self.get_data(self.data, path)
        x = np.arange(len(y))
        save_path = path[:path.rfind('/')+1] + "event_indices"
        parent_id = self.data_tree.parent(self.data_tree.selection()[0])
        if self.has_child_named(parent_id, "event_indices"):
            picked_idx = self.get_data(self.data, self.get_full_path(parent_id)[0] + "/event_indices")
        else:
            picked_idx = []
        view = PointsSelectorView(self, x, y, picked_idx, add_remove_enabled=True, 
                                 callback=lambda data: self.set_data(self.data, save_path, data, add_key=True),
                                 xlabel='index', ylabel=item, title=path)
        self.child_windows.append(view)
        
    def pick_strain_array_arrivals(self):
        path, item = self.get_full_path()
        run_idx = int(path[path.find('runs/[')+6:path.find(']/events')])
        temp = path[path.find('events/[')+8::]
        event_idx = int(temp[:temp.find(']')])
        view = DynamicStrainArrivalPickerView(self, run_idx, event_idx)
        self.child_windows.append(view)
        
    def fit_cohesive_zone_model(self):
        path, item = self.get_full_path()
        run_idx = int(path[path.find('runs/[')+6:path.find(']/events')])
        temp = path[path.find('events/[')+8::]
        event_idx = int(temp[:temp.find(']')])
        view = CZMFitterView(self, run_idx, event_idx)
        self.child_windows.append(view)

    def pick_indicies(self):
        item = self.data_tree.selection()[0]
        item_name = self.data_tree.item(item)['text'].split(':')[0]
        view = IndexPickerView(self, item_y=item_name)
        self.child_windows.append(view)

    def extract_slope(self):
        item = self.data_tree.selection()[0]
        item_name = self.data_tree.item(item)['text'].split(':')[0]
        view = SlopeAnalyzerView(self, item_y=item_name)
        self.child_windows.append(view)

    def extract_events(self):
        item = self.data_tree.selection()[0]
        parent = self.data_tree.parent(item)
        event_indices_path = self.get_full_path()[0]
        parent_path = self.get_full_path(parent)[0]
        events_path = f"{parent_path}/events"
        run_path = f"{parent_path}"
        if self.has_child_named(parent, "events"):
            ans = askokcancel(title="Confirmation", message=f"This procedure will replace all data in \"{events_path}\".", icon=WARNING)
            if not ans:
                return
        window = simpledialog.askfloat('Set event time window length', 'Please set the duration before and after the event to be extracted.', initialvalue=5)
        if window is None:
            print('Event extraction aborted.')
            return
        else:
            print(f'Window set to (-{window}, {window})')
        
        events = list()
        run = self.get_data(self.data, run_path)
        event_indices = self.get_data(self.data, event_indices_path)
        # f = h5py.File('data_'+self.data["name"]+'/'+run['strain']['filename'], 'r')
        f = h5py.File('./'+run['strain']['filename'], 'r')
        n_channels = tpc5.getNChannels(f)
        n_samples = tpc5.getNSamples(f, 1)
        TriggerSample = tpc5.getTriggerSample(f, 1, 1)
        SamplingRate = tpc5.getSampleRate(f, 1, 1)
        startTime = -TriggerSample / SamplingRate
        endTime = (n_samples - TriggerSample) / SamplingRate
        ts = np.arange(startTime, endTime, 1/SamplingRate)
        ts += run['strain']['time_offset'] + run['time'][0] - ts[0]

        for i in range(len(event_indices)):
            print(f'Extracting event {i+1}/{len(event_indices)}...')
            idx = event_indices[i]
            event = dict()
            event_time = run["time"][idx]
            idx_beg = np.argmin(np.abs(event_time - window - run["time"]))
            idx_end = np.argmin(np.abs(event_time + window - run["time"]))
            idx_event = range(idx_beg, idx_end + 1)
            event['event_time'] = event_time
            event['time'] = run['time'][idx_event]
            try:
                event['normal_stress'] = run['normal_stress'][idx_event]
                event['shear_stress'] = run['shear_stress'][idx_event]
                event['friction'] = run['friction'][idx_event]
                event['LP_displacement'] = run['LP_displacement'][idx_event]
                event['LP_velocity'] = run['LP_velocity'][idx_event]
                event['displacement'] = run['displacement'][idx_event]
                # event['Exy1'] = run['Exy1'][idx_event]

                idx_beg = np.argmin(np.abs(event_time - window - run['time'][0] - run['strain']['time'] - run['strain']['time_offset']))
                idx_end = np.argmin(np.abs(event_time + window - run['time'][0] - run['strain']['time'] - run['strain']['time_offset']))
                idx_event = range(idx_beg, idx_end + 1)
                event['strain'] = dict()
                event['strain']['filename_downsampled'] = run['strain']['filename_downsampled']
                event['strain']['filename'] = run['strain']['filename']
                event['strain']['time'] = run['time'][0] + run['strain']['time_offset'] + run['strain']['time'][idx_event]
                event['strain']['raw'] = run['strain']['raw'][:, idx_event]
                event['strain']['original'] = dict()
                time_before = event['event_time'] - window
                time_after = event['event_time'] + window
                idx_before = np.argmin(np.abs(ts - time_before))
                idx_after = np.argmin(np.abs(ts - time_after))
                tt = ts[idx_before:idx_after]
                y = np.zeros((n_channels, len(tt)))
                for i in range(n_channels):
                    print(f'Loading raw strain data {i+1}/{n_channels}')
                    y[i, :] = tpc5.getVoltageData(f, i + 1)[idx_before:idx_after]
                for i in range(y.shape[0]):
                    y[i, :] -= y[i, 0:int(y.shape[1] / 100)].mean()
                event['strain']['original']['time'] = tt
                event['strain']['original']['raw'] = y
            except:
                for key in run:
                    if key == "events":
                        continue
                    if type(run[key]) is np.ndarray or type(run[key]) is list:
                        event[key] = run[key][idx]
            events.append(event)
        
        self.set_data(self.data, events_path, events, add_key=True)
        # run.pop("event_indices")
        showinfo(title="Success", message=f"Events extracted.")
    
    def edit_string(self):
        path, item = self.get_full_path()
        data = self.get_data(self.data, path)

        new_string = simpledialog.askstring('Edit String', f'{path}', initialvalue=data)
        if new_string is None:
            print('Edit String aborted.')
            return
        else:
            self.set_data(self.data, path, new_string)



    def pick_run(self):
        item_id = self.data_tree.selection()[0]
        item_path, item_name = self.get_full_path(item_id)

        y = self.get_data(self.data, item_path)
        x = np.arange(len(y))
        picked_idx = [int(len(y)/3), int(len(y)/3*2)]
        view = PointsSelectorView(self, x, y, picked_idx, add_remove_enabled=False, 
                                 callback=lambda idx: self.extract_run(idx),
                                 xlabel='index', ylabel=item_name, title=item_path)
        self.child_windows.append(view)
        
    def extract_run(self, idx, name=None):
        run = dict()
        idx = range(idx[0], idx[-1]+1)
        if not "runs" in self.data:
            self.data["runs"] = list()
        if name is None:
            name = f"run{len(self.data['runs'])}"
        run["name"] = name

        for key in self.data:
            if key == "runs":
                continue
            if type(self.data[key]) is np.ndarray or type(self.data[key]) is list:
                run[key] = self.data[key][idx]
        self.data["runs"].append(run)
        self.refresh_tree()
        
    def on_delete(self, event):
        item_id = self.data_tree.selection()[0]
        item_path = self.get_full_path(item_id)[0]
        ans = askokcancel(title="Confirmation", message=f"This procedure will delete \"{item_path}\".", icon=WARNING)
        if not ans:
            return
        parent_id = self.data_tree.parent(item_id)
        parent_path = self.get_full_path(parent_id)[0]
        parent = self.get_data(self.data, parent_path)
        item_name = self.data_tree.item(item_id, "text").split(":")[0]
        if type(parent) is dict:
            parent.pop(item_name)
        elif type(parent) is list:
            parent.pop(int(item_name.split(']')[0].split('[')[1]))
        self.refresh_tree()
        

    # def on_test(self):
    #     selected_item = self.data_tree.selection()
    #     path, item = self.get_full_path()
    #     data = self.get_data(self.data, path)
    #     test_view = TestDataUpdatingView(self, data, path, self.set_data)


if __name__ == "__main__":
    root = tk.Tk()
    event_explorer = EventExplorer(root)
    root.mainloop()
