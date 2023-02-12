import sys
import qdarktheme

from views import View, ViewWidget

# import imaging

from PyQt6.QtCore import (
    Qt, pyqtSignal
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QPushButton, 
    QFileDialog, QGridLayout, QVBoxLayout, QStackedLayout, 
    QStyle
)
from PyQt6.QtGui import (
    QGuiApplication, QDragMoveEvent
)

class UploadWidget(QWidget, ViewWidget):
    dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

        self._button = QPushButton()
        self._button.setText("Add Files")
        self._button.clicked.connect(self._getFile)

        self._uploadIcon = QLabel()
        fileDiag = self.style().standardIcon( QStyle.StandardPixmap.SP_FileDialogStart )
        self._uploadIcon.setPixmap( fileDiag.pixmap(50, 50) )
        self._uploadIcon.setGeometry(50, 50, 50, 50)

        buttonLayout = QVBoxLayout()
        buttonLayout.addWidget(self._button)

        gridLayout = QGridLayout()
        gridLayout.addWidget(self._uploadIcon, 0, 0, Qt.AlignmentFlag.AlignHCenter)
        gridLayout.addLayout(buttonLayout, 1, 0)
        self.setLayout(gridLayout)

    def _getFile(self):
        fileName = QFileDialog.getOpenFileNames(self, "Open file", 'c:\\', "Image files (*.jpg *.png)")
        self.dropped.emit(fileName[0])

    def dragEnterEvent(self, e: QDragMoveEvent):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e: QDragMoveEvent):
        if e.mimeData().hasUrls():
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            links = []
            for r in event.mimeData().urls():
                links.append(r)
            self.dropped.emit(links)
            self.swap.emit(View.Upload)
        else:
            event.ignore()

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("New App!")
        self.setMinimumSize(400, 300)
        self.setMaximumSize(800, 600)

        self.input = UploadWidget(parent = self)
        self.input.dropped.connect(self.printFiles)
        self.input.swap.connect(self._setView)

        self.stackLayout = QStackedLayout()
        self.stackLayout.addWidget(self.input)

        container = QWidget()
        container.setLayout(self.stackLayout)

        self.setCentralWidget(container)

    def printFiles(self, list = []):
        print("Dropped in: ", list)

    def _setView(self, v: View):
        match v:
            case View.Upload:
                self.stackLayout.setCurrentWidget(self.input)
                print("testing")
        
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