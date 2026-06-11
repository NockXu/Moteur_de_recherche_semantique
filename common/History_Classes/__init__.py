from .HistoryRepository import HistoryRepository
from .HistoryData import HistoryData
from .Tree import Tree
from ui import save_in_config

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import sys

save_in_config("history_path", "./storage/history")

app = QApplication(sys.argv)

history = HistoryRepository()
QTimer.singleShot(0, history.load)