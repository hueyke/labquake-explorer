import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

class PointsDraggingView(tk.Toplevel):
    def __init__(self, root, x, y, picked_idx):
        self.root = tk.Toplevel(root)
        self.root.title("Move the points to desired positions")

        # Matplotlib Figure and Tkinter Canvas
        self.fig, self.ax = plt.subplots()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Initialize variables
        self.selected_points = []
        self.point_alpha_default = 0.8
        self.mouse_button_pressed = None
        self.currently_dragging = False
        self.current_artist = None
        self.offset = [0, 0]
        self.master_curve = None

        # Connect events
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)

        # Initialize master curve and selected points
        self.x = x
        self.y = y
        self.picked_idx = picked_idx
        self.init_master_curve()

        # Bind the configure event for window resizing
        self.root.bind("<Configure>", self.on_configure)

    def init_master_curve(self):
        self.master_curve, = self.ax.plot(self.x, self.y, zorder=-100)
        width, height = self.get_circle_dims()
        for i in range(len(self.picked_idx)):
            idx = self.picked_idx[i]
            x_point, y_point = self.x[idx], self.y[idx]
            new_point_label = i
            point_object = patches.Ellipse([x_point, y_point], width=width, height=height, angle=0, color='r', fill=False, lw=1,
                                           alpha=self.point_alpha_default, transform=self.ax.transData,
                                           label=new_point_label)
            point_object.set_picker(5)
            self.ax.add_patch(point_object)
            self.selected_points.append(point_object)
            self.canvas.draw()

    def get_circle_dims(self):
        self.canvas.draw()
        xl = self.ax.get_xlim()
        yl = self.ax.get_ylim()
        ratio = (yl[-1] - yl[0]) / (xl[-1] - xl[0])
        fig_size = self.fig.get_size_inches()
        ratio *= fig_size[0] / fig_size[1]
        width = (xl[-1] - xl[0]) / fig_size[0] * 0.15
        return width, width * ratio

    def on_press(self, event):
        self.currently_dragging = True
        if event.button == 3:
            self.mouse_button_pressed = "right"
        elif event.button == 1:
            self.mouse_button_pressed = "left"

    def on_release(self, event):
        self.current_artist = None
        self.currently_dragging = False

    def on_pick(self, event):
        if self.current_artist is None:
            self.current_artist = event.artist
            if isinstance(event.artist, patches.Ellipse):
                if event.mouseevent.dblclick:
                    if self.mouse_button_pressed == "right" and len(self.ax.patches) > 2:
                        event.artist.remove()
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
        if event.xdata is None:
            return
        if isinstance(self.current_artist, patches.Ellipse):
            dx, dy = self.offset
            cx, cy = event.xdata + dx, event.ydata + dy
            idx = np.argmin((self.x - cx) ** 2 + (self.y - cy) ** 2)
            self.picked_idx[int(self.current_artist.get_label())] = idx
            self.current_artist.center = self.x[idx], self.y[idx]
            self.canvas.draw()
            # print(self.picked_idx)

    def on_configure(self, event):
        if self.ax:
            width, height = self.get_circle_dims()
            for point in self.selected_points:
                point.set_width(width)
                point.set_height(height)
            self.canvas.draw()



if __name__ == "__main__":
    root = tk.Tk()
    x = np.linspace(0, 2 * np.pi, 1000)
    y = np.sin(x)
    picked_idx = [100, 300, 500, 700, 900]
    pointsDraggingView = PointsDraggingView(root, x, y, picked_idx)
    root.mainloop()
