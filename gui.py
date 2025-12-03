# gui.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QHeaderView, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import QTimer, Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    """
    Matplotlib canvas embedded in PyQt.
    """
    def __init__(self, parent=None):
        fig = Figure()
        self.axes_cpu = fig.add_subplot(211)
        self.axes_mem = fig.add_subplot(212)
        super().__init__(fig)
        self.setParent(parent)


class MainWindow(QMainWindow):
    def __init__(self, collector_module, analytics_engine, parent=None):
        super().__init__(parent)

        self.collector = collector_module
        self.analytics = analytics_engine

        self.setWindowTitle("Real-Time Process Monitoring Dashboard")
        self.resize(1100, 700)

        # ===== Top-level layout =====
        central = QWidget()
        main_layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # === Top info (CPU & Memory labels) ===
        info_layout = QHBoxLayout()
        self.lbl_cpu = QLabel("CPU: -- %")
        self.lbl_mem = QLabel("Memory: -- % (-- / -- GB)")
        self.lbl_cpu.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.lbl_mem.setStyleSheet("font-size: 14px; font-weight: bold;")
        info_layout.addWidget(self.lbl_cpu)
        info_layout.addWidget(self.lbl_mem)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        # === Middle area: left = process table, right = charts ===
        middle_layout = QHBoxLayout()
        main_layout.addLayout(middle_layout, stretch=1)

        # Process table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["PID", "Name", "Status", "CPU %", "Memory (MB)", "Action"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)

        middle_layout.addWidget(self.table, stretch=3)

        # Charts
        self.canvas = MplCanvas(self)
        middle_layout.addWidget(self.canvas, stretch=3)

        # === Bottom area: alerts ===
        bottom_layout = QVBoxLayout()
        bottom_label = QLabel("Alerts")
        bottom_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.alert_list = QListWidget()

        bottom_layout.addWidget(bottom_label)
        bottom_layout.addWidget(self.alert_list, stretch=1)
        main_layout.addLayout(bottom_layout)

        # Timer for periodic refresh
        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # 1000 ms = 1 second
        self.timer.timeout.connect(self.refresh_dashboard)
        self.timer.start()

    def refresh_dashboard(self):
        # 1. Get data from collector
        system_stats = self.collector.get_system_stats()
        processes = self.collector.get_process_list()

        # 2. Update analytics
        self.analytics.update_history(system_stats)
        alerts = self.analytics.check_alerts(system_stats)

        # 3. Update GUI elements
        self.update_system_labels(system_stats)
        self.update_process_table(processes)
        self.update_charts()
        self.update_alerts(alerts)

    def update_system_labels(self, stats: dict):
        cpu = stats["cpu_percent"]
        mem_used = stats["memory_used"] / (1024 * 1024 * 1024)  # bytes to GB
        mem_total = stats["memory_total"] / (1024 * 1024 * 1024)
        mem_percent = stats["memory_percent"]

        self.lbl_cpu.setText(f"CPU: {cpu:.1f} %")
        self.lbl_mem.setText(
            f"Memory: {mem_percent:.1f} % ({mem_used:.2f} / {mem_total:.2f} GB)"
        )

        # Color for CPU label
        if cpu > 90:
            self.lbl_cpu.setStyleSheet("color: red; font-weight: bold;")
        elif cpu > 80:
            self.lbl_cpu.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.lbl_cpu.setStyleSheet("color: black; font-weight: bold;")

        # Color for memory label
        if mem_percent > 90:
            self.lbl_mem.setStyleSheet("color: red; font-weight: bold;")
        elif mem_percent > 80:
            self.lbl_mem.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.lbl_mem.setStyleSheet("color: black; font-weight: bold;")

    def update_process_table(self, processes):
        self.table.setRowCount(len(processes))

        for row, proc in enumerate(processes):
            # PID
            item_pid = QTableWidgetItem(str(proc["pid"]))
            item_pid.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_pid)

            # Name
            item_name = QTableWidgetItem(str(proc["name"]))
            self.table.setItem(row, 1, item_name)

            # Status
            item_status = QTableWidgetItem(str(proc["status"]))
            self.table.setItem(row, 2, item_status)

            # CPU %
            item_cpu = QTableWidgetItem(f"{proc['cpu_percent']:.1f}")
            item_cpu.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_cpu)

            # Memory MB
            item_mem = QTableWidgetItem(f"{proc['memory_mb']:.1f}")
            item_mem.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_mem)

            # Action button (Kill)
            btn_kill = QPushButton("Kill")
            btn_kill.clicked.connect(
                lambda _, pid=proc["pid"], name=proc["name"]: self.handle_kill_process(pid, name)
            )
            self.table.setCellWidget(row, 5, btn_kill)

    def update_charts(self):
        # Clear axes
        self.canvas.axes_cpu.cla()
        self.canvas.axes_mem.cla()

        times = list(self.analytics.time_history)
        cpu_vals = list(self.analytics.cpu_history)
        mem_vals = list(self.analytics.memory_history)

        if times:
            # CPU chart
            self.canvas.axes_cpu.plot(times, cpu_vals, marker='o')
            self.canvas.axes_cpu.set_ylabel("CPU %")
            self.canvas.axes_cpu.set_ylim(0, 100)
            self.canvas.axes_cpu.set_title("CPU Usage (Last N Samples)")
            self.canvas.axes_cpu.grid(True)

            # Memory chart
            self.canvas.axes_mem.plot(times, mem_vals, marker='o')
            self.canvas.axes_mem.set_ylabel("Memory %")
            self.canvas.axes_mem.set_ylim(0, 100)
            self.canvas.axes_mem.set_xlabel("Time")
            self.canvas.axes_mem.set_title("Memory Usage (Last N Samples)")
            self.canvas.axes_mem.grid(True)

            self.canvas.figure.tight_layout()

        self.canvas.draw()

    def update_alerts(self, alerts):
        for alert in alerts:
            text = f"[{alert['time']}] [{alert['level']}] {alert['message']}"
            item = QListWidgetItem(text)
            if alert["level"] == "CRITICAL":
                item.setForeground(Qt.red)
            elif alert["level"] == "WARNING":
                item.setForeground(Qt.darkYellow)
            self.alert_list.addItem(item)
            self.alert_list.scrollToBottom()

    def handle_kill_process(self, pid, name):
        reply = QMessageBox.question(
            self,
            "Confirm Kill",
            f"Are you sure you want to terminate '{name}' (PID: {pid})?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.collector.kill_process(pid)
            if success:
                QMessageBox.information(self, "Success", f"Process {name} (PID: {pid}) terminated.")
            else:
                QMessageBox.warning(self, "Failed", f"Could not terminate PID {pid}.")
