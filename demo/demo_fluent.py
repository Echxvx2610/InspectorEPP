from qfluentwidgets import FluentWidget
import sys
from pathlib import Path

# Asegurar que el proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon , QAction
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QWidget, QVBoxLayout , QGridLayout
from qfluentwidgets import PushButton

# interfaz base de pyside6

# def main():
#     app = QApplication(sys.argv)
#     main_window = QWidget()
#     main_window.setWindowTitle("Demo Fluent")
#     main_window.setGeometry(100, 100, 800, 600)
#     main_window.show()
#     sys.exit(app.exec())

# interfaz base de fluent
def main():
    app = QApplication(sys.argv)
    window = FluentWidget()
    window.setWindowTitle("Demo Fluent")
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()