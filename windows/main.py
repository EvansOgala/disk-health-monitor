import os

if os.name == "nt":
    from pyside_ui import DiskHealthQtApp
else:
    from ui import DiskHealthApp


def main():
    if os.name == "nt":
        DiskHealthQtApp.run_app()
    else:
        app = DiskHealthApp()
        app.run(None)


if __name__ == "__main__":
    main()
