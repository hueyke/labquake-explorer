import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
import numpy as np
from scipy import stats
import os


class EventAnalyzerView(tk.Toplevel):
    def __init__(self, parent, run_idx, event_idx, item_y="shear_stress", item_x="displacement"):
        self.parent = parent
        super().__init__(self.parent.root)
        self.title(f"Event Analyzer - Event {event_idx}")

        # Initialize data attributes
        self.run_idx = run_idx
        self.event_idx = event_idx
        self.data_manager = self.parent.data_manager
        self.event = None

        # Load event data
        self.event = self.data_manager.get_data(f"runs/[{self.run_idx}]/events/[{self.event_idx}]")

        # Store the initial data fields
        self.item_y = item_y  # Default to shear_stress
        self.item_x = item_x  # Default to displacement

        # Configure window layout - adjust to accommodate event selection
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)  # Make column 2 expandable
        self.grid_rowconfigure(2, weight=1)

        # Create event selection frame
        event_selection_frame = ttk.LabelFrame(self, text="Event Selection")
        event_selection_frame.grid(row=0, column=0, rowspan=2, padx=5, pady=5, sticky="nsw")

        # Event selection combobox
        ttk.Label(event_selection_frame, text="Event Index:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.event_combobox = ttk.Combobox(event_selection_frame, width=10, state="readonly")
        self.event_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.save_button = ttk.Button(event_selection_frame, text="Save Event", command=self.save_results, width=15)
        self.save_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # Create data selection frame
        data_frame = ttk.LabelFrame(self, text="Data Fields")
        data_frame.grid(row=0, column=1, rowspan=2, columnspan=2, padx=5, pady=5, sticky="nsew")

        # X and Y data selectors within the frame
        tk.Label(data_frame, text="X Data:", width=8, anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.data_x_combo = ttk.Combobox(data_frame, state="readonly", width=20)
        self.data_x_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        tk.Label(data_frame, text="Y Data:", width=8, anchor="e").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.data_y_combo = ttk.Combobox(data_frame, state="readonly", width=20)
        self.data_y_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Create frame for results display
        results_frame = ttk.LabelFrame(self, text="Analysis Results")
        results_frame.grid(row=0, column=3, rowspan=2, columnspan=1, padx=5, pady=5, sticky="nsew")

        # Create textboxes for slope and other metrics with consistent width and alignment
        tk.Label(results_frame, text="Loading Stiffness:", anchor="e", width=18).grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.loading_slope_text = tk.Entry(results_frame, state="readonly", width=12, justify="right")
        self.loading_slope_text.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        tk.Label(results_frame, text="Unloading Stiffness:", anchor="e", width=18).grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.rupture_slope_text = tk.Entry(results_frame, state="readonly", width=12, justify="right")
        self.rupture_slope_text.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        tk.Label(results_frame, text="Stress Drop:", anchor="e", width=12).grid(row=0, column=2, padx=5, pady=2, sticky="e")
        self.stress_drop_text = tk.Entry(results_frame, state="readonly", width=12, justify="right")
        self.stress_drop_text.grid(row=0, column=3, padx=5, pady=2, sticky="w")

        tk.Label(results_frame, text="Displacement:", anchor="e", width=12).grid(row=1, column=2, padx=5, pady=2, sticky="e")
        self.displacement_text = tk.Entry(results_frame, state="readonly", width=12, justify="right")
        self.displacement_text.grid(row=1, column=3, padx=5, pady=2, sticky="w")

        # Create matplotlib figure with better styling
        self.figure = Figure(figsize=(10, 6), dpi=100, facecolor='#f5f5f5')
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#ffffff')
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")

        # Add navigation toolbar
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.grid(row=3, column=0, columnspan=4, padx=0, pady=0, sticky="ew")
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

        # Initialize data attributes
        self.data_x = []
        self.data_y = []

        # Initialize marker attributes
        self.markers = []
        self.current_artist = None
        self.currently_dragging = False
        self.offset = [0, 0]

        # Points to track (6 points total)
        # Points 0,1: Loading slope segment
        # Points 2,3: Rupture slope segment
        # Point 4: Rupture start
        # Point 5: Rupture end
        self.picked_idx = []

        # Initialize lines for visualization
        self.loading_line = None
        self.rupture_line = None
        self.rupture_span = None

        # Initialize event combobox
        self.init_event_combobox()

        # Connect event handler
        self.event_combobox.bind("<<ComboboxSelected>>", self.on_event_changed)

        # Init comboboxes and data
        self.init_comboboxes()

        # Check for saved analysis and load it
        if 'event_analysis' in self.event:
            saved_analysis = self.event['event_analysis']
            if ('loading_indices' in saved_analysis and 
                'unloading_indices' in saved_analysis and
                'rupture_start_index' in saved_analysis and
                'rupture_end_index' in saved_analysis):

                # Use saved indices
                self.picked_idx = [
                    saved_analysis['loading_indices'][0],
                    saved_analysis['loading_indices'][1],
                    saved_analysis['unloading_indices'][0],
                    saved_analysis['unloading_indices'][1],
                    saved_analysis['rupture_start_index'],
                    saved_analysis['rupture_end_index']
                ]
            else:
                # Fall back to default positions
                self._set_default_point_positions()
        else:
            # Set default positions for the 6 points
            self._set_default_point_positions()

        # Plot with points
        self.plot_picked_points()

        # Event bindings
        self.figure.canvas.mpl_connect('pick_event', self.on_pick)
        self.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.figure.canvas.mpl_connect('resize_event', self.on_resize)
        self.data_y_combo.bind("<<ComboboxSelected>>", self.data_selected)
        self.data_x_combo.bind("<<ComboboxSelected>>", self.data_selected)
    
    def _set_default_point_positions(self):
        """Helper method to set default point positions"""
        n = len(self.data_y)
        self.picked_idx = [
            int(n * 0.3),     # Loading slope start
            int(n * 0.45),    # Loading slope end
            int(n * 0.5),     # Rupture slope start
            int(n * 0.7),     # Rupture slope end
            int(n * 0.5),     # Rupture start
            int(n * 0.7)      # Rupture end
        ]
    
    def init_event_combobox(self):
        """Initialize the event selection combobox"""
        n_events = len(self.data_manager.get_data(f"runs/[{self.run_idx}]/events"))
        options = [f"{i}" for i in range(n_events)]
        self.event_combobox.config(values=options)
        self.event_combobox.current(self.event_idx)

    def on_event_changed(self, event=None):
        """Handle event selection from combobox"""
        new_event_idx = int(self.event_combobox.get())
        if new_event_idx != self.event_idx:
            self.event_idx = new_event_idx
            # Update title
            self.title(f"Event Analyzer - Event {self.event_idx}")
            # Load the new event
            self.event = self.data_manager.get_data(f"runs/[{self.run_idx}]/events/[{self.event_idx}]")
            # Reset the comboboxes with new event data
            self.init_comboboxes()
            # Check for saved analysis in the new event
            if 'event_analysis' in self.event:
                saved_analysis = self.event['event_analysis']
                if ('loading_indices' in saved_analysis and 
                    'unloading_indices' in saved_analysis and
                    'rupture_start_index' in saved_analysis and
                    'rupture_end_index' in saved_analysis):

                    # Use saved indices
                    self.picked_idx = [
                        saved_analysis['loading_indices'][0],
                        saved_analysis['loading_indices'][1],
                        saved_analysis['unloading_indices'][0],
                        saved_analysis['unloading_indices'][1],
                        saved_analysis['rupture_start_index'],
                        saved_analysis['rupture_end_index']
                    ]
                else:
                    # Fall back to default positions
                    self._set_default_point_positions()
            else:
                # Set default positions for the 6 points
                self._set_default_point_positions()

            # Update the plot with new data and points
            self.plot_picked_points()

    def init_comboboxes(self):
        """Initialize comboboxes with event fields of the same length as time"""
        # Get time array to use as reference length
        if 'time' in self.event:
            time_length = len(self.event['time'])
        else:
            # Fall back to event_time if 'time' not available
            print("Warning: 'time' field not found in event data")
            return
        
        # Function to recursively find arrays with matching length
        def find_matching_arrays(data, path=""):
            matching_fields = []
            if isinstance(data, dict):
                for key, value in data.items():
                    new_path = f"{path}/{key}" if path else key
                    if isinstance(value, (list, np.ndarray)) and len(value) == time_length:
                        matching_fields.append(new_path)
                    elif isinstance(value, dict):
                        matching_fields.extend(find_matching_arrays(value, new_path))
            return matching_fields
        
        # Get all fields with matching length
        matching_fields = find_matching_arrays(self.event)
        
        # Sort the fields for easier selection
        matching_fields.sort()
        
        # Configure comboboxes
        self.data_x_combo.config(values=matching_fields)
        self.data_y_combo.config(values=matching_fields)
        
        # Set initial selections using smart defaults
        
        # Try to set x_data (displacement)
        if self.item_x and self.item_x in matching_fields:
            self.data_x_combo.set(self.item_x)
        else:
            # Try to find displacement field
            displacement_fields = [f for f in matching_fields if 'displacement' in f.lower()]
            if displacement_fields:
                self.data_x_combo.set(displacement_fields[0])
                self.item_x = displacement_fields[0]
            elif 'time' in matching_fields:
                # Default to time if no displacement field
                self.data_x_combo.set('time')
                self.item_x = 'time'
            elif matching_fields:
                # Last resort: use first field
                self.data_x_combo.set(matching_fields[0])
                self.item_x = matching_fields[0]
        
        # Try to set y_data (shear_stress)
        if self.item_y and self.item_y in matching_fields:
            self.data_y_combo.set(self.item_y)
        else:
            # Try to find shear_stress field
            stress_fields = [f for f in matching_fields if 'shear_stress' in f.lower()]
            if stress_fields:
                self.data_y_combo.set(stress_fields[0])
                self.item_y = stress_fields[0]
            else:
                # Try other stress fields
                other_stress = [f for f in matching_fields if 'stress' in f.lower()]
                if other_stress:
                    self.data_y_combo.set(other_stress[0])
                    self.item_y = other_stress[0]
                elif matching_fields:
                    # Last resort: use first field
                    self.data_y_combo.set(matching_fields[0])
                    self.item_y = matching_fields[0]
        
        # Load the data
        self.plot_data()
    
    def data_selected(self, event=None):
        """Handle data selection from comboboxes"""
        self.item_y = self.data_y_combo.get()
        self.item_x = self.data_x_combo.get()
        
        # First load the data
        self.plot_data()
        
        # If we have saved analysis and changing fields, keep the indices
        if len(self.data_y) > 0 and len(self.picked_idx) == 6:
            # Validate indices are within data range
            max_idx = len(self.data_y) - 1
            for i in range(6):
                if self.picked_idx[i] > max_idx:
                    # Reset to defaults if any index is out of range
                    self._set_default_point_positions()
                    break
        else:
            # Set default positions when data changes or no existing indices
            self._set_default_point_positions()
            
        # Update the plot with points
        self.plot_picked_points()
    
    def plot_data(self):
        """Plot the selected data"""
        if self.item_y is None:
            return
        
        self.ax.clear()
        
        # Helper function to access nested dictionary values using path notation
        def get_nested_data(data_dict, path):
            parts = path.split('/')
            current = data_dict
            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    print(f"Warning: Path '{path}' not found in data")
                    return None
            return current
        
        if self.item_x is None:
            # If no x data is selected, use index
            self.data_y = get_nested_data(self.event, self.item_y)
            if self.data_y is None:
                return
                
            self.data_x = np.arange(len(self.data_y))  # Use indices as x-values
            self.ax.plot(self.data_x, self.data_y, zorder=-100, linewidth=1.5)
            self.ax.set_ylabel(self.item_y)
            self.ax.set_xlabel("Index")
        else:
            # Use selected x and y data
            self.data_x = get_nested_data(self.event, self.item_x)
            self.data_y = get_nested_data(self.event, self.item_y)
            
            if self.data_x is None or self.data_y is None:
                return
                
            self.ax.plot(self.data_x, self.data_y, zorder=-100, linewidth=1.5)
            self.ax.set_ylabel(self.item_y)
            self.ax.set_xlabel(self.item_x)
        
        # Add grid lines
        self.ax.grid(True, linestyle='--', alpha=0.3)
        
        # Set title with run and event info
        self.ax.set_title(f"{self.data_manager.get_data('name')} run{self.run_idx:02d} event{self.event_idx}: {self.item_y} vs {self.item_x if self.item_x else 'Index'}")
        
        # Apply better styling to the plot
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.tick_params(direction='out')
        
        self.canvas.draw()
    
    def plot_picked_points(self):
        """Plot the marker points and connecting lines"""
        if not self.picked_idx or len(self.picked_idx) != 6 or len(self.data_y) == 0:
            return
            
        width, height = self.get_circle_dims()
        
        # Clear existing markers and lines
        for marker in self.markers:
            if marker in self.ax.patches:
                marker.remove()
        self.markers = []
        
        if self.loading_line and self.loading_line in self.ax.lines:
            self.loading_line.remove()
        if self.rupture_line and self.rupture_line in self.ax.lines:
            self.rupture_line.remove()
            
        # Clear any existing span first to prevent accumulation
        if self.rupture_span:
            try:
                self.rupture_span.remove()
            except:
                pass
                
            # Also remove from collections to be thorough
            for coll in self.ax.collections[:]:
                if coll == self.rupture_span:
                    self.ax.collections.remove(coll)
        
        # Ensure all indices are within data range
        max_idx = len(self.data_y) - 1
        valid_indices = True
        for i in range(len(self.picked_idx)):
            if self.picked_idx[i] > max_idx:
                valid_indices = False
                break
                
        if not valid_indices:
            self._set_default_point_positions()
                    
        # Define colors for different point types - using more refined colors
        colors = ['#33CCC4', '#33CCC4', '#CC3366', '#CC3366', '#33CC66', '#33CC66']
        # Create new markers for the 6 points
        for i in range(len(self.picked_idx)):
            idx = self.picked_idx[i]
            if idx >= len(self.data_x) or idx >= len(self.data_y):
                continue
                
            x = self.data_x[idx]
            y = self.data_y[idx]
            
            marker = patches.Ellipse((x, y), width=width, height=height, 
                                     color=colors[i], fill=False, lw=2, 
                                     picker=8, label=str(i))
            self.ax.add_patch(marker)
            self.markers.append(marker)
        
        # Plot loading slope line (between points 0 and 1)
        x_loading = [self.data_x[self.picked_idx[0]], self.data_x[self.picked_idx[1]]]
        y_loading = [self.data_y[self.picked_idx[0]], self.data_y[self.picked_idx[1]]]
        self.loading_line, = self.ax.plot(x_loading, y_loading, '--', color='#33CCC4', 
                                         linewidth=2, zorder=-50, label='Loading Stiffness')
        
        # Plot rupture slope line (between points 2 and 3)
        x_rupture = [self.data_x[self.picked_idx[2]], self.data_x[self.picked_idx[3]]]
        y_rupture = [self.data_y[self.picked_idx[2]], self.data_y[self.picked_idx[3]]]
        self.rupture_line, = self.ax.plot(x_rupture, y_rupture, '--', color='#CC3366',
                                         linewidth=2, zorder=-50, label='Unloading Stiffness')
        
        # Plot shaded area between rupture start and end points (points 4 and 5)
        x_start = self.data_x[self.picked_idx[4]]
        x_end = self.data_x[self.picked_idx[5]]
        self.rupture_span = self.ax.axvspan(x_start, x_end, alpha=0.15, color='#33CC66', zorder=-100)
        
        # Add legend
        # self.ax.legend(loc='best')
        
        # Redraw canvas
        self.canvas.draw()
        
        # Update analysis results
        self.update_analysis()
    
    def get_circle_dims(self):
        """Calculate appropriate dimensions for marker circles based on plot scaling"""
        self.canvas.draw()
        xl = self.ax.get_xlim()
        yl = self.ax.get_ylim()
        ratio = (yl[-1] - yl[0]) / (xl[-1] - xl[0])
        fig_size = self.figure.get_size_inches()
        ratio *= fig_size[0] / fig_size[1]
        width = (xl[-1] - xl[0]) / fig_size[0] * 0.15
        return width, width * ratio
    
    # Updated sections of EventAnalyzerView class to implement linear regression for slope calculations

    def update_analysis(self):
        """Update all calculated values using linear regression for slope calculations"""
        if len(self.picked_idx) != 6:
            return
            
        try:
            # Sort indices to ensure proper range selection
            loading_idx_start = min(self.picked_idx[0], self.picked_idx[1])
            loading_idx_end = max(self.picked_idx[0], self.picked_idx[1])
            
            rupture_idx_start = min(self.picked_idx[2], self.picked_idx[3])
            rupture_idx_end = max(self.picked_idx[2], self.picked_idx[3])
            
            # Get data ranges for linear regression
            loading_indices = range(loading_idx_start, loading_idx_end + 1)
            rupture_indices = range(rupture_idx_start, rupture_idx_end + 1)
            
            # Extract x and y data for linear regression
            x_loading = [self.data_x[i] for i in loading_indices]
            y_loading = [self.data_y[i] for i in loading_indices]
            
            x_rupture = [self.data_x[i] for i in rupture_indices]
            y_rupture = [self.data_y[i] for i in rupture_indices]
            
            # Perform linear regression for loading stiffness
            slope_loading, intercept_loading, r_value_loading, p_value_loading, std_err_loading = stats.linregress(x_loading, y_loading)
            
            # Perform linear regression for unloading/rupture stiffness
            slope_rupture, intercept_rupture, r_value_rupture, p_value_rupture, std_err_rupture = stats.linregress(x_rupture, y_rupture)
            
            # Rupture start/end (points 4,5)
            x4, y4 = self.data_x[self.picked_idx[4]], self.data_y[self.picked_idx[4]]
            x5, y5 = self.data_x[self.picked_idx[5]], self.data_y[self.picked_idx[5]]
            
            # Calculate stress drop and displacement
            stress_drop = abs(y4 - y5)  # Absolute value of change in y (stress)
            displacement = abs(x5 - x4) # Absolute value of change in x (displacement)
            
            # Update textboxes with consistent formatting
            self.set_textbox(self.loading_slope_text, f"{slope_loading:.6g}")
            self.set_textbox(self.rupture_slope_text, f"{slope_rupture:.6g}")
            self.set_textbox(self.stress_drop_text, f"{stress_drop:.6g}")
            self.set_textbox(self.displacement_text, f"{displacement:.6g}")
            
        except (IndexError, ZeroDivisionError) as e:
            print(f"Error calculating values: {e}")
    
    def set_textbox(self, textbox, text):
        """Helper method to set text in a readonly textbox"""
        textbox.config(state="normal")
        textbox.delete(0, tk.END)
        textbox.insert(0, text)
        textbox.config(state="readonly")
    
    def on_pick(self, event):
        """Handle pick events on markers"""
        if self.current_artist is None:
            self.current_artist = event.artist
            if isinstance(event.artist, patches.Ellipse):
                x0, y0 = self.current_artist.center
                x1, y1 = event.mouseevent.xdata, event.mouseevent.ydata
                self.offset = [(x0 - x1), (y0 - y1)]
    
    def on_press(self, event):
        """Handle mouse button press events"""
        self.currently_dragging = True
    
    def on_release(self, event):
        """Handle mouse button release events"""
        self.current_artist = None
        self.currently_dragging = False
        self.on_resize(None)
    
    def on_motion(self, event):
        """Handle mouse motion events for dragging markers"""
        if not self.currently_dragging or self.current_artist is None:
            return
        if event.xdata is None or event.ydata is None:
            return  # Mouse is outside plot area
        
        if isinstance(self.current_artist, patches.Ellipse):
            try:
                # Calculate new position
                dx, dy = self.offset
                cx, cy = event.xdata + dx, event.ydata + dy
                xl = self.ax.get_xlim()
                yl = self.ax.get_ylim()
                yw = yl[-1] - yl[0]
                xw = xl[-1] - xl[0]
                
                # Find nearest data point
                distances = ((self.data_x - cx) / xw) ** 2 + ((self.data_y - cy) / yw) ** 2
                idx = np.argmin(distances)
                
                # Update marker position
                x_coord = self.data_x[idx]
                y_coord = self.data_y[idx]
                self.current_artist.set_center((x_coord, y_coord))
                
                # Update picked index
                point_idx = int(self.current_artist.get_label())
                self.picked_idx[point_idx] = idx
                
                # Update lines
                if point_idx in [0, 1]:  # Loading slope points
                    x_loading = [self.data_x[self.picked_idx[0]], self.data_x[self.picked_idx[1]]]
                    y_loading = [self.data_y[self.picked_idx[0]], self.data_y[self.picked_idx[1]]]
                    self.loading_line.set_data(x_loading, y_loading)
                
                elif point_idx in [2, 3]:  # Rupture slope points
                    x_rupture = [self.data_x[self.picked_idx[2]], self.data_x[self.picked_idx[3]]]
                    y_rupture = [self.data_y[self.picked_idx[2]], self.data_y[self.picked_idx[3]]]
                    self.rupture_line.set_data(x_rupture, y_rupture)
                
                elif point_idx in [4, 5]:  # Rupture span points
                    # Remove existing span properly
                    if self.rupture_span:
                        # Try multiple ways to remove it to ensure it's gone
                        try:
                            self.rupture_span.remove()
                        except:
                            pass
                            
                        # Also try removing from collections
                        for coll in self.ax.collections[:]:
                            if coll == self.rupture_span:
                                self.ax.collections.remove(coll)
                    
                    # Create new span
                    x_start = self.data_x[self.picked_idx[4]]
                    x_end = self.data_x[self.picked_idx[5]]
                    self.rupture_span = self.ax.axvspan(x_start, x_end, alpha=0.15, color='#33CC66', zorder=-100)
                
                # Update analysis values
                self.update_analysis()
                
                # Redraw canvas
                self.canvas.draw_idle()
                
            except Exception as e:
                print(f"Error in on_motion: {e}")
    
    def on_resize(self, event):
        """Handle window resize events to adjust marker sizes"""
        if hasattr(self, 'ax') and self.markers:
            width, height = self.get_circle_dims()
            for marker in self.markers:
                marker.set_width(width)
                marker.set_height(height)
            self.canvas.draw()
    
    def save_results(self):
        """Save the analysis results to the data manager"""
        if len(self.picked_idx) != 6:
            return
            
        try:
            # Create results dictionary with only essential fields
            results = {
                'loading_indices': [self.picked_idx[0], self.picked_idx[1]],
                'unloading_indices': [self.picked_idx[2], self.picked_idx[3]],
                'rupture_start_index': self.picked_idx[4],
                'rupture_end_index': self.picked_idx[5],
                'loading_stiffness': float(self.loading_slope_text.get()),
                'unloading_stiffness': float(self.rupture_slope_text.get()),
                'stress_drop': float(self.stress_drop_text.get()),
                'displacement': float(self.displacement_text.get())
            }
            
            # Save to the event data structure
            save_path = f"runs/[{self.run_idx}]/events/[{self.event_idx}]/event_analysis"
            
            # Save the results
            self.data_manager.set_data(save_path, results, True)
            
            # Also update the event object for persistence
            self.event['event_analysis'] = results
            
            # Refresh tree to show new data
            self.parent.refresh_tree()
            
            # Show confirmation message
            # tk.messagebox.showinfo("Save Successful", 
            #                       f"Event analysis results saved to {save_path}")
                                  
        except Exception as e:
            tk.messagebox.showerror("Save Failed", f"Error saving results: {e}")