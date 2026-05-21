from .HistoryRepository import HistoryRepository
from .HistoryData import HistoryData
from .Tree import Tree
from ui import save_in_config

from PyQt6.QtWidgets import QApplication
import sys

save_in_config("history_path", "./storage/history")

app = QApplication(sys.argv)

history = HistoryRepository()
history.load()