import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import numpy as np
import os
from simplePlotView import SimplePlotView
# from testDataUpdatingView import TestDataUpdatingView
from pointsDraggingView import PointsDraggingView
from pointsPickingView import PointsPickingView

class DataViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Viewer")

        # Treeview to display files and folders
        self.data_tree = ttk.Treeview(root)
        self.data_tree.heading("#0", text="[Data File]", anchor="w")
        self.data_tree.pack(expand=tk.YES, fill=tk.BOTH)
        
        # Double-click callback on the Treeview item
        self.data_tree.bind("<Double-1>", self.on_double_click)

        # Right-click callback on the Treeview item
        self.data_tree.bind("<Button-2>", self.on_right_click)

        # Context menu
        self.context_menu = tk.Menu(root, tearoff=0)
        # self.context_menu.add_command(label="Test", command=self.on_test)
        self.context_menu.add_command(label="Min/Max", command=self.min_max)
        self.context_menu.add_command(label="Pick", command=self.pick)

        # Buttons
        self.open_button = tk.Button(
            root, text="Load", command=self.load_file)
        self.open_button.pack(side=tk.LEFT, padx=5)

        self.plot_button = tk.Button(
            root, text="Refresh", command=self.refresh_tree)
        self.plot_button.pack(side=tk.LEFT, padx=5)

        # initialize
        self.data = None

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
            elif type(parent_dict[item]) is int:
                label_text = '%s: %d' % (item, parent_dict[item])
            elif type(parent_dict[item]) is float:
                label_text = '%s: %f' % (item, parent_dict[item])
            elif type(parent_dict[item]) is np.float64:
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
                elif type(parent_array[i]) is np.float64:
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
            figure_view_window = tk.Toplevel(self.root)
            figure_view = SimplePlotView(figure_view_window)
            figure_view.ax.plot(data)
            figure_view.ax.set_xlabel('index')
            figure_view.ax.set_ylabel(item)
            figure_view.ax.set_title(path.replace('/[', '['))
        elif type(data) is dict:
            print('dict')
        elif type(data) is list:
            print('list')
        else:
            print(data)

    def on_right_click(self, event):
        item = self.data_tree.selection()
        if item:
            self.context_menu.post(event.x_root, event.y_root)

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
    
    def set_data(self, parent, path, value):
        paths = path.split('/')
        key = paths[0]
        if key[0] == '[' and key[-1] == ']':
            s = key.split(']')[0].split('[')[1]
            key = int(s)
        item = parent[key]

        print(f'set_data: {path} {value}')
        if len(paths) == 1:
            parent[key] = value
        else:
            self.set_data(item, path[path.index('/')+1:], value)
    
    def update_data(self, path, value):
        self.set_data(self.data, path, value)

    # def on_test(self):
    #     selected_item = self.data_tree.selection()
    #     path, item = self.get_full_path()
    #     data = self.get_data(self.data, path)
    #     test_view = TestDataUpdatingView(self, data, path, self.update_data)
        
    def min_max(self):
        path, item = self.get_full_path()
        y = self.get_data(self.data, path)
        x = np.arange(len(y))
        idx_min = np.argmin(y)
        idx_max = np.argmax(y)
        picked_idx = [idx_max, idx_min]
        pointsDraggingView = PointsDraggingView(root, x, y, picked_idx)
        
    def pick(self):
        path, item = self.get_full_path()
        y = self.get_data(self.data, path)
        # try:
        #     xpath = path[:path.rfind('/')+1] + "time"
        #     print(xpath)
        #     x = self.get_data(self.data, xpath)
        # except: 
        #     x = np.arange(len(y))
        x = np.arange(len(y))
        picked_idx = []
        pointsPickingView = PointsPickingView(root, x, y, picked_idx)
        


if __name__ == "__main__":
    root = tk.Tk()
    data_viewer = DataViewer(root)
    root.mainloop()
