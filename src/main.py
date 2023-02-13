import sys
import qdarktheme

from views import View

from imaging import LoadWidget
from display import UploadWidget

from PyQt6.QtCore import (
    Qt, pyqtSlot
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QStackedLayout
)
from PyQt6.QtGui import (
    QGuiApplication
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("New App!")
        self.setMinimumSize(400, 300)
        self.setMaximumSize(800, 600)

        # All scenes being initialized
        self.upload_widget   = UploadWidget(parent = self)
        self.load_widget     = LoadWidget(parent = self)

        self.upload_widget.swap.connect(self._set_view)
        self.load_widget.swap.connect(self._set_view)

        # self.upload_widget.files_recieved.connect(self._startProcessing)
        
        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(self.upload_widget)
        self.stack_layout.addWidget(self.load_widget)

        container = QWidget()
        container.setLayout(self.stack_layout)

        self.setCentralWidget(container)

    @pyqtSlot(View)
    def _set_view(self, v):
        match v:
            case View.UPLOAD:
                self.stack_layout.setCurrentWidget(self.upload_widget)
            case View.LOAD:
                self.stack_layout.setCurrentWidget(self.load_widget)
        
def main():
    app = QApplication(sys.argv)

    qdarktheme.setup_theme("auto")
    
    max_size = QGuiApplication.primaryScreen().availableSize()
    max_size.scale(800, 600, Qt.AspectRatioMode.KeepAspectRatio)

    window = MainWindow()
    window.resize(max_size)
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()