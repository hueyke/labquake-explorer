import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D

class InteractiveConnectedDotsView(tk.Toplevel):
    def __init__(self, root):
        # super().__init__(root)
        self.root = root
        self.root.title("Interactive Plot")

        # Matplotlib Figure and Tkinter Canvas
        self.fig, self.ax = plt.subplots()
        self.ax.set_title("Double click left button to create draggable point\nDouble click right to remove a point", loc="left")
        self.ax.set_xlim(0, 4000)
        self.ax.set_ylim(0, 3000)
        self.ax.set_aspect('equal')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        #------------------------------------------------
        self.listLabelPoints = []
        self.point_alpha_default = 0.8
        self.mousepress = None
        self.currently_dragging = False
        self.current_artist = None
        self.offset = [0, 0]
        self.n = 0
        self.line_object = None

        #------------------------------------------------
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('button_press_event', self.on_click)

        plt.grid(True)

    def on_press(self, event):
        self.currently_dragging = True
        if event.button == 3:
            self.mousepress = "right"
        elif event.button == 1:
            self.mousepress = "left"

    def on_release(self, event):
        self.current_artist = None
        self.currently_dragging = False

    def on_pick(self, event):
        if self.current_artist is None:
            self.current_artist = event.artist
            if isinstance(event.artist, patches.Circle):
                if event.mouseevent.dblclick:
                    if self.mousepress == "right" and len(self.ax.patches) > 2:
                        event.artist.remove()
                        xdata = list(self.line_object[0].get_xdata())
                        ydata = list(self.line_object[0].get_ydata())
                        for i in range(len(xdata)):
                            if event.artist.get_label() == self.listLabelPoints[i]:
                                xdata.pop(i)
                                ydata.pop(i)
                                self.listLabelPoints.pop(i)
                                break
                        self.line_object[0].set_data(xdata, ydata)
                        self.canvas.draw()
                else:
                    x0, y0 = self.current_artist.center
                    x1, y1 = event.mouseevent.xdata, event.mouseevent.ydata
                    self.offset = [(x0 - x1), (y0 - y1)]
            elif isinstance(event.artist, Line2D):
                if event.mouseevent.dblclick:
                    if self.mousepress == "left":
                        self.n += 1
                        x, y = event.mouseevent.xdata, event.mouseevent.ydata
                        new_point_label = "point" + str(self.n)
                        point_object = patches.Circle([x, y], radius=50, color='r', fill=False, lw=2,
                                                      alpha=self.point_alpha_default, transform=self.ax.transData,
                                                      label=new_point_label)
                        point_object.set_picker(5)
                        self.ax.add_patch(point_object)
                        xdata = list(self.line_object[0].get_xdata())
                        ydata = list(self.line_object[0].get_ydata())
                        point_inserted = False
                        for i in range(len(xdata) - 1):
                            if x > min(xdata[i], xdata[i + 1]) and x < max(xdata[i], xdata[i + 1]) and \
                               y > min(ydata[i], ydata[i + 1]) and y < max(ydata[i], ydata[i + 1]):
                                xdata.insert(i + 1, x)
                                ydata.insert(i + 1, y)
                                self.listLabelPoints.insert(i + 1, new_point_label)
                                point_inserted = True
                                break
                        self.line_object[0].set_data(xdata, ydata)
                        self.canvas.draw()
                        if not point_inserted:
                            print("Error: point not inserted")
                else:
                    xdata = event.artist.get_xdata()
                    ydata = event.artist.get_ydata()
                    x1, y1 = event.mouseevent.xdata, event.mouseevent.ydata
                    self.offset = xdata[0] - x1, ydata[0] - y1

    def on_motion(self, event):
        if not self.currently_dragging:
            return
        if self.current_artist is None:
            return
        if event.xdata is None:
            return
        dx, dy = self.offset
        if isinstance(self.current_artist, patches.Circle):
            cx, cy = event.xdata + dx, event.ydata + dy
            self.current_artist.center = cx, cy
            xdata = list(self.line_object[0].get_xdata())
            ydata = list(self.line_object[0].get_ydata())
            for i in range(len(xdata)):
                if self.listLabelPoints[i] == self.current_artist.get_label():
                    xdata[i] = cx
                    ydata[i] = cy
                    break
            self.line_object[0].set_data(xdata, ydata)
        elif isinstance(self.current_artist, Line2D):
            xdata = list(self.line_object[0].get_xdata())
            ydata = list(self.line_object[0].get_ydata())
            xdata0 = xdata[0]
            ydata0 = ydata[0]
            for i in range(len(xdata)):
                xdata[i] = event.xdata + dx + xdata[i] - xdata0
                ydata[i] = event.ydata + dy + ydata[i] - ydata0
            self.line_object[0].set_data(xdata, ydata)
            for p in self.ax.patches:
                point_label = p.get_label()
                i = self.listLabelPoints.index(point_label)
                p.center = xdata[i], ydata[i]
        self.canvas.draw()

    def on_click(self, event):
        if event and event.dblclick:
            if len(self.listLabelPoints) < 2:
                self.n += 1
                x, y = event.xdata, event.ydata
                new_point_label = "point" + str(self.n)
                point_object = patches.Circle([x, y], radius=50, color='r', fill=False, lw=2,
                                              alpha=self.point_alpha_default, transform=self.ax.transData,
                                              label=new_point_label)
                point_object.set_picker(5)
                self.ax.add_patch(point_object)
                self.listLabelPoints.append(new_point_label)
                if len(self.listLabelPoints) == 2:
                    xdata = []
                    ydata = []
                    for p in self.ax.patches:
                        cx, cy = p.center
                        xdata.append(cx)
                        ydata.append(cy)
                    self.line_object = self.ax.plot(xdata, ydata, alpha=0.5, c='r', lw=2, picker=True)
                    self.line_object[0].set_pickradius(5)
                self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    interactive_plot = InteractiveConnectedDotsView(root)
    root.mainloop()
