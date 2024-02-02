import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
from scipy import signal
import warnings

class DynamicStrainArrivalPickingView(tk.Toplevel):
    def __init__(self, parent, run_idx, event_idx):
        self.parent = parent
        super().__init__(self.parent.root)
        self.title("Pick Arrivals")

        # Configure row and column properties
        # 7 columns, 4 rows
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(5, weight=1)


        # Labels
        ttk.Label(self, text="Event Index:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.cf_label = ttk.Label(self, text="Cf=0.00m/s")
        self.cf_label.grid(row=0, column=4, padx=5, pady=5, sticky="e")
        ttk.Label(self, text="Filter:", anchor="e", justify="left").grid(row=3, column=0, padx=5, pady=5, sticky="e")

        # Comboboxes
        self.event_combobox = ttk.Combobox(self, width=10)
        self.event_combobox.grid(row=0, column=1, padx=5, pady=5)
        self.filter_combobox = ttk.Combobox(self, width=10, state="disabled")
        self.filter_combobox.grid(row=3, column=1, padx=5, pady=5)
        self.filter_combobox["values"] = ("savgol_filter")

        # Checkbox
        self.enabled_channels_mb = tk.Menubutton(self, text="Enabled Channels")
        self.enabled_channels_mb.grid(row=0, column=2, padx=5, pady=5)
        self.enabled_channels_mb.menu = tk.Menu(self.enabled_channels_mb, tearoff=0)
        self.enabled_channels_mb["menu"] = self.enabled_channels_mb.menu

        self.fitting_channels_mb = tk.Menubutton(self, text="Fitting Channels")
        self.fitting_channels_mb.grid(row=0, column=3, padx=5, pady=5)
        self.fitting_channels_mb.menu = tk.Menu(self.fitting_channels_mb, tearoff=0)
        self.fitting_channels_mb["menu"] = self.fitting_channels_mb.menu

        # Button
        self.save_button = tk.Button(self, text="Save", command=self.save)
        self.save_button.grid(row=0, column=6, padx=5, pady=5, sticky="w")
        self.filter_toggle = tk.Button(self, text="On", command=self.toggle_filter)
        self.filter_toggle.grid(row=3, column=6, padx=5, pady=5)

        # Matplotlib Figure and Tkinter Canvas
        self.fig = plt.figure(figsize=(7, 7), constrained_layout=True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, columnspan=7, padx=5, pady=5, sticky="nsew")
        self.axs = None
        
        # Navigation toolbar for zooming and panning
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.grid(row=2, column=0, columnspan=7, padx=0, pady=0, sticky="ew")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        # Data
        self.run_idx = run_idx
        self.event_idx = event_idx
        self.event = None
        self.enabled_channels = None
        self.fitting_channels = None
        self.picked_idx = None
        self.fitting_markers = []
        self.not_fitting_markers = []
        self.offset = [0, 0]
        self.current_artist = None
        self.currently_dragging = False
        self.rupture_speed = None
        self.fitted_line = None
        self.filtering = True
        self.init_event_combobox()
        self.on_selected_event_changed(None)

        # Event bindings
        self.fig.canvas.mpl_connect("pick_event", self.on_pick)
        self.fig.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.fig.canvas.mpl_connect("button_press_event", self.on_press)
        self.fig.canvas.mpl_connect("button_release_event", self.on_release)
        self.fig.canvas.mpl_connect("resize_event", self.on_resize)
        self.fig.canvas.mpl_connect("scroll_event", self.on_resize)
        self.event_combobox.bind("<<ComboboxSelected>>", self.on_selected_event_changed)

    def plot(self):
        linestyle = ".-"

        self.fig.clear()
        gs = self.fig.add_gridspec(5, hspace=0, height_ratios=[1, 1, 1, 1, 10])
        self.axs = gs.subplots(sharex=True)
        self.axs[0].set_ylabel(r"$\tau$ (MPa)")
        self.axs[1].set_ylabel(r"$\mu$")
        self.axs[2].set_ylabel(r"$\delta_\mathrm{LP}\ \mathrm{({\mu}m)}$")
        self.axs[3].set_ylabel(r"$\delta\ \mathrm{({\mu}m)}$")

        t = self.event["time"] - self.event["event_time"]
        self.axs[0].plot(t, self.event["shear_stress"], linestyle, color="C0")
        self.axs[1].plot(t, self.event["friction"], linestyle, color="C0")
        self.axs[2].plot(t, self.event["LP_displacement"] - self.event["LP_displacement"][0], linestyle, color="C0")
        self.axs[3].plot(t, self.event["displacement"] - self.event["displacement"][0], linestyle, color="C0")

        tt = self.event["strain"]["original"]["time"] - self.event["event_time"]
        y = self.event["strain"]["original"]["raw"]

        n_channels = y.shape[0]
        if self.enabled_channels is None:
            if "enabled_channels" in self.event:
                self.enabled_channels = self.event["strain"]["enabled_channels"]
            else:
                self.enabled_channels = [i % 2 == 0 for i in range(n_channels)]
        if self.fitting_channels is None:
            if "fitting_channels" in self.event:
                self.fitting_channels = self.event["strain"]["fitting_channels"]
            else:
                # self.fitting_channels = [i % 2 == 0 for i in range(n_channels)]
                self.fitting_channels = [False, False, False, False, False, False, True, False, True, False, True, False, True, False, False, False]
        if (not "locations" in self.event["strain"]) or (not len(self.event["strain"]["locations"]) == n_channels):
            self.event["strain"]["locations"] = [10.5 + 12 * int(i / 2) for i in range(n_channels)]
        
        self.lines = [None for i in range(n_channels)]

        line_idx = 0
        ratios = np.ones(y.shape[0])
        for i in range(y.shape[0]):
            if not self.enabled_channels[i]:
                continue
            loc = self.event["strain"]["locations"][i]
            self.axs[4].plot([tt[0], tt[-1]], [loc, loc], "k:", zorder=-101)
            ratios[i] = 12 / (y[i, :].max() - y[i, :].min())
            self.lines[i] = self.axs[4].plot(tt, y[i, :] * ratios[i] + loc, color="C%d" % line_idx, zorder=-100)
            line_idx += 1
        self.axs[4].set_ylabel("location along fault (mm)")
        self.axs[4].set_xlabel("time - %f (s)" %  self.event["event_time"])
        self.axs[4].set_ylim(105, 0)
        self.axs[0].set_xlim(tt[0], tt[-1])
        
        self.fig.suptitle("%s run%02d event%d" % (self.parent.data["name"], 
                                                  self.run_idx, 
                                                  self.event_idx))
        
        if self.picked_idx is None:
            if "picked_idx" in self.event["strain"]["original"]:
                self.picked_idx = self.event["strain"]["original"]["picked_idx"]
            else:
                middle_idx = int(y.shape[1] / 2)
                self.picked_idx = [middle_idx for i in range(n_channels)]
        self.draw_markers()

    def draw_markers(self):
        width, height = self.get_circle_dims()
        for marker in self.fitting_markers:
            marker.remove()
        for marker in self.not_fitting_markers:
            marker.remove()
        self.fitting_markers = []
        self.not_fitting_markers = []
        for i in range(len(self.picked_idx)):
            if not self.enabled_channels[i]:
                continue
            idx = self.picked_idx[i]
            if self.fitting_channels[i]:
                color = "red"
            else:
                color = "black"
            (x , y) = self.lines[i][0].get_data()
            marker = patches.Ellipse((x[idx], y[idx]), width=width, height=height, color=color, fill=False, lw=2, picker=8, label=str(i))
            self.axs[4].add_patch(marker)
            if self.fitting_channels[i]:
                self.fitting_markers.append(marker)
            else:
                self.not_fitting_markers.append(marker)
        self.canvas.draw()


    def on_pick(self, event):
        if self.current_artist is None:
            self.current_artist = event.artist
            if isinstance(event.artist, patches.Ellipse):
                x0, y0 = self.current_artist.center
                x1, y1 = event.mouseevent.xdata, event.mouseevent.ydata
                self.offset = [(x0 - x1), (y0 - y1)]

    def on_motion(self, event):
        if not self.currently_dragging:
            return
        if self.current_artist is None:
            return
        if isinstance(self.current_artist, patches.Ellipse):
                channel = int(self.current_artist.get_label())
                dx, dy = self.offset
                cx, cy = event.xdata + dx, event.ydata + dy
                xl = self.axs[4].get_xlim()
                yl = self.axs[4].get_ylim()
                yw = yl[-1] - yl[0]
                xw = xl[-1] - xl[0]
                (x , y) = self.lines[channel][0].get_data()
                idx = np.argmin(((x - cx) / xw) ** 2 + ((y - cy) / yw) ** 2)
                self.current_artist.set_center((x[idx], y[idx]))
                self.picked_idx[channel] = idx
                self.update_fitted_line()

    def on_press(self, event):
        self.currently_dragging = True

    def on_release(self, event):
        self.current_artist = None
        self.currently_dragging = False
        self.on_resize(None)

    def get_circle_dims(self):
        xl = self.axs[4].get_xlim()
        yl = self.axs[4].get_ylim()
        ratio = (yl[-1] - yl[0]) / (xl[-1] - xl[0])
        bbox = self.axs[4].get_window_extent()
        ax_size = [bbox.width, bbox.height]
        ratio *= ax_size[0] / ax_size[1]
        width = (xl[-1] - xl[0]) / ax_size[0] * 0.1 * self.fig.dpi
        return width, width * ratio

    def on_resize(self, event):
        if not self.axs is None:
            width, height = self.get_circle_dims()
            for marker in self.fitting_markers:
                marker.set_width(width)
                marker.set_height(height)
            for marker in self.not_fitting_markers:
                marker.set_width(width)
                marker.set_height(height)
            self.canvas.draw()
    
    def update_fitted_line(self):
        x = np.empty(len(self.fitting_markers))
        y = np.empty(len(self.fitting_markers))
        for i in range(len(self.fitting_markers)):
            idx = int(self.fitting_markers[i].get_label())
            x[i] = self.fitting_markers[i].get_center()[0]
            y[i] = self.event["strain"]["locations"][idx]
        a = np.polyfit(y, x, 1)
        if self.fitted_line:
            self.fitted_line[0].remove()
        self.fitted_line = self.axs[4].plot(a[0] * y + a[1], y, "r--")
        self.canvas.draw()
        warnings.filterwarnings("ignore", message="divide by zero encountered in double_scalars")
        self.rupture_speed = -1e-3 / a[0]
        warnings.filterwarnings("default", message="divide by zero encountered in double_scalars")
        self.cf_label.configure(text=f"Cf = {self.rupture_speed:.2e} m/s")
        self.update()
    
    def save(self):
        self.event["strain"]["enabled_channels"] = self.enabled_channels
        self.event["strain"]["fitting_channels"] = self.fitting_channels
        self.event["rupture_speed"] = self.rupture_speed
        self.event["strain"]["original"]["picked_idx"] = self.picked_idx
        self.event["strain"]["original"]["rupture_arrival_time"] = np.array([self.event["strain"]["time"][i] for i in self.picked_idx])
        self.parent.refresh_tree()
        print(f"Saved runs[{self.run_idx}]/events[{self.event_idx}] to data.")

    def init_event_combobox(self):
        n_events = len(self.parent.data["runs"][self.run_idx]["events"])
        options = [f"{i}" for i in range(n_events)]
        self.event_combobox.config(values=options, state="readonly")
        self.event_combobox.current(self.event_idx)

    def init_enabled_channels_mb(self):
        n = len(self.enabled_channels)
        self.enabled_channels_mb.menu.delete(0, "end")
        self.enabled_channels_mb.items = [tk.IntVar() for i in range(n)]
        for i in range(n):
            self.enabled_channels_mb.items[i].set(self.enabled_channels[i])
            self.enabled_channels_mb.menu.add_checkbutton( label="channel %d" %i, variable=self.enabled_channels_mb.items[i], command=self.enabled_channels_changed)

    def init_fitting_channels_mb(self):
        n = len(self.fitting_channels)
        self.fitting_channels_mb.menu.delete(0, "end")
        self.fitting_channels_mb.items = [tk.IntVar() for i in range(n)]
        for i in range(n):
            self.fitting_channels_mb.items[i].set(self.fitting_channels[i])
            self.fitting_channels_mb.menu.add_checkbutton( label="channel %d" %i, variable=self.fitting_channels_mb.items[i], command=self.fitting_channels_changed)

    def on_selected_event_changed(self, event):
        self.event_idx = int(self.event_combobox.get())
        self.event = self.parent.data["runs"][self.run_idx]["events"][self.event_idx]
        if "enabled_channels" in self.event["strain"]:
            self.enabled_channels = self.event["strain"]["enabled_channels"]
        else:
            self.enabled_channels = None
        if "fitting_channels" in self.event["strain"]:
            self.fitting_channels = self.event["strain"]["fitting_channels"]
        else:
            self.fitting_channels = None
        if "picked_idx" in self.event["strain"]["original"]:
            self.picked_idx = self.event["strain"]["original"]["picked_idx"]
        else:
            self.picked_idx = None
        self.fitting_markers = []
        self.not_fitting_markers = []
        self.offset = [0, 0]
        self.current_artist = None
        self.currently_dragging = False
        self.rupture_speed = None
        self.fitted_line = None
        self.plot()
        self.init_enabled_channels_mb()
        self.init_fitting_channels_mb()
        self.update_fitted_line()

    def enabled_channels_changed(self):
        n = len(self.enabled_channels)
        for i in range(n):
            self.enabled_channels[i] = self.enabled_channels_mb.items[i].get()
        self.plot()
        self.update_fitted_line()

    def fitting_channels_changed(self):
        n = len(self.fitting_channels)
        for i in range(n):
            self.fitting_channels[i] = self.fitting_channels_mb.items[i].get()
        self.draw_markers()
        self.update_fitted_line()

    def toggle_filter(self):
        self.filtering = not self.filtering
        if self.filtering:
            self.filter_toggle.config(text="On")
        else:
            self.filter_toggle.config(text="Off")


if __name__ == "__main__":
    pass
