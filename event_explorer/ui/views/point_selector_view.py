import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class PointsSelectorView(tk.Toplevel):
    def __init__(self, parent, x, y, picked_idx, add_remove_enabled=False, callback=None, xlabel=None, ylabel=None, title=None):
        self.root = parent.root
        self.parent = parent
        super().__init__(self.root)
        self.title("Points Selector")

        # Buttons
        if callback:
            self.callback = callback
            self.save_button = tk.Button(self, text="Save", command=self.save)
            self.save_button.pack(side=tk.TOP, padx=5)

        # Matplotlib Figure and Tkinter Canvas
        self.fig = plt.Figure()
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        
        # Navigation toolbar for zooming and panning
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        self.canvas_widget.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)

        # Master curve
        self.x_values = x
        self.y_values = y
        self.ax.plot(self.x_values, self.y_values, '.-', color='C0', zorder=-100)
        if xlabel:
            self.ax.set_xlabel(xlabel)
        if ylabel:
            self.ax.set_ylabel(ylabel)
        if title:
            self.ax.set_title(title)

        # Data points
        self.add_remove_enabled = add_remove_enabled
        self.picked_idx = picked_idx
        self.markers = []
        self.offset = [0, 0]
        self.mouse_button_pressed = None
        self.current_artist = None
        self.currently_dragging = False
        self.plot_data_points()

        # Event bindings
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('resize_event', self.on_resize)
        self.fig.canvas.mpl_connect('scroll_event', self.on_resize)

    def plot_data_points(self):
        width, height = self.get_circle_dims()
        for i in range(len(self.picked_idx)):
            idx = self.picked_idx[i]
            x = self.x_values[idx]
            y = self.y_values[idx]
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
                    idx = np.argmin(((self.x_values - cx) / xw) ** 2 + ((self.y_values - cy) / yw) ** 2)
                    self.current_artist.set_center((self.x_values[idx], self.y_values[idx]))
                    self.canvas.draw()
                    self.picked_idx[int(self.current_artist.get_label())] = idx
                    # print(self.picked_idx)
                except:
                    pass

    def on_press(self, event):
        self.currently_dragging = True
        if event.button == 1:
            self.mouse_button_pressed = "left"
            if event.dblclick and self.add_remove_enabled:
                width, height = self.get_circle_dims()
                xl = self.ax.get_xlim()
                yl = self.ax.get_ylim()
                yw = yl[-1] - yl[0]
                xw = xl[-1] - xl[0]
                idx = np.argmin(((self.x_values - event.xdata) / xw) ** 2 + ((self.y_values - event.ydata) / yw) ** 2)
                marker = patches.Ellipse((self.x_values[idx], self.y_values[idx]), width=width, height=height, color='red', fill=False, lw=1, picker=5, label=str(len(self.picked_idx)))
                self.ax.add_patch(marker)
                self.markers.append(marker)
                self.picked_idx.append(idx)
                self.canvas.draw()
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

    def save(self):
        self.picked_idx.sort()
        self.callback(np.array(self.picked_idx))

if __name__ == "__main__":
    root = tk.Tk()
    class Parent:
        def __init__(self, root):
            self.root = root
    x = np.linspace(0, 2 * np.pi, 1000)
    y = np.sin(x)
    picked_idx = [100, 300, 500, 700, 900]
    parent = Parent(root)
    interactive_view = PointsSelectorView(parent, x, y, picked_idx, add_remove_enabled=True)
    root.mainloop()
