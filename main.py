from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget, QLineEdit, QMessageBox
from PyQt5.QtCore import pyqtSlot, QRunnable, QThreadPool

from widgets import CustomPbar, SelectDirectoryLayout

import sys
import threading
import time
import zipfile

# Unzipping threads limit. The app uses 2 more threads for the UI
THREAD_LIMIT = 4

class Unzipper(QRunnable):
    """Multithreaded Unzipper for a Qt app (`QRunnable`). 
    Divides the zip archive between `x` threads, attempting to allocate about the same size to unzip to each thread"""
    def __init__(self, path, target, progress_bar) -> None:
        super().__init__()
        self.path = path
        self.target = target
        self.my_zip = zipfile.ZipFile(path, 'r')
        self.progress_bar: CustomPbar = progress_bar
        self.progress_bar.setValue(0)

    def allocate_files(self, files) -> tuple[list[list[str]], list[str]]:
        """Basic file allocation based on size, so all threads have around the same amount of work to do;
        workaround for having to allocate more files to finished threads in filelist/THREAD_LIMIT scenario,
        if one of the threads gets only small sized files and finish way before the other.

        Creates a dictionary of files and their sizes, allocates the files based on which thread has the lowest allocation size.
        
        Args:
        ------------
        files: `list`
            List of files in the archive (string directories)

        Returns:
        ------------
        threads_allocation: `list[list[str]]`
            List of allocations for each thread. Each allocation list contains string file directories
        folders: `list[str]`
            List of string folder directories
        """

        sizelist: dict = {file.filename: file.file_size for file in files}
        threads_allocation = [[] for thread in range(0, THREAD_LIMIT)]
        threads_allocation_count: list[int] = [0 for thread in range(0, THREAD_LIMIT)]

        folders = []
        # needed for handling folders first to prevent race conditions

        sorted_sizelist: list = sorted(sizelist.items(), key=lambda x: x[1], reverse=True)
        for file, size in sorted_sizelist:
            if size == 0:
                folders.append(file)
                continue
            lowest_thread = threads_allocation_count.index(min(threads_allocation_count))
            threads_allocation[lowest_thread].append(file)
            threads_allocation_count[lowest_thread] += size

        return threads_allocation, folders

    # running _extract_member directly saves some processing time, though realistically it doesn't have any impact
    def _extract_folders(self, zip_ref: zipfile.ZipFile, folders: list[str]):
        for folder in folders:
            zip_ref._extract_member(folder, self.target, None)

    def _extract_allocation(self, zip_ref: zipfile.ZipFile, allocation, target):
        for filename in allocation:
            zip_ref._extract_member(filename, target, None)
            self.progress_bar.progressSignal.emit()

    @pyqtSlot()
    def run(self):
        start = time.time()
        files = self.my_zip.filelist
        allocations, folders = self.allocate_files(files)
        self.progress_bar.setRange(0, len(files) - len(folders) - 1)

        with self.my_zip as zip_ref:
            # extract folders to assure proper structure and prevent race conditions
            self._extract_folders(zip_ref, folders)

            threads = []
            for allocation in allocations:
                t = threading.Thread(target=self._extract_allocation, args=(zip_ref, allocation, self.target))
                t.start()
                threads.append(t)
        
            for thread in threads:
                thread.join()

        end = time.time()
        print(end - start)

class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

        self.zip_path = ""
        self.target_path = ""

    def _set_layout(self):
        layout = QVBoxLayout()
        layout.addLayout(self.zip_select.directory_layout)
        layout.addLayout(self.target_select.directory_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self._unzip_button)
        self._main.setLayout(layout)

    def init_ui(self):
        self.setWindowTitle('Multithreaded Unzipper')
        self.setGeometry(100, 100, 400, 160)
        self.setFixedSize(self.size())

        self._main = QWidget()
        self.setCentralWidget(self._main)
        self.threadpool = QThreadPool()

        if self.threadpool.maxThreadCount() - THREAD_LIMIT - 2 < 0:
            AppError("Thread limit exceeds number of your CPU threads.", 
                    f"This might slow down the threads performance.\nThe app requires 2 threads to run, you can use rest of the threads.\n \
                    \nTotal Threads: {self.threadpool.maxThreadCount()}\
                    \nTotal Available Threads: {self.threadpool.maxThreadCount()-2}",
                    QMessageBox.Warning)
            
        # widget setup
        self.zip_select = SelectDirectoryLayout("Select Zip File:")
        self.zip_select.set_button_target(lambda: self.choose_file(self.zip_select.directory_textfield))

        self.target_select = SelectDirectoryLayout("Choose Target Directory")
        self.target_select.set_button_target(lambda: self.choose_directory(self.target_select.directory_textfield))

        self.progress_bar = CustomPbar(self)
        self.progress_bar.setFixedWidth(385)

        self._unzip_button = QPushButton("Unzip!")
        self._unzip_button.clicked.connect(self.unzip)

        self._set_layout()
        self.show()

    def choose_file(self, textfield: QLineEdit):
        options = QFileDialog.Options()
        selected_file, _ = QFileDialog.getOpenFileName(self, "Choose File", "", "Zip Files (*.zip)", options=options)
        if selected_file:
            textfield.setText(selected_file)
            self.zip_path = selected_file
        
    def choose_directory(self, textfield: QLineEdit):
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        selected_directory = QFileDialog.getExistingDirectory(self, "Choose Directory", "", options=options)
        if selected_directory:
            textfield.setText(selected_directory)
            self.target_path = selected_directory

    def _verify_inputs(self):
        self.zip_path = self.zip_path or self.zip_select.directory_textfield.text() or None
        if not self.zip_path:
            raise AppError("Missing path to file", "Please enter a path to a Zip archive")

        if not self.zip_path.endswith(".zip"):
            raise AppError("Incorrect path to file", "Please enter a path to a Zip File")
        
        self.target_path = self.target_path or self.target_select.directory_textfield.text() or None
        if not self.target_path:
            raise AppError("Missing target path", "Please enter a correct target path")

    def unzip(self):     
        try:
            self._verify_inputs()
        except AppError:
            return
        
        worker = Unzipper(self.zip_path, self.target_path, self.progress_bar)
        worker.progress_bar.progressSignal.connect(self.progress_bar.update_progress)
        self.threadpool.start(worker)

class AppError(Exception):
    def show_error_alert(self, header, message, error_type):
        if error_type is QMessageBox.Warning:
            title = "Warning"
        error_msg = QMessageBox()
        error_msg.setIcon(error_type)
        error_msg.setWindowTitle(title)
        error_msg.setText(header)
        error_msg.setStandardButtons(QMessageBox.Ok)

        if message:
            error_msg.setInformativeText(message)

        error_msg.exec_()

    def __init__(self, header, message=None, error_type: QMessageBox.Icon = QMessageBox.Warning):
        self.show_error_alert(header, message, error_type)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AppWindow()
    sys.exit(app.exec_())


# THREAD =
# 16.054221868515015
# 18.067972660064697
# 17.995511054992676
# 18.665905237197876
# 18.109553337097168
# WINDOWS =
# 2 minutes 15 seconds
# 7zip = 44.82717299461365
# 1 minute 1 second