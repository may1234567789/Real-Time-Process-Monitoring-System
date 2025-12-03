# main.py
import sys
from PyQt5.QtWidgets import QApplication

import collector
from analytics import AnalyticsEngine
from gui import MainWindow


def main():
    app = QApplication(sys.argv)

    analytics_engine = AnalyticsEngine(max_history=60)
    window = MainWindow(collector_module=collector, analytics_engine=analytics_engine)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
