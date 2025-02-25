import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal, optimize
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
        self.strain_gauge = tk.IntVar(value=6)  # Default to gauge 6
        self.num_gauges = None  # Will be set after loading event
        
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
        
        # Configure window
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create UI elements
        self.create_control_frame()
        self.create_parameters_frame()
        
        # Load initial event before UI creation
        self.load_event(self.event_idx)
        
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

        # Strain gauge selection
        ttk.Label(control_frame, text="Strain Gauge:").pack(side=tk.LEFT, padx=5)
        self.gauge_combobox = ttk.Combobox(
            control_frame,
            textvariable=self.strain_gauge,
            width=5,
            state="readonly"
        )
        self.gauge_combobox.pack(side=tk.LEFT, padx=5)
        self.gauge_combobox.bind("<<ComboboxSelected>>", self.update_plot)
        
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
            validate='focusout',
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
        
        # Add Fit button
        fit_button = ttk.Button(
            button_frame,
            text="Fit",
            command=self.fit_parameters
        )
        fit_button.pack(side=tk.LEFT, padx=5)
        
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

        # Dynamically determine number of strain gauges
        self.num_gauges = len(self.event["strain"]["original"]["raw"])
        gauge_options = [str(i) for i in range(self.num_gauges)]
        self.gauge_combobox.config(values=gauge_options)

        # Update view limits and parameters if saved data exists
        if 'czm_parms' in self.event:
            params = self.event['czm_parms']
            if isinstance(params, list) and len(params) == 8:
                self._set_parameters(*params[:4])
                vline_x0, vline_x1 = params[4], params[5]
                vline_x2 = vline_x1 * 2 - vline_x0
                self.x_lim_min, self.x_lim_max = params[6], params[7]
                self.strain_gauge.set(min(6, self.num_gauges - 1))
            elif isinstance(params, dict):
                self._set_parameters(params['Cf'], params['y'], params['Xc'], params['Gc'])
                vline_x0, vline_x1, vline_x2 = params['x_min'], params['x_tip'], params['x_max']
                self.x_lim_min, self.x_lim_max = params['x_lim_min'], params['x_lim_max']
                if 'strain_gauge' in params and 0 <= params['strain_gauge'] < self.num_gauges:
                    self.strain_gauge.set(params['strain_gauge'])
                else:
                    self.strain_gauge.set(min(6, self.num_gauges - 1))
            self.gauge_combobox.set(self.strain_gauge.get())
            self._plot_vertical_lines([vline_x0, vline_x1, vline_x2])
            self.event['czm_parms'] = {
                'Cf': self.Cf.get(),
                'y': self.y.get(),
                'Xc': self.Xc.get(),
                'Gc': self.Gc.get(),
                'x_min': vline_x0,
                'x_tip': vline_x1,
                'x_max': vline_x2,
                'x_lim_min': self.x_lim_min,
                'x_lim_max': self.x_lim_max
            }
        else:
            self._set_default_parameters()

        self.axs[0].set_xlim(self.x_lim_min, self.x_lim_max)

    def _set_parameters(self, Cf, y, Xc, Gc):
        """Helper method to set parameters"""
        self.Cf.set(Cf)
        self.y.set(y)
        self.Xc.set(Xc)
        self.Gc.set(Gc)

    def _set_default_parameters(self):
        """Helper method to set default parameters"""
        self.x_lim_min, self.x_lim_max = -0.1, 0.1
        try:
            rupture_speed = self.data_manager.get_data(f"runs/[{self.run_idx}]/events/[{self.event_idx}]/rupture_speed")
            self.Cf.set(np.abs(rupture_speed))
        except:
            self.Cf.set(10)
        self.y.set(8e-3)
        self.Xc.set(1)
        self.Gc.set(1)

    def _plot_vertical_lines(self, positions):
        """Helper method to plot vertical lines"""
        if not hasattr(self, 'axs'):
            return
        for i, x_pos in enumerate(positions):
            color = 'r' if i == 1 else 'g'
            linestyle = '--'
            alpha = 0.5
            vline = self.axs[0].axvline(x=x_pos, color=color, linestyle=linestyle, alpha=alpha)
            vline_twin = self.axs[1].axvline(x=x_pos, color=color, linestyle=linestyle, alpha=alpha)
            self.vlines.append(vline)
            self.vlines_twin.append(vline_twin)

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
            vline_x2 = self.vlines[2].get_xdata()[0]
            
            # Update x limits from current view
            self.x_lim_min, self.x_lim_max = self.axs[0].get_xlim()
            
            # Create or update the czm_parms in the event data
            params = {
                'Cf': self.Cf.get(),
                'y': self.y.get(),
                'Xc': self.Xc.get(),
                'Gc': self.Gc.get(),
                'x_min': vline_x0,
                'x_tip': vline_x1,
                'x_max': vline_x2,
                'x_lim_min': self.x_lim_min,
                'x_lim_max': self.x_lim_max
            }
            
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
            if isinstance(self.event['czm_parms'], list) and len(self.event['czm_parms']) == 8:
                line_positions = [self.event['czm_parms'][4], self.event['czm_parms'][5], self.event['czm_parms'][5]*2-self.event['czm_parms'][4]]
            elif isinstance(self.event['czm_parms'], dict):
                line_positions = [self.event['czm_parms']['x_min'], self.event['czm_parms']['x_tip'], self.event['czm_parms']['x_max']]
        # Handle vertical lines
        if not line_positions:  # Initialize lines if they don't exist
            # Calculate evenly spaced positions across full range
            line_positions = np.linspace(self.x_lim_min, self.x_lim_max, 5)[1:-2]  # Create 5 points and take middle 3

        # Clear existing plots
        xlim_temp = self.axs[0].get_xlim()
        for ax in self.axs:
            ax.clear()

        # Get data
        t = self.event["strain"]["original"]["time"] - self.event["event_time"]
        gage_idx = self.strain_gauge.get()
        exy = DataProcessor.voltage_to_strain(self.event["strain"]["original"]["raw"][gage_idx])
        eyy = DataProcessor.voltage_to_strain(self.event["strain"]["original"]["raw"][14])

        # Apply filter if enabled
        if self.filtering:
            window_length = self.filter_window.get()
            if window_length % 2 == 0:
                window_length += 1
                self.filter_window.set(window_length)
            exy = signal.savgol_filter(exy, window_length, 2)
            eyy = signal.savgol_filter(eyy, window_length, 2)

        idx_zero = np.argmin(np.abs(t - line_positions[2]))
        # Plot data
        self.axs[0].plot(t, exy - exy[idx_zero], 'b-', label='Exy')
        self.axs[1].plot(t, eyy - eyy[idx_zero], 'r-', label='Eyy')

        # Add delta_sigma_xy to the Sxy axis
        rupture_speed = self.Cf.get()
        x = -t * rupture_speed  # x in meters
        if len(line_positions) >= 2:
            x_zeroed = x + line_positions[1] * rupture_speed  # Zeroed at vertical line index 2
        else:
            x_zeroed = x  # Default to non-zeroed if not enough vertical lines

        # Compute delta_sigma_xy
        delta_sigma_xx, delta_sigma_xy, delta_sigma_yy = CohesiveCrack.delta_sigmas(
            x_zeroed, self.y.get(), self.Xc.get(), self.Cf.get(), 
            self.C_s, self.C_d, self.nu, self.Gc.get(), self.E
        )
        delta_e_xx, delta_e_xy, delta_e_yy = DataProcessor.stress_to_strain(
            self.E, self.nu, delta_sigma_xx, delta_sigma_xy, delta_sigma_yy
        )
        delta_e_xy -= delta_e_xy[idx_zero]
        delta_e_yy -= delta_e_yy[idx_zero]
        self.axs[0].plot(t, delta_e_xy, 'g--', label='CZM')
        self.axs[1].plot(t, delta_e_yy, 'g--', label='CZM')

        # Labels and title
        self.axs[1].set_xlabel('Time (s)')
        self.axs[0].set_ylabel('Exy')
        self.axs[1].set_ylabel('Eyy')
        
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
        if self.is_navigation_active():
            return  # Let matplotlib handle navigation events

        if event.button == 1:  # Left-click for line dragging
            if event.inaxes:
                # Check each line to see if click is near it
                for i, vline in enumerate(self.vlines):
                    line_x = vline.get_xdata()[0]
                    xlim_temp = self.axs[0].get_xlim()
                    if abs(event.xdata - line_x) < 0.01 * (xlim_temp[1]-xlim_temp[0]):
                        self.drag_active = True
                        self.active_line_idx = i
                        break

    def on_mouse_release(self, event):
        self.drag_active = False
        self.active_line_idx = None

    def on_mouse_move(self, event):
        if self.is_navigation_active():
            return  # Let matplotlib handle navigation events

        if self.drag_active and event.inaxes and self.active_line_idx is not None:
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
    
    def fit_parameters(self):
        """Fit Gamma and Xc parameters to the data between vertical lines."""
        if len(self.vlines) < 3:
            print("Need 3 vertical lines to define fitting region")
            return
            
        # Get x positions of vertical lines
        t0, t1, t2 = sorted([self.vlines[0].get_xdata()[0], self.vlines[1].get_xdata()[0], self.vlines[2].get_xdata()[0]])
        
        # Get experimental data
        t = self.event["strain"]["original"]["time"] - self.event["event_time"]
        gage_idx = self.strain_gauge.get()
        exy = DataProcessor.voltage_to_strain(self.event["strain"]["original"]["raw"][gage_idx])
        
        if self.filtering:
            window_length = self.filter_window.get()
            exy = signal.savgol_filter(exy, window_length, 2)
        
        # Get indices for fitting region
        mask = (t >= t1) & (t <= t2)
        t_fit = t[mask]
        exy_fit = exy[mask]
        
        # Zero the data at the first point
        idx_zero = np.argmin(np.abs(t_fit - t2))
        exy_fit -= exy_fit[idx_zero]
        
        # Define objective function for optimization
        def objective(params):
            Gc, Xc = params
            x = -t_fit * self.Cf.get()
            x_zeroed = x + t1 * self.Cf.get()
            
            delta_sigma_xx, delta_sigma_xy, delta_sigma_yy = CohesiveCrack.delta_sigmas(
                x_zeroed, self.y.get(), Xc, self.Cf.get(), 
                self.C_s, self.C_d, self.nu, Gc, self.E
            )
            delta_e_xx, delta_e_xy, delta_e_yy = DataProcessor.stress_to_strain(
                self.E, self.nu, delta_sigma_xx, delta_sigma_xy, delta_sigma_yy
            )
            delta_e_xy -= delta_e_xy[idx_zero]
            
            return np.sum(((exy_fit - delta_e_xy) * 1e9) ** 2)
        
        # Initial guess
        initial_guess = [self.Gc.get(), self.Xc.get()]
        
        # Bounds for parameters (Gc > 0, Xc > 0)
        bounds = ((1e-6, None), (1e-6, None))
        
        # Perform optimization
        result = optimize.minimize(
            objective, 
            initial_guess,
            bounds=bounds,
            method='L-BFGS-B'
        )
        
        if result.success:
            # Update parameters with fitted values
            self.Gc.set(result.x[0])
            self.Xc.set(result.x[1])
            
            self.update_plot()
            print(f"Fitted parameters: Gc={result.x[0]:.2e}, Xc={result.x[1]:.2f}")
        else:
            print("Fitting failed:", result.message)

if __name__ == "__main__":
    pass