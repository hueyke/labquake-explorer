import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from matplotlib.widgets import Cursor

class CohesiveZoneModelFittingView(tk.Toplevel):
    def __init__(self, parent, run_idx, event_idx):
        self.parent = parent
        super().__init__(self.parent.root)
        self.title("Cohesive Zone Model Fitting")
        
        # Configure window
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Top controls
        control_frame = ttk.Frame(self)
        control_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Event selection
        ttk.Label(control_frame, text="Event Index:").pack(side=tk.LEFT, padx=5)
        self.event_combobox = ttk.Combobox(control_frame, width=10)
        self.event_combobox.pack(side=tk.LEFT, padx=5)
        
        # Filter controls
        ttk.Label(control_frame, text="Filter Window:").pack(side=tk.LEFT, padx=5)
        self.filter_window = tk.StringVar(value="51")
        self.filter_spinbox = ttk.Spinbox(
            control_frame, 
            from_=3, 
            to=201, 
            increment=2,
            textvariable=self.filter_window,
            width=5
        )
        self.filter_spinbox.pack(side=tk.LEFT, padx=5)
        
        self.filter_button = tk.Button(
            control_frame, 
            text="Filter On", 
            relief="sunken",
            command=self.toggle_filter
        )
        self.filter_button.pack(side=tk.LEFT, padx=5)

        # Matplotlib figure
        self.fig = plt.figure(figsize=(10, 6))
        self.gs = self.fig.add_gridspec(2, hspace=0.3)
        self.axs = self.gs.subplots(sharex=True)
        
        # Canvas setup
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Toolbar
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.grid(row=2, column=0, padx=0, pady=0, sticky="ew")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        # Data attributes
        self.run_idx = run_idx
        self.event_idx = event_idx
        self.event = None
        self.filtering = True
        
        # View limits
        self.x_min = -0.05
        self.x_max = 0.05
        
        # Vertical line attributes
        self.vlines = None
        self.vlines_twin = None
        self.active_line_idx = None
        self.drag_active = False
        
        # Connect event handlers
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        # Initialize
        self.init_event_combobox()
        self.event_combobox.bind("<<ComboboxSelected>>", self.on_event_changed)
        self.filter_spinbox.bind("<Return>", self.update_plot)
        self.on_event_changed()

    def init_event_combobox(self):
        n_events = len(self.parent.data["runs"][self.run_idx]["events"])
        options = [f"{i}" for i in range(n_events)]
        self.event_combobox.config(values=options, state="readonly")
        self.event_combobox.current(self.event_idx)

    def on_event_changed(self, event=None):
        self.event_idx = int(self.event_combobox.get())
        self.event = self.parent.data["runs"][self.run_idx]["events"][self.event_idx]
        self.update_plot()

    def toggle_filter(self):
        self.filtering = not self.filtering
        if self.filtering:
            self.filter_button.config(text="Filter On", relief="sunken")
        else:
            self.filter_button.config(text="Filter Off", relief="raised")
        self.update_plot()

    def update_plot(self, event=None):
        # Clear existing plots
        for ax in self.axs:
            ax.clear()
            
        # Get data
        t = self.event["strain"]["original"]["time"] - self.event["event_time"]
        y6 = self.event["strain"]["original"]["raw"][6]
        y14 = self.event["strain"]["original"]["raw"][14]
        
        # Apply filter if enabled
        if self.filtering:
            window_length = int(self.filter_window.get())
            if window_length % 2 == 0:
                window_length += 1
                self.filter_window.set(str(window_length))
            y6 = signal.savgol_filter(y6, window_length, 2)
            y14 = signal.savgol_filter(y14, window_length, 2)

        # Plot data
        self.axs[0].plot(t, y6, 'b-')
        self.axs[1].plot(t, y14, 'r-')
        
        # Configure axes
        for ax in self.axs:
            ax.grid(True)
            ax.set_xlim(self.x_min, self.x_max)  # Use class variables
        
        # Labels and title
        self.axs[1].set_xlabel('Time (s)')
        self.axs[0].set_ylabel('exy')
        self.axs[1].set_ylabel('eyy')
        self.fig.suptitle(f"{self.parent.data['name']} run{self.run_idx:02d} event{self.event_idx}")
        
        # Handle vertical lines
        if self.vlines is None:  # Initialize lines if they don't exist
            # Initialize the lists
            self.vlines = []
            self.vlines_twin = []
            
            # Calculate evenly spaced positions across full range
            x_positions = np.linspace(self.x_min, self.x_max, 7)[1:-1]  # Create 7 points and take middle 5
            
            # Create the lines
            for x_pos in x_positions:
                # Create line in top plot
                vline = self.axs[0].axvline(x=x_pos, color='g', linestyle='--', alpha=0.5)
                self.vlines.append(vline)
                
                # Create twin line in bottom plot
                vline_twin = self.axs[1].axvline(x=x_pos, color='g', linestyle='--', alpha=0.5)
                self.vlines_twin.append(vline_twin)
        else:
            # Update existing lines positions
            for vline, vline_twin in zip(self.vlines, self.vlines_twin):
                x_pos = vline.get_xdata()[0]
                vline.set_xdata([x_pos, x_pos])
                vline_twin.set_xdata([x_pos, x_pos])
        
        # Refresh canvas
        self.canvas.draw()

    def on_mouse_press(self, event):
        if event.inaxes:
            # Check each line to see if click is near it
            for i, vline in enumerate(self.vlines):
                line_x = vline.get_xdata()[0]
                if abs(event.xdata - line_x) < 0.002:  # Reduced sensitivity for multiple lines
                    self.drag_active = True
                    self.active_line_idx = i
                    break

    def on_mouse_release(self, event):
        self.drag_active = False
        self.active_line_idx = None

    def on_mouse_move(self, event):
        if self.drag_active and event.inaxes and self.active_line_idx is not None:
            # Update active line pair
            new_x = event.xdata
            self.vlines[self.active_line_idx].set_xdata([new_x, new_x])
            self.vlines_twin[self.active_line_idx].set_xdata([new_x, new_x])
            self.canvas.draw_idle()

if __name__ == "__main__":
    pass