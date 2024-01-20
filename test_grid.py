import tkinter as tk

root = tk.Tk()

label1 = tk.Label(root, text="Row 0, Column 0")
label2 = tk.Label(root, text="Row 0, Column 1")
label3 = tk.Label(root, text="Row 1, Column 0")

label1.grid(row=0, column=0)
label2.grid(row=0, column=1)
label3.grid(row=1, column=0)

root.mainloop()