import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

class MatplotlibPickerView(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.root.title("Interactive Sine Curve")

        # Matplotlib Figure and Tkinter Canvas
        self.fig, self.ax = plt.subplots()
        self.ax.set_title("Pick, Drag, Add, and Remove Points on Sine Curve")
        self.ax.set_xlim(0, 2 * np.pi)
        self.ax.set_ylim(-1, 1)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Sine curve
        self.x_values = np.linspace(0, 2 * np.pi, 100)
        self.y_values = np.sin(self.x_values)
        self.ax.plot(self.x_values, self.y_values, label='Sine Curve', color='blue')

        # Data points
        self.data_points = [(np.pi / 4, np.sqrt(2) / 2), (3 * np.pi / 4, np.sqrt(2) / 2)]
        self.markers = []

        self.plot_data_points()

        # Event bindings
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.fig.canvas.mpl_connect('button_press_event', self.on_button_press)

        # Bind the configure event for window resizing
        self.root.bind("<Configure>", self.on_configure)

    def plot_data_points(self):
        width, height = self.get_circle_dims()
        for x, y in self.data_points:
            size_x = (self.ax.get_xlim()[1] - self.ax.get_xlim()[0]) * 0.02
            size_y = (self.ax.get_ylim()[1] - self.ax.get_ylim()[0]) * 0.02
            marker = patches.Ellipse((x, y), width=width, height=height, color='red', picker=5)
            self.ax.add_patch(marker)
            self.markers.append(marker)

        self.canvas.draw()

    def on_pick(self, event):
        if isinstance(event.artist, patches.Ellipse):
            picked_marker = event.artist
            picked_marker.set_color('green')
            self.canvas.draw()

    def on_motion(self, event):
        if event.inaxes and event.inaxes is self.ax:
            for marker in self.markers:
                contains, _ = marker.contains(event)
                if contains:
                    if event.button == 1 and event.xdata:
                        marker.set_center((event.xdata, np.sin(event.xdata)))
                        self.canvas.draw()

    def on_button_press(self, event):
        if event.dblclick:
            if event.button == 1:
                # Double-click with left button to add a point
                x = event.xdata
                y = np.sin(x)
                self.data_points.append((x, y))
                width, height = self.get_circle_dims()
                marker = patches.Ellipse((x, y), width=width, height=height, color='red', picker=5)
                self.ax.add_patch(marker)
                self.markers.append(marker)
                self.canvas.draw()
            elif event.button == 3:
                # Double-click with right button to remove a point
                for marker in self.markers:
                    contains, _ = marker.contains(event)
                    if contains:
                        marker.remove()
                        self.markers.remove(marker)
                        self.data_points.remove((marker.center[0], marker.center[1]))
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

    def on_configure(self, event):
        if self.ax:
            width, height = self.get_circle_dims()
            for point in self.selected_points:
                point.set_width(width)
                point.set_height(height)
            self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    interactive_view = MatplotlibPickerView(root)
    root.mainloop()
