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
        self.uploadWidget   = UploadWidget(parent = self)
        self.loadWidget     = LoadWidget(parent = self)

        self.uploadWidget.swap.connect(self._setView)
        self.loadWidget.swap.connect(self._setView)

        # self.uploadWidget.filesRecieved.connect(self._startProcessing)
        
        self.stackLayout = QStackedLayout()
        self.stackLayout.addWidget(self.uploadWidget)
        self.stackLayout.addWidget(self.loadWidget)

        container = QWidget()
        container.setLayout(self.stackLayout)

        self.setCentralWidget(container)

    @pyqtSlot(View)
    def _setView(self, v):
        match v:
            case View.Upload:
                self.stackLayout.setCurrentWidget(self.uploadWidget)
            case View.Load:
                self.stackLayout.setCurrentWidget(self.loadWidget)
        
def main():
    app = QApplication(sys.argv)

    qdarktheme.setup_theme("auto")
    
    maxSize = QGuiApplication.primaryScreen().availableSize()
    maxSize.scale(800, 600, Qt.AspectRatioMode.KeepAspectRatio)

    window = MainWindow()
    window.resize(maxSize)
    window.show()

    sys.exit( app.exec() )

if __name__ == '__main__':
    main()