import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import numpy as np
import os
import simplePlotView

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

        # Buttons
        self.open_button = tk.Button(
            root, text="Browse", command=self.browse_file)
        self.open_button.pack(side=tk.LEFT, padx=5)

        # self.plot_button = tk.Button(
        #     root, text="Plot Array", command=self.plot_array)
        # self.plot_button.pack(side=tk.LEFT, padx=5)

    def browse_file(self):
        data_path = filedialog.askopenfilename(
            title="Select pre-processed file", 
            filetypes = (("NPZ File","*.npz"),("all files","*.*")))
        if data_path:
            # Clear existing tree items
            self.data_tree.delete(*self.data_tree.get_children())

            # Display files and folders in the treeview
            self.data = np.load(data_path, allow_pickle=True)
            self.data = {'exp': self.data['exp'][()]}
            self.data_tree.heading("#0", text=self.data['exp']['name'], anchor="w")
            self.display_dict_structure(self.data, "")

    def display_dict_structure(self, parent_dict, parent_iid):
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
                self.display_dict_structure(parent_dict[item], iid)
            if type(parent_dict[item]) is np.ndarray or type(parent_dict[item]) is list:
                if len(parent_dict[item]) < 100:
                    self.display_array_structure(parent_dict[item], iid)
    
    def display_array_structure(self, parent_array, parent_iid):
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
                self.display_dict_structure(parent_array[i], iid)
            if type(parent_array[i]) is np.ndarray or type(parent_array[i]) is list:
                if len(parent_array[i]) < 100:
                    self.display_array_structure(parent_array[i], iid)

    def on_double_click(self, event):
        selected_item = self.data_tree.selection()
        path, item = self.get_full_path()
        print(f"Double-clicked on item: {path}")
        data = self.get_data(self.data, path)
        if type(data) is np.ndarray:
            print(f"plotting {item}")
            figure_view_window = tk.Toplevel(self.root)
            figure_view = simplePlotView.SimplePlotView(figure_view_window)
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

if __name__ == "__main__":
    root = tk.Tk()
    data_viewer = DataViewer(root)
    root.mainloop()
