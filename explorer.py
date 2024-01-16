import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import numpy as np
import h5py
import os


class FileListViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("File List Viewer")

        # Treeview to display files and folders
        self.file_tree = ttk.Treeview(root)
        self.file_tree.heading("#0", text="[Data File]", anchor="w")
        self.file_tree.pack(expand=tk.YES, fill=tk.BOTH)

        # Buttons
        self.open_button = tk.Button(
            root, text="Browse", command=self.browse_file)
        self.open_button.pack(side=tk.LEFT, padx=5)

        # self.load_button = tk.Button(
        #     root, text="Load Files", command=self.load_files)
        # self.load_button.pack(side=tk.LEFT, padx=5)

    def browse_file(self):
        data_path = filedialog.askopenfilename(
            title="Select pre-processed file", 
            filetypes = (("NPZ File","*.npz"),("all files","*.*")))
        if data_path:
            # Clear existing tree items
            self.file_tree.delete(*self.file_tree.get_children())

            # Display files and folders in the treeview
            self.data = np.load(data_path, allow_pickle=True)
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
                label_text = '%s [%d]' % (item, len(parent_dict[item]))
            elif type(parent_dict[item]) is list:
                label_text = '%s [%d]' % (item, len(parent_dict[item]))
            elif type(parent_dict[item]) is range:
                label_text = '%s [%d:%d]' % (item, parent_dict[item].start, parent_dict[item].stop)
            else:
                label_text = '%s: %s' % (item, type(parent_dict[item]))
            iid = self.file_tree.insert(parent_iid, "end", text=label_text, open=False)
            if type(parent_dict[item]) is dict:
                self.display_dict_structure(parent_dict[item], iid)
            if type(parent_dict[item]) is np.ndarray or type(parent_dict[item]) is list:
                if len(parent_dict[item]) < 100:
                    self.display_array_structure(parent_dict[item], iid)
    
    def display_array_structure(self, parent_array, parent_iid):
        for i in range(len(parent_array)):
            try:
                label_text ='[%d] %s' % (i, parent_array[i]['Name'])
            except:
                if type(parent_array[i]) is dict:
                    label_text = '[%d]' % i
                elif type(parent_array[i]) is np.float64:
                    label_text = '[%d] %f' % (i, parent_array[i])
                else:
                    label_text = '[%d] %s' % (i, str(type(parent_array[i])))
            iid = self.file_tree.insert(parent_iid, "end", text=label_text, open=False)
            if type(parent_array[i]) is dict:
                self.display_dict_structure(parent_array[i], iid)
            if type(parent_array[i]) is np.ndarray or type(parent_array[i]) is list:
                if len(parent_array[i]) < 100:
                    self.display_array_structure(parent_array[i], iid)

    # def load_files(self):
    #     selected_item = self.file_tree.selection()
    #     if selected_item:
    #         item_text = self.file_tree.item(selected_item, "text")
    #         print(f"Selected File/Folder: {item_text}")
    #     else:
    #         print("No file/folder selected.")


if __name__ == "__main__":
    root = tk.Tk()
    file_list_viewer = FileListViewer(root)
    root.mainloop()
