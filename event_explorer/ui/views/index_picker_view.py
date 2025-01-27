import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class IndexPickerView(tk.Toplevel):
    def __init__(self, parent, item_y=None, item_x=None):
        self.root = parent.root
        super().__init__(self.root)
        self.title("Index Picker")
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self.parent = parent

        # Row 0
        tk.Label(self, text="X Data").grid(row=0, column=0, padx=5, pady=5)
        tk.Label(self, text="Y Data").grid(row=0, column=1, padx=5, pady=5)
        tk.Label(self, text="Picked Index").grid(row=0, column=3, padx=5, pady=5)

        # Row 1
        self.data_x_combo = ttk.Combobox(self, state="readonly")
        self.data_x_combo.grid(row=1, column=0, padx=5, pady=5)
        self.data_y_combo = ttk.Combobox(self, state="readonly")
        self.data_y_combo.grid(row=1, column=1, padx=5, pady=5)
        self.index_textbox = tk.Entry(self, state="readonly")
        self.index_textbox.grid(row=1, column=3, padx=5, pady=5)

        # Matplotlib Figure and Tkinter Canvas
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")

        
        # Navigation toolbar for zooming and panning
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.grid(row=3, column=0, columnspan=4, padx=0, pady=0, sticky="ew")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        # Data points
        self.add_remove_enabled = True
        self.picked_idx = []
        self.item_y = item_y
        self.item_x = item_x
        self.index_y = None
        self.index_x = None
        self.data_x = []
        self.data_y = []
        self.markers = []
        self.offset = [0, 0]
        self.mouse_button_pressed = None
        self.current_artist = None
        self.currently_dragging = False
        self.plot_picked_points()

        # init functions
        self.init_comboboxes()
        self.plot_data()

        # Event bindings
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('resize_event', self.on_resize)
        self.fig.canvas.mpl_connect('scroll_event', self.on_resize)
        self.data_y_combo.bind("<<ComboboxSelected>>", self.data_y_selected)
        self.data_x_combo.bind("<<ComboboxSelected>>", self.data_x_selected)

    def data_y_selected(self, event):
        self.item_y = self.data_y_combo.get()
        self.plot_data()

    def data_x_selected(self, event):
        self.item_x = self.data_x_combo.get()
        self.plot_data()

    def plot_data(self):
        if self.item_y is None:
            return
        
        if self.item_x is None:
            self.ax.clear()
            self.data_y = self.parent.get_data(self.parent.data, self.item_y)
            self.ax.plot(self.data_y, zorder=-100)
            self.ax.set_ylabel(self.item_y)
            self.ax.set_xlabel("Index")
        else:
            self.ax.clear()
            self.data_x = self.parent.get_data(self.parent.data, self.item_x)
            self.data_y = self.parent.get_data(self.parent.data, self.item_y)
            self.ax.plot(self.data_x, self.data_y, zorder=-100)
            self.ax.set_ylabel(self.item_y)
            self.ax.set_xlabel(self.item_x)
        self.canvas.draw()

    def plot_picked_points(self):
        width, height = self.get_circle_dims()
        for i in range(len(self.picked_idx)):
            idx = self.picked_idx[i]
            x = self.data_x[idx]
            y = self.data_y[idx]
            marker = patches.Ellipse((x, y), width=width, height=height, color='red', fill=False, lw=2, picker=8, label=str(i))
            self.ax.add_patch(marker)
            self.markers.append(marker)

        self.canvas.draw()

    def on_pick(self, event):
        if self.current_artist is None:
            self.current_artist = event.artist
            if isinstance(event.artist, patches.Ellipse):
                if event.mouseevent.dblclick:
                    if self.add_remove_enabled and self.mouse_button_pressed == "right":
                        i = int(self.current_artist.get_label())
                        self.markers.remove(self.current_artist)
                        self.current_artist.remove()
                        self.current_artist = None
                        del self.picked_idx[i]
                        self.canvas.draw()
                else:
                    x0, y0 = self.current_artist.center
                    x1, y1 = event.mouseevent.xdata, event.mouseevent.ydata
                    self.offset = [(x0 - x1), (y0 - y1)]

    def on_motion(self, event):
        if not self.currently_dragging:
            return
        if self.current_artist is None:
            return
        if isinstance(self.current_artist, patches.Ellipse):
                try:
                    dx, dy = self.offset
                    cx, cy = event.xdata + dx, event.ydata + dy
                    xl = self.ax.get_xlim()
                    yl = self.ax.get_ylim()
                    yw = yl[-1] - yl[0]
                    xw = xl[-1] - xl[0]
                    idx = np.argmin(((self.data_x - cx) / xw) ** 2 + ((self.data_y - cy) / yw) ** 2)
                    self.current_artist.set_center((self.data_x[idx], self.data_y[idx]))
                    self.canvas.draw()
                    self.picked_idx[int(self.current_artist.get_label())] = idx
                    self.set_index_textbox(str(idx))
                except:
                    pass

    def on_press(self, event):
        self.currently_dragging = True
        if event.button == 1:
            self.mouse_button_pressed = "left"
            if event.dblclick and self.add_remove_enabled:
                if len(self.data_x) == 0:
                    return
                width, height = self.get_circle_dims()
                xl = self.ax.get_xlim()
                yl = self.ax.get_ylim()
                yw = yl[-1] - yl[0]
                xw = xl[-1] - xl[0]
                idx = np.argmin(((self.data_x - event.xdata) / xw) ** 2 + ((self.data_y - event.ydata) / yw) ** 2)
                marker = patches.Ellipse((self.data_x[idx], self.data_y[idx]), width=width, height=height, color='red', fill=False, lw=1, picker=5, label=str(len(self.picked_idx)))
                self.ax.add_patch(marker)
                self.markers.append(marker)
                self.picked_idx.append(idx)
                self.canvas.draw()
                self.set_index_textbox(str(idx))
        # elif event.button == 3:
        else:
            self.mouse_button_pressed = "right"

    def on_release(self, event):
        self.current_artist = None
        self.currently_dragging = False
        self.on_resize(None)

    def get_circle_dims(self):
        self.canvas.draw()
        xl = self.ax.get_xlim()
        yl = self.ax.get_ylim()
        ratio = (yl[-1] - yl[0]) / (xl[-1] - xl[0])
        fig_size = self.fig.get_size_inches()
        ratio *= fig_size[0] / fig_size[1]
        width = (xl[-1] - xl[0]) / fig_size[0] * 0.15
        return width, width * ratio

    def on_resize(self, event):
        if self.ax:
            width, height = self.get_circle_dims()
            for marker in self.markers:
                marker.set_width(width)
                marker.set_height(height)
            self.canvas.draw()

    def init_comboboxes(self):
        items = list()
        i = 0
        for item in self.parent.data_tree.get_children(""):
            item_label = self.parent.data_tree.item(item)['text'].split(':')[0]
            items.append(item_label)
            if item_label == self.item_y:
                self.index_y = i
            elif item_label == self.item_x:
                self.index_x = i
            i += 1
        
        self.data_x_combo.config(values=items)
        self.data_y_combo.config(values=items)
        if self.index_y:
            self.data_y_combo.current(self.index_y)
        if self.index_x:
            self.data_x_combo.current(self.index_x)
        

    def set_index_textbox(self, text):
        self.index_textbox.config(state="normal")
        self.index_textbox.delete(0, tk.END)
        self.index_textbox.insert(0, text)
        self.index_textbox.config(state="readonly")
        self.clipboard_clear()
        self.clipboard_append(text)