import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import numpy as np
import os
from numbers import Number
from views.simplePlottingView import SimplePlottingView
from views.pointsPickingView import PointsPickingView
from views.dynamicStrainArrivalPickingView import DynamicStrainArrivalPickingView

class EventExplorer:
    def __init__(self, root):
        self.root = root
        self.root.title("Event Explorer")
        self.root.geometry(f"300x{self.root.winfo_screenheight()}+0+0")

        # Treeview to display files and folders
        self.data_tree = ttk.Treeview(root)
        self.data_tree.heading("#0", text="[Data File]", anchor="w")
        self.data_tree.pack(expand=tk.YES, fill=tk.BOTH)
        
        # Click callback on the Treeview item
        self.data_tree.bind("<Double-1>", self.on_double_click)
        self.data_tree.bind("<Button-1>", self.on_left_click)
        self.data_tree.bind("<Button-2>", self.on_right_click)
        self.data_tree.bind("<Button-3>", self.on_right_click)

        # Context menus
        self.run_menu = tk.Menu(root, tearoff=0)
        self.run_menu.add_command(label="Pick Events", command=self.pick_events)
        self.event_menu = tk.Menu(root, tearoff=0)
        self.event_menu.add_command(label="Pick Arrivals", command=self.pick_strain_array_arrivals)
        self.event_array_menu = tk.Menu(root, tearoff=0)
        self.event_array_menu.add_command(label="Min/Max", command=self.min_max)

        # Buttons
        self.open_button = tk.Button(
            root, text="Load", command=self.load_file)
        self.open_button.pack(side=tk.LEFT, padx=2)

        self.plot_button = tk.Button(
            root, text="Refresh", command=self.refresh_tree)
        self.plot_button.pack(side=tk.LEFT, padx=2)

        self.save_button = tk.Button(
            root, text="Save As", command=self.save_file, state="disabled")
        self.save_button.pack(side=tk.RIGHT, padx=2)

        # initialize
        self.data = None
        self.active_context_menu = None


    def load_file(self):
        data_path = filedialog.askopenfilename(
            title="Select pre-processed file", 
            filetypes = (("NPZ File","*.npz"),("all files","*.*")))
        if data_path:
            # Clear existing tree items
            self.data_tree.delete(*self.data_tree.get_children())

            # Display files and folders in the treeview
            self.data = np.load(data_path, allow_pickle=True)
            self.data = {'exp': self.data['exp'][()]}
            self.refresh_tree()
            self.data_path = data_path
            self.save_button.configure(state="active")


    def save_file(self):
        data_path = filedialog.asksaveasfilename(
            title="Save data file", 
            confirmoverwrite=True,
            defaultextension=".npz",
            filetypes = (("NPZ File","*.npz"),("all files","*.*")))
        if data_path:
            np.savez(data_path, exp=self.data["exp"])
            print(f"File saved: {data_path}")

    
    def refresh_tree(self):
        if not self.data:
            print('No data loaded.')
            return
        self.data_tree.delete(*self.data_tree.get_children())
        self.build_tree_dict(self.data, "")
        for item in self.data_tree.get_children(""):
            self.data_tree.item(item, open=True)
            for lv2_item in self.data_tree.get_children(item):
                self.data_tree.item(lv2_item, open=True)
        

    def build_tree_dict(self, parent_dict, parent_iid):
        self.data_tree.heading("#0", text=self.data['exp']['name'], anchor="w")
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
                if len(parent_dict[item]) < 100:
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
                if len(parent_array[i]) < 100:
                    self.build_tree_array(parent_array[i], iid)

    def on_double_click(self, event):
        path, item = self.get_full_path()
        print(f"Double-clicked on item: {path}")
        data = self.get_data(self.data, path)
        if type(data) is np.ndarray:
            print(f"plotting {item}")
            view = SimplePlottingView(self)
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
        item = self.data_tree.selection()[0]
        if item:
            item_name = self.data_tree.item(item)['text'].split(':')[0]
            parent_name = self.data_tree.item(self.data_tree.parent(item))['text'].split(':')[0]
            grandparent_name = self.data_tree.item(self.data_tree.parent(self.data_tree.parent(item)))['text'].split(':')[0]
            if grandparent_name == "runs":
                item_label = self.data_tree.item(item)['text'].split(':')
                if len(item_label) > 1 and "array" in item_label[1]:
                    self.active_context_menu = self.run_menu
                    self.active_context_menu.post(event.x_root, event.y_root)
            elif grandparent_name == "events":
                item_label = self.data_tree.item(item)['text'].split(':')
                if len(item_label) > 1 and "array" in item_label[1]:
                    self.active_context_menu = self.event_array_menu
                    self.active_context_menu.post(event.x_root, event.y_root)
                else:
                    self.active_context_menu = self.event_menu
                    self.active_context_menu.post(event.x_root, event.y_root)
            elif parent_name == "events":
                self.active_context_menu = self.event_menu
                self.active_context_menu.post(event.x_root, event.y_root)
            

    def get_full_path(self):
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
        
    def min_max(self):
        path, item = self.get_full_path()
        y = self.get_data(self.data, path)
        x = np.arange(len(y))
        idx_min = np.argmin(y)
        idx_max = np.argmax(y)
        picked_idx = [idx_max, idx_min]
        view = PointsPickingView(self, x, y, picked_idx, add_remove_enabled=False,
                                 xlabel='index', ylabel=item, title=path)
        
    def pick_events(self):
        path, item = self.get_full_path()
        y = self.get_data(self.data, path)
        # try:
        #     xpath = path[:path.rfind('/')+1] + "time"
        #     print(xpath)
        #     x = self.get_data(self.data, xpath)
        # except: 
        #     x = np.arange(len(y))
        x = np.arange(len(y))
        save_path = path[:path.rfind('/')+1] + "event_indices"
        picked_idx = []
        view = PointsPickingView(self, x, y, picked_idx, add_remove_enabled=True, 
                                 callback=lambda data: self.set_data(self.data, save_path, data, add_key=True),
                                 xlabel='index', ylabel=item, title=path)
        
    def pick_strain_array_arrivals(self):
        path, item = self.get_full_path()
        run_idx = int(path[path.find('runs/[')+6:path.find(']/events')])
        temp = path[path.find('events/[')+8::]
        event_idx = int(temp[:temp.find(']')])
        view = DynamicStrainArrivalPickingView(self, run_idx, event_idx)

    # def on_test(self):
    #     selected_item = self.data_tree.selection()
    #     path, item = self.get_full_path()
    #     data = self.get_data(self.data, path)
    #     test_view = TestDataUpdatingView(self, data, path, self.set_data)


if __name__ == "__main__":
    root = tk.Tk()
    data_viewer = EventExplorer(root)
    root.mainloop()
    if root:
        root.destroy()
