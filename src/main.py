from PyQt6.QtWidgets import QApplication
import sys
from src.gui.ROV_GUI import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle('ROV控制')
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()