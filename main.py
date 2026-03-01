import tkinter as tk

from ui import DiskHealthApp


def main():
    root = tk.Tk()
    try:
        root.tk.call("wm", "class", root._w, "DiskHealthMonitor")
    except tk.TclError:
        pass
    DiskHealthApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
