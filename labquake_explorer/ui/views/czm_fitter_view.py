import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from matplotlib.widgets import Cursor
from labquake_explorer.utils.cohesive_crack import CohesiveCrack
from labquake_explorer.data.data_processor import DataProcessor



class CZMFitterView(tk.Toplevel):
    def __init__(self, parent, run_idx, event_idx):
        self.parent = parent
        super().__init__(self.parent.root)
        self.title("Cohesive Zone Model Fitting")
        
        # Initialize data attributes first
        self.run_idx = run_idx
        self.event_idx = event_idx
        self.event = None
        self.filtering = False
        self.data_manager = self.parent.data_manager
        
        # Material properties
        self.E = 51e9      # Young's modulus (Pa)
        self.nu = 0.25     # Poisson's ratio
        self.C_s = 2760    # Shear wave speed (m/s)
        self.C_d = 4790    # Longitudinal wave speed (m/s)

        # Create matplotlib figure
        self.create_matplotlib_figure()
            
        # Vertical line attributes
        self.vlines = []
        self.vlines_twin = []
        self.active_line_idx = None
        self.drag_active = False
        
        # Initialize parameter values
        self.Cf = tk.DoubleVar()
        self.y = tk.DoubleVar()
        self.Xc = tk.DoubleVar()
        self.Gc = tk.DoubleVar()
        
        # Load initial event before UI creation
        self.load_event(self.event_idx)
        
        # Configure window
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create UI elements
        self.create_control_frame()
        self.create_parameters_frame()
        
        # Connect event handlers
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        # Initialize event data and combobox
        self.init_event_combobox()
        self.event_combobox.bind("<<ComboboxSelected>>", self.on_event_changed)
        self.filter_spinbox.bind("<Return>", self.update_plot)
        
        # Initial plot
        self.update_plot()

    def create_control_frame(self):
        control_frame = ttk.Frame(self)
        control_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Event selection
        ttk.Label(control_frame, text="Event Index:").pack(side=tk.LEFT, padx=5)
        self.event_combobox = ttk.Combobox(control_frame, width=10)
        self.event_combobox.pack(side=tk.LEFT, padx=5)
        
        # Filter controls
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(filter_frame, text="Filter Window:").pack(side=tk.LEFT, padx=2)
        self.filter_window = tk.IntVar(value=51)
        self.filter_spinbox = ttk.Spinbox(
            filter_frame, 
            from_=3, 
            to=201, 
            increment=2,
            textvariable=self.filter_window,
            width=10,
            validate='all',
            validatecommand=(self.register(self.validate_filter_window), '%P')
        )
        self.filter_spinbox.pack(side=tk.LEFT)
        
        self.filter_button = tk.Button(
            control_frame, 
            text="Filter Off", 
            relief="raised",
            command=self.toggle_filter
        )
        self.filter_button.pack(side=tk.LEFT, padx=5)

    def create_matplotlib_figure(self):
        self.fig = plt.figure(figsize=(10, 6))
        self.gs = self.fig.add_gridspec(2, hspace=0.3)
        self.axs = self.gs.subplots(sharex=True)
        for ax in self.axs:
            ax.grid(True)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.grid(row=2, column=0, padx=0, pady=0, sticky="ew")
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

    def create_parameters_frame(self):
        params_frame = ttk.Frame(self)
        params_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        
        param_configs = [
            ("Cf", self.Cf, 10),
            ("y", self.y, 1e-3),
            ("Xc", self.Xc, 1),
            ("Gc", self.Gc, 1)
        ]
        
        for label_text, var, increment in param_configs:
            frame = ttk.Frame(params_frame)
            frame.pack(side=tk.LEFT, padx=10)
            
            ttk.Label(frame, text=label_text).pack(side=tk.LEFT, padx=2)
            spinbox = ttk.Spinbox(
                frame,
                textvariable=var,
                width=10,
                from_=0,
                to=1e6,
                increment=increment
            )
            spinbox.pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(params_frame)
        button_frame.pack(side=tk.LEFT, padx=10)
        
        # Add Update button
        update_button = ttk.Button(
            button_frame,
            text="Update",
            command=self.update_plot
        )
        update_button.pack(side=tk.LEFT, padx=5)
        
        # Add Save button
        save_button = ttk.Button(
            button_frame,
            text="Save",
            command=self.save_parameters
        )
        save_button.pack(side=tk.LEFT, padx=5)

    def load_event(self, event_idx):
        # Clear existing lines from both lists and axes
        for line in self.vlines:
            line.remove()
        for line in self.vlines_twin:
            line.remove()
        self.vlines = []
        self.vlines_twin = []
        
        self.event_idx = event_idx
        self.event = self.data_manager.get_data(f"runs/[{self.run_idx}]/events/[{self.event_idx}]")

        # Update view limits and parameters if saved data exists
        if 'czm_parms' in self.event:
            params = self.event['czm_parms']
            self.x_min = params[6]
            self.x_max = params[7]
            self.Cf.set(params[0])
            self.y.set(params[1])
            self.Xc.set(params[2])
            self.Gc.set(params[3])
            # Create new vertical lines at saved positions
            vline_x0, vline_x1 = params[4], params[5]
            for x_pos in [vline_x0, vline_x1]:
                if hasattr(self, 'axs'):
                    vline = self.axs[0].axvline(x=x_pos, color='g', linestyle='--', alpha=0.5)
                    vline_twin = self.axs[1].axvline(x=x_pos, color='g', linestyle='--', alpha=0.5)
                    self.vlines.append(vline)
                    self.vlines_twin.append(vline_twin)
        else:
            self.x_min = -0.01
            self.x_max = 0.01
            try:
                self.Cf.set(np.abs(self.data_manager.get_data(f"runs/[{self.run_idx}]/events/[{self.event_idx}]/rupture_speed")))
            except:
                self.Cf.set(10)
            self.y.set(8e-3)
            self.Xc.set(1)
            self.Gc.set(1)

        self.axs[0].set_xlim(self.x_min, self.x_max)

    def init_event_combobox(self):
        n_events = len(self.data_manager.get_data(f"runs/[{self.run_idx}]/events"))
        options = [f"{i}" for i in range(n_events)]
        self.event_combobox.config(values=options, state="readonly")
        self.event_combobox.current(self.event_idx)

    def on_event_changed(self, event=None):
        self.load_event(int(self.event_combobox.get()))
        self.update_plot()

    def toggle_filter(self):
        self.filtering = not self.filtering
        if self.filtering:
            self.filter_button.config(text="Filter On", relief="sunken")
        else:
            self.filter_button.config(text="Filter Off", relief="raised")
        self.update_plot()

    def save_parameters(self):
        """Save the current parameters to the event data."""
        if hasattr(self, 'vlines') and self.vlines is not None and len(self.vlines) >= 2:
            vline_x0 = self.vlines[0].get_xdata()[0]
            vline_x1 = self.vlines[1].get_xdata()[0]
            
            # Update x limits from current view
            self.x_min, self.x_max = self.axs[0].get_xlim()
            
            # Create or update the czm_parms in the event data
            params = [
                self.Cf.get(),
                self.y.get(),
                self.Xc.get(),
                self.Gc.get(),
                vline_x0,
                vline_x1,
                self.x_min,
                self.x_max
            ]
            
            # Update the event data
            self.event['czm_parms'] = params
            
            # Also update the parent data structure to ensure persistence
            self.data_manager.set_data(f"runs/[{self.run_idx}]/events/[{self.event_idx}]/czm_parms", params, True)
            self.parent.refresh_tree()
            print(f"Saved parameters for event {self.event_idx}: {params}")

    def update_plot(self, event=None):
        # Store current line positions before clearing
        line_positions = []
        if self.vlines is not None:
            line_positions = [line.get_xdata()[0] for line in self.vlines]
        elif 'czm_parms' in self.event:  # Use saved line positions if available
            line_positions = [self.event['czm_parms'][4], self.event['czm_parms'][5]]

        # Clear existing plots
        xlim_temp = self.axs[0].get_xlim()
        for ax in self.axs:
            ax.clear()

        # Get data
        t = self.event["strain"]["original"]["time"] - self.event["event_time"]
        sxy = DataProcessor.shear_strain_to_stress(
            self.E, self.nu, DataProcessor.voltage_to_strain(self.event["strain"]["original"]["raw"][6])
        )
        syy = DataProcessor.shear_strain_to_stress(
            self.E, self.nu, DataProcessor.voltage_to_strain(self.event["strain"]["original"]["raw"][14])
        )
        sxy *= 1e-6  # Convert to MPa
        syy *= 1e-6  # Convert to MPa

        # Apply filter if enabled
        if self.filtering:
            window_length = self.filter_window.get()
            if window_length % 2 == 0:
                window_length += 1
                self.filter_window.set(window_length)
            sxy = signal.savgol_filter(sxy, window_length, 2)
            syy = signal.savgol_filter(syy, window_length, 2)

        # Handle vertical lines
        if not line_positions:  # Initialize lines if they don't exist
            # Calculate evenly spaced positions across full range
            line_positions = np.linspace(self.x_min, self.x_max, 5)[1:-2]  # Create 7 points and take middle 5

        idx_zero = np.argmin(np.abs(t - line_positions[0]))
        # Plot data
        self.axs[0].plot(t, sxy - sxy[idx_zero], 'b-', label='Sxy')
        self.axs[1].plot(t, syy - syy[idx_zero], 'r-', label='Syy')

        # Add delta_sigma_xy to the Sxy axis
        rupture_speed = self.Cf.get()
        x = t * rupture_speed  # x in meters
        if len(line_positions) >= 2:
            x_zeroed = x - line_positions[1] * rupture_speed  # Zeroed at vertical line index 2
        else:
            x_zeroed = x  # Default to non-zeroed if not enough vertical lines

        # Compute delta_sigma_xy
        delta_sigma_xy, delta_sigma_yy = CohesiveCrack.delta_sigmas(
            x_zeroed, self.y.get(), self.Xc.get(), self.Cf.get(), 
            self.C_s, self.C_d, self.nu, self.Gc.get(), self.E
        )
        self.axs[0].plot(t, -delta_sigma_xy * 1e-6, 'g--', label='CZM')
        self.axs[1].plot(t, delta_sigma_yy * 1e-6, 'g--', label='CZM')

        # Labels and title
        self.axs[1].set_xlabel('Time (s)')
        self.axs[0].set_ylabel('Sxy (MPa)')
        self.axs[1].set_ylabel('Syy (MPa)')
        
        self.fig.suptitle(f"{self.data_manager.get_data('name')} run{self.run_idx:02d} event{self.event_idx}")

        # Clear existing line lists
        self.vlines = []
        self.vlines_twin = []

        # Create/recreate the lines at their positions
        for x_pos in line_positions:
            # Create line in top plot
            vline = self.axs[0].axvline(x=x_pos, color='g', linestyle='--', alpha=0.5)
            self.vlines.append(vline)

            # Create twin line in bottom plot
            vline_twin = self.axs[1].axvline(x=x_pos, color='g', linestyle='--', alpha=0.5)
            self.vlines_twin.append(vline_twin)

        # Add legends to the plots
        self.axs[0].legend()
        self.axs[1].legend()

        self.axs[0].set_xlim(xlim_temp)

        # Refresh canvas
        self.canvas.draw()

    def is_navigation_active(self):
        """Check if pan or zoom tools are currently active."""
        return self.toolbar.mode in ['pan/zoom', 'zoom rect']

    def on_mouse_press(self, event):
        if event.inaxes and not self.is_navigation_active():
            # Check each line to see if click is near it
            for i, vline in enumerate(self.vlines):
                line_x = vline.get_xdata()[0]
                xlim_temp = self.axs[0].get_xlim()
                if abs(event.xdata - line_x) < 0.01 * (xlim_temp[1]-xlim_temp[0]):  # Reduced sensitivity for multiple lines
                    self.drag_active = True
                    self.active_line_idx = i
                    break

    def on_mouse_release(self, event):
        self.drag_active = False
        self.active_line_idx = None

    def on_mouse_move(self, event):
        if self.drag_active and event.inaxes and self.active_line_idx is not None and not self.is_navigation_active():
            # Update active line pair
            new_x = event.xdata
            self.vlines[self.active_line_idx].set_xdata([new_x, new_x])
            self.vlines_twin[self.active_line_idx].set_xdata([new_x, new_x])
            self.canvas.draw_idle()
            self.update_plot()
            
    def validate_filter_window(self, value):
        """Validate that the filter window value is an odd integer."""
        if value == "":  # Allow empty field for editing
            return True
        try:
            val = int(value)
            return val >= 3 and val <= 201 and val % 2 == 1
        except ValueError:
            return False

if __name__ == "__main__":
    pass