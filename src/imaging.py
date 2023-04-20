from views import View, ViewWidget
from detection import DocUtils

import traceback

from keras_ocr.pipeline import Pipeline
from keras import backend as K

from PIL import Image

from PyQt6.QtCore import (
    Qt, pyqtSignal, pyqtSlot, QObject,
    QThreadPool, QRunnable, QMutex, QMutexLocker
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QProgressBar, QVBoxLayout, QMessageBox
)   

# Worker Class comes from this repo: https://github.com/mochisue/pyqt-async-sample/blob/7bd6124c3c6fa8e88f792581dbfda44d7144552b/src/sample.py#L144
# Allows for any function to be run using the QThreadPool, works perfectly for our use case of QT's asynchronous features.
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(str, int, int)

# Any function going in here should be able to take the worker object.
class Worker(QRunnable):
    def __init__(self, fn_run, *args, **kwargs):
        super().__init__()
        self.fn_run = fn_run
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.mutex = QMutex()
        self.is_stop = False

    @pyqtSlot()
    def run(self):
        result = None
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

class ImageModel(QObject):
    content_changed = pyqtSignal(str)

    def __init__(self, org, corner, mask, final, parent=None):
        super().__init__(parent)
        self.org = org
        self.corner = corner
        self.tx_mask = mask
        self.final = final

### ------------------------------------------------------------------------------ ###

class LoadWidget(QWidget, ViewWidget):
    result_ready = pyqtSignal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)

        # For now, max 1 process at a time. Will experiement and see how much I can parallize
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(1) 

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setFixedWidth(350)
        self._progress_bar.setValue(0)

        self._label = QLabel()
        self._label.resize(300, 20)

        self.worker = None
        
        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self._progress_bar, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        layout.setContentsMargins(50,20,50,20)
        
        self.setLayout(layout)
    
    def closeEvent(self, a0):
        if isinstance(self.worker, Worker):
            self.worker.stop()
        a0.accept()

    # Replace test thread with full thread
    @pyqtSlot(list)
    def recieve_files(self, img_paths):
        self.start_thread(Worker(self._run_full_thread, img_paths))

    @pyqtSlot(list, str, str)
    def save_files(self, img, path, type):
        self.start_thread(Worker(self._run_save_thread, img, path, type))

    def start_thread(self, worker: Worker):
        worker.signals.error.connect(self._error_thread)
        worker.signals.result.connect(self._result_thread)
        worker.signals.finished.connect(self._finish_thread)
        worker.signals.progress.connect(self._progress_thread)
        self._thread_pool.start(worker)
        self.worker = worker

    def _error_thread(self, message):
        print(message)

    def _result_thread(self, result):
        # Happens when thread is force stopped.
        if result is None:
            return
        
        self.worker = None
        
        if result[0] == 'final':
            QMessageBox.about(self, "Alert", "File Saved!")
            self.swap.emit(View.UPLOAD)
        else:
            self.result_ready.emit(result)
            self.swap.emit(View.RESULT)

    def _finish_thread(self):
        self._thread_pool.waitForDone()

    def _progress_thread(self, text, progress, limit):
        self._label.setText(text)
        self._progress_bar.setRange(0, limit)
        self._progress_bar.setValue(progress)

    def _run_full_thread(self, worker_object: Worker, img_paths):
        worker_object.signals.progress.emit(f"Starting Process", 0, 0)

        pipeline = Pipeline()
        sorted(img_paths)

        progress = 0
        limit = len(img_paths)*2

        result = []
        for id, img in enumerate(img_paths):
            worker_object.signals.progress.emit(f"Cropping Image #{id+1}", progress, limit)
            if worker_object.is_stop:
                return None
            
            org, corner = DocUtils.get_document(img)
            crop = DocUtils.crop_document(org, corner)
            progress += 1

            # For testing purposes skips text removal
            final = DocUtils.get_resized_final(crop, None, height=600)
            result.append(ImageModel(org, corner, None, final))

            # worker_object.signals.progress.emit(f"Removing Text #{id+1}", progress, limit)
            # if worker_object.is_stop:
            #     return None

            # mask = DocUtils.get_text_mask(crop, pipeline)
            # final = DocUtils.get_resized_final(crop, mask, height=600)
            # progress += 1
            
            # result.append(ImageModel(org, corner, mask, final))
            
        worker_object.signals.progress.emit("Wrapping up", progress, limit)
        K.clear_session()
        return 'inputs', result
    
    def _run_save_thread(self, worker_object: Worker, imgs, path, type):
        worker_object.signals.progress.emit(f"Saving as File", 0, 0)

        progress = 0
        limit = len(imgs)

        pil_img: list[Image.Image] = []
        for id, model in enumerate(imgs):
            worker_object.signals.progress.emit(f"Appending page {id}.", progress, limit)
            if worker_object.is_stop:
                return None
            
            crop = DocUtils.crop_document(model.org, model.corner)
            final = DocUtils.get_resized_final(crop, model.tx_mask, width=1000)
            pil_img.append(DocUtils.opencv_to_pil(final))
            progress += 1

        # Could be reused to save as multiple different types
        pil_img[0].save(path, "PDF", resolution=100.0, save_all=True, append_images=pil_img[1:])

        worker_object.signals.progress.emit("Done", 1, 1)
        return 'final', None

    def _run_crop_thread(self, worker_object):
        pass

    def _run_blur_thread(self, worker_object):
        pass