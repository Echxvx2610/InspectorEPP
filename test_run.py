import sys
try:
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from src.ui.app import MainWindow
    win = MainWindow()
    win.show()
    print("MainWindow initialized successfully!")
    # Cierre limpio: dispara closeEvent, que detiene el VideoWorker
    win.close()
    sys.exit(0)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
