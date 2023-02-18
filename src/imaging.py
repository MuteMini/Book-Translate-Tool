import traceback
import cv2

from views import View, ViewWidget

from PyQt6.QtCore import (
    Qt, pyqtSignal, pyqtSlot, QObject, QRect,
    QThreadPool, QRunnable, QMutex, QMutexLocker
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QProgressBar, QMessageBox,
    QGridLayout, QVBoxLayout
)

# Worker Class comes from this repo: https://github.com/mochisue/pyqt-async-sample/blob/7bd6124c3c6fa8e88f792581dbfda44d7144552b/src/sample.py#L144
# Allows for any function to be run using the QThreadPool, works perfectly for our use case of QT's asynchronous features.
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal()
    result = pyqtSignal(object)

# Any function going in here should be able to take the worker object.
class Worker(QRunnable):
    def __init__(self, fn_run, *args, **kwargs):
        super(QRunnable, self).__init__()
        self.fn_run = fn_run
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.mutex = QMutex()
        self.is_stop = False

    @pyqtSlot()
    def run(self):
        try:
            with QMutexLocker(self.mutex):
                self.is_stop = False
            result = self.fn_run(self, *self.args, **self.kwargs)
        except:
            self.signals.error.emit(traceback.format_exc())
        else:
            self.signals.finished.emit()
        finally:
            self.signals.result.emit(result)

    def stop(self):
        with QMutexLocker(self.mutex):
            self.is_stop = True

class LoadWidget(QWidget, ViewWidget):
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        # For now, max 1 process at a time. Will experiement and see how much I can parallize
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(1) 

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setFixedWidth(350)
        self._progress_bar.setValue(0)

        self._label = QLabel("Processing Photos")
        self._label.resize(300, 20)
        
        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self._progress_bar, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        layout.setContentsMargins(50,20,50,20)
        
        self.setLayout(layout)
    
    @pyqtSlot(list)
    def recieve_files(self, img_paths):
        worker = Worker(self._increment_progress, img_paths)

        self.start_thread(worker)

    def start_thread(self, worker: Worker):
        worker.signals.error.connect(self.error_thread)
        worker.signals.result.connect(self.result_thread)
        worker.signals.finished.connect(self.finish_thread)
        self.thread_pool.start(worker)

    def error_thread(self, message):
        print(message)

    def result_thread(self, message):
        print(f"Return value:{message}")

    def finish_thread(self):
        print("Asynchronous processing is complete")
        self.thread_pool.waitForDone()

    def _increment_progress(self, worker_object, img_paths):
        print(img_paths)
        import time

        for i in range(0, 101):
            if worker_object.is_stop:
                return "Interrupted"
            self._progress_bar.setValue(i)
            time.sleep(0.1)
    
        return "Completed"