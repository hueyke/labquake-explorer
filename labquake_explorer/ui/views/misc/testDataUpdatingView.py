import tkinter as tk

class TestDataUpdatingView:
    def __init__(self, parent, data, path, update_callback):
        self.parent = parent
        self.data = data
        self.path = path
        self.update_callback = update_callback

        # Create a Toplevel window
        self.window = tk.Toplevel(self.parent.root)  # Use self.parent.root as the master
        self.window.title("Test View")

        # Add the "add 1" button for a specific key
        self.add_button = tk.Button(self.window, text=f"Test", command=self.button_pressed)
        self.add_button.pack()

    def button_pressed(self):
        # self.data['exp']['runs'][0]['name'] = "Test"
        self.data = "Test"

        # Update the main view's label using the callback
        self.update_callback(self.path, self.data)
