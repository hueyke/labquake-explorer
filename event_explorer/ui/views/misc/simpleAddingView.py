import tkinter as tk

class ChildView:
    def __init__(self, parent, data_var, update_callback):
        self.parent = parent
        self.data_var = data_var
        self.update_callback = update_callback

        # Create a Toplevel window
        self.window = tk.Toplevel(self.parent.root)  # Use self.parent.root as the master
        self.window.title("Child View")

        # Add the "add 1" button for a specific key
        self.key = 'counter'
        self.add_button = tk.Button(self.window, text=f"Add 1 to {self.key}", command=self.add_to_data)
        self.add_button.pack(pady=10)

        # Bind the window close event to a method
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def add_to_data(self):
        # Add 1 to the specific key in the dictionary
        current_value = self.data_var.get(self.key, 0)
        self.data_var[self.key] = current_value + 1

        # Update the main view's label using the callback
        self.update_callback()

    def on_close(self):
        self.window.destroy()

class MainView:
    def __init__(self, root):
        self.root = root
        self.root.title("Main View")

        # Shared data dictionary
        self.data_var = {}

        # Add the "Add" button
        self.add_button = tk.Button(root, text="Add", command=self.open_child_view)
        self.add_button.pack(pady=20)

        # Add label to display specific data variable value
        self.key = 'counter'
        self.data_label = tk.Label(root, text=f"{self.key.capitalize()}: 0")
        self.data_label.pack(pady=10)

    def open_child_view(self):
        # Open the child view with the update callback
        child_view = ChildView(self, self.data_var, self.update_data_label)

    def update_data_label(self):
        # Update the label with the new data variable value for a specific key
        self.data_label.config(text=f"{self.key.capitalize()}: {self.data_var.get(self.key, 0)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MainView(root)
    root.mainloop()
