import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from typing import Optional
import os

class IndexPickerView(tk.Toplevel):
    def __init__(self, parent, item_y=None, item_x=None):
        self.root = parent.root
        super().__init__(self.root)
        self.title("Index Picker")
        self.parent = parent
        self.data_manager = parent.data_manager
        
        # Store the initial full path
        self.base_path = None
        if item_y:
            self.base_path = os.path.dirname(item_y)
            self.item_y = os.path.basename(item_y)
        else:
            self.item_y = None
        self.item_x = item_x

        # Grid configuration
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(2, weight=1)

        # Row 0 - Labels
        tk.Label(self, text="X Data").grid(row=0, column=0, padx=5, pady=5)
        tk.Label(self, text="Y Data").grid(row=0, column=1, padx=5, pady=5)
        tk.Label(self, text="Picked Index").grid(row=0, column=3, padx=5, pady=5)

        # Row 1 - Comboboxes and Textbox
        self.data_x_combo = ttk.Combobox(self, state="readonly")
        self.data_x_combo.grid(row=1, column=0, padx=5, pady=5)
        self.data_y_combo = ttk.Combobox(self, state="readonly")
        self.data_y_combo.grid(row=1, column=1, padx=5, pady=5)
        self.index_textbox = tk.Entry(self, state="readonly")
        self.index_textbox.grid(row=1, column=3, padx=5, pady=5)

        # Row 2 - Matplotlib Figure and Canvas
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")

        # Row 3 - Navigation toolbar
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.grid(row=3, column=0, columnspan=4, padx=0, pady=0, sticky="ew")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

        # Data points initialization
        self.index_y = None
        self.index_x = None
        self.data_x = []
        self.data_y = []
        self.markers = []
        self.offset = [0, 0]
        self.mouse_button_pressed = None
        self.current_artist = None
        self.currently_dragging = False
        self.picked_idx = []

        # Initialize UI components
        self.init_comboboxes()
        self.plot_data()
        if len(self.data_y) > 0:
            self.picked_idx = [int(len(self.data_y)/3), int(len(self.data_y)/3*2)]
            self.plot_picked_points()

        # Event bindings
        self.figure.canvas.mpl_connect('pick_event', self.on_pick)
        self.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.figure.canvas.mpl_connect('resize_event', self.on_resize)
        self.figure.canvas.mpl_connect('scroll_event', self.on_resize)
        self.data_y_combo.bind("<<ComboboxSelected>>", self.data_y_selected)
        self.data_x_combo.bind("<<ComboboxSelected>>", self.data_x_selected)

    def data_y_selected(self, event):
        """Handle Y-data combobox selection"""
        self.item_y = self.data_y_combo.get()
        self.plot_data()
        self.plot_picked_points()

    def data_x_selected(self, event):
        """Handle X-data combobox selection"""
        self.item_x = self.data_x_combo.get()
        self.plot_data()
        self.plot_picked_points()

    def plot_data(self):
        """Plot the selected data on the matplotlib figure"""
        if self.item_y is None:
            return
        
        if self.item_x is None:
            self.ax.clear()
            y_path = os.path.join(self.base_path, self.item_y) if self.base_path else self.item_y
            self.data_y = self.parent.data_manager.get_data(y_path)
            self.data_x = np.array([])  # Empty array for when no x data is selected
            self.ax.plot(self.data_y, zorder=-100)
            self.ax.set_ylabel(self.item_y)
            self.ax.set_xlabel("Index")
        else:
            self.ax.clear()
            x_path = os.path.join(self.base_path, self.item_x) if self.base_path else self.item_x
            y_path = os.path.join(self.base_path, self.item_y) if self.base_path else self.item_y
            self.data_x = self.parent.data_manager.get_data(x_path)
            self.data_y = self.parent.data_manager.get_data(y_path)
            self.ax.plot(self.data_x, self.data_y, zorder=-100)
            self.ax.set_ylabel(self.item_y)
            self.ax.set_xlabel(self.item_x)
        self.canvas.draw()

    def plot_picked_points(self):
        """Plot the picked points on the graph"""
        width, height = self.get_circle_dims()
        
        # Remove old markers properly
        for marker in self.markers:
            if marker in self.ax.patches:
                marker.remove()
        self.markers = []
        
        # Create new markers
        for i in range(len(self.picked_idx)):
            idx = self.picked_idx[i]
            x = self.data_x[idx] if len(self.data_x) > 0 else idx
            y = self.data_y[idx]
            marker = patches.Ellipse((x, y), width=width, height=height, color='red', fill=False, lw=2, picker=8, label=str(i))
            self.ax.add_patch(marker)
            self.markers.append(marker)
        
        self.canvas.draw()
        picked_indices = [int(idx) for idx in self.picked_idx]
        self.set_index_textbox(str(picked_indices))

    def on_pick(self, event):
        """Handle pick events for the markers"""
        if self.current_artist is None:
            self.current_artist = event.artist
            if isinstance(event.artist, patches.Ellipse):
                x0, y0 = self.current_artist.center
                x1, y1 = event.mouseevent.xdata, event.mouseevent.ydata
                self.offset = [(x0 - x1), (y0 - y1)]

    def on_motion(self, event):
        """Handle motion events for dragging markers"""
        if not self.currently_dragging:
            return
        if self.current_artist is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        
        if isinstance(self.current_artist, patches.Ellipse):
            try:
                dx, dy = self.offset
                cx, cy = event.xdata + dx, event.ydata + dy
                xl = self.ax.get_xlim()
                yl = self.ax.get_ylim()
                yw = yl[-1] - yl[0]
                xw = xl[-1] - xl[0]
                
                # Handle case where no x data is selected
                if len(self.data_x) == 0:
                    # Use index as x coordinate
                    x_values = np.arange(len(self.data_y))
                    idx = np.argmin(((x_values - cx) / xw) ** 2 + ((self.data_y - cy) / yw) ** 2)
                    x_coord = idx
                else:
                    # Use actual x data
                    idx = np.argmin(((self.data_x - cx) / xw) ** 2 + ((self.data_y - cy) / yw) ** 2)
                    x_coord = self.data_x[idx]
                
                # Update marker position
                self.current_artist.set_center((x_coord, self.data_y[idx]))
                self.canvas.draw()
                self.picked_idx[int(self.current_artist.get_label())] = idx
                picked_indices = [int(idx) for idx in self.picked_idx]
                self.set_index_textbox(str(picked_indices))
            except Exception as e:
                print(f"Error in on_motion: {e}")

    def on_press(self, event):
        """Handle mouse press events"""
        self.currently_dragging = True
        if event.button == 1:
            self.mouse_button_pressed = "left"
        else:
            self.mouse_button_pressed = "right"

    def on_release(self, event):
        """Handle mouse release events"""
        self.current_artist = None
        self.currently_dragging = False
        self.on_resize(None)

    def get_circle_dims(self):
        """Calculate dimensions for the marker circles"""
        self.canvas.draw()
        xl = self.ax.get_xlim()
        yl = self.ax.get_ylim()
        ratio = (yl[-1] - yl[0]) / (xl[-1] - xl[0])
        fig_size = self.figure.get_size_inches()
        ratio *= fig_size[0] / fig_size[1]
        width = (xl[-1] - xl[0]) / fig_size[0] * 0.15
        return width, width * ratio

    def on_resize(self, event):
        """Handle window resize events"""
        if self.ax:
            width, height = self.get_circle_dims()
            for marker in self.markers:
                marker.set_width(width)
                marker.set_height(height)
            self.canvas.draw()

    def init_comboboxes(self):
        """Initialize comboboxes with available data items"""
        items = []
        i = 0
        
        # Get the parent of the selected item
        selected_item = None
        if self.item_y:
            full_path = os.path.join(self.base_path, self.item_y) if self.base_path else self.item_y
            for item in self.parent.data_tree.get_children(""):
                if self._find_item_by_path(item, full_path):
                    selected_item = self._find_item_by_path(item, full_path)
                    break
        
        if selected_item:
            parent_id = self.parent.data_tree.parent(selected_item)
            
            # Get all siblings
            if parent_id:
                siblings = self.parent.data_tree.get_children(parent_id)
                self.base_path = self.parent.get_full_path(parent_id)[0]
            else:
                siblings = self.parent.data_tree.get_children("")
                self.base_path = ""
                
            # Add each array sibling
            for item in siblings:
                item_text = self.parent.data_tree.item(item)['text']
                if ':' in item_text and "array" in item_text.split(':')[1]:
                    item_label = item_text.split(':')[0].strip()
                    items.append(item_label)
                    if item_label == self.item_y:
                        self.index_y = i
                    elif item_label == self.item_x:
                        self.index_x = i
                    i += 1
        
        # Update comboboxes
        self.data_x_combo.config(values=items)
        self.data_y_combo.config(values=items)
        if self.index_y is not None:
            self.data_y_combo.current(self.index_y)
        if self.index_x is not None:
            self.data_x_combo.current(self.index_x)

    def _find_item_by_path(self, current_item: str, target_path: str) -> Optional[str]:
        """Recursively find a tree item by its full path"""
        current_path = self.parent.get_full_path(current_item)[0]
        if current_path == target_path:
            return current_item

        # Search children
        for child in self.parent.data_tree.get_children(current_item):
            result = self._find_item_by_path(child, target_path)
            if result:
                return result

        return None

    def set_index_textbox(self, text):
        """Update the index textbox with new value"""
        self.index_textbox.config(state="normal")
        self.index_textbox.delete(0, tk.END)
        self.index_textbox.insert(0, text)
        self.index_textbox.config(state="readonly")
        self.clipboard_clear()
        self.clipboard_append(text)
        