from PyQt6.QtCore import (
    Qt, pyqtSignal, QSize
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QWidget,
    QPushButton, QFileDialog, QVBoxLayout
)
from PyQt6.QtGui import (
    QAction, QGuiApplication
)

import qdarktheme
import sys

class DropBoxInput(QWidget):
    dropped = pyqtSignal(list)

    def __init__(self, parent):
        super().__init__(parent)

        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

        self.button = QPushButton()
        self.button.setText("Add Files")
        self.button.clicked.connect(self._getFile)
        # Icon here should be the FileDialogStart

        layout = QVBoxLayout()
        layout.addWidget(self.button)
        self.setLayout(layout)

    def _getFile(self):
        fileName = QFileDialog.getOpenFileNames(self, "Open file", 'c:\\', "Image files (*.jpg *.png)")
        self.dropped.emit(fileName[0])

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            links = []
            for r in event.mimeData().urls():
                links.append(r)
            self.dropped.emit(links)
        else:
            event.ignore()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("New App!")
        self.setMinimumSize(400, 300)
        self.setMaximumSize(800, 600)

        self.input = DropBoxInput(parent = self)
        self.input.dropped.connect(self.printFiles)

        self.setCentralWidget(self.input)

    def printFiles(self, list = []):
        print("Dropped in: ", list)

    def contextMenuEvent(self, e):
        context = QMenu(self)
        context.addAction(QAction("test 1", self))
        context.addAction(QAction("test 2", self))
        context.addAction(QAction("test 3", self))
        context.exec(e.globalPos())
        
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