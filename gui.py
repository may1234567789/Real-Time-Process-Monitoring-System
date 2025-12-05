# gui.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QHeaderView, QMessageBox, QListWidget, QListWidgetItem,
    QLineEdit, QComboBox, QFrame, QSplitter, QStatusBar, QSizePolicy
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    """
    Matplotlib canvas embedded in PyQt.
    """
    def __init__(self, parent=None):
        self.fig = Figure()
        self.axes_cpu = self.fig.add_subplot(211)
        self.axes_mem = self.fig.add_subplot(212)
        super().__init__(self.fig)
        self.setParent(parent)


class MainWindow(QMainWindow):
    def __init__(self, collector_module, analytics_engine, parent=None):
        super().__init__(parent)

        self.collector = collector_module
        self.analytics = analytics_engine

        self.setWindowTitle("Real-Time Process Monitoring Dashboard")
        self.resize(1350, 800)

        # ===== Global style (dark) =====
        self._apply_styles()

        # ===== Central widget root layout =====
        central = QWidget()
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(central)

        # ------------------------------------------------------------------
        # LEFT SIDEBAR
        # ------------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(80)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 20, 10, 20)
        side_layout.setSpacing(20)

        # Logo
        logo = QLabel("⚙️")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFont(QFont("Segoe UI Emoji", 26))
        side_layout.addWidget(logo)

        # Nav buttons
        nav_items = [
            ("🏠", "Overview"),
            ("📈", "Graphs"),
            ("🧾", "Processes"),
            ("⚡", "Alerts"),
        ]
        for icon, label in nav_items:
            btn = QPushButton(icon)
            btn.setObjectName("iconButton")
            btn.setFixedSize(50, 50)
            btn.clicked.connect(
                lambda _, section=label: self.handle_sidebar_click(section)
            )
            side_layout.addWidget(btn, alignment=Qt.AlignHCenter)

        side_layout.addStretch()

        # Profile
        profile = QLabel("MB")
        profile.setObjectName("profileBadge")
        profile.setAlignment(Qt.AlignCenter)
        profile.setFixedSize(40, 40)
        side_layout.addWidget(profile, alignment=Qt.AlignHCenter)

        root_layout.addWidget(sidebar)

        # ------------------------------------------------------------------
        # MAIN CONTENT AREA
        # ------------------------------------------------------------------
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(16, 14, 16, 10)
        main_layout.setSpacing(12)
        root_layout.addWidget(main_area)

        # ===== TOP BAR =====
        top_bar = QHBoxLayout()
        top_bar.setSpacing(20)

        title_block = QVBoxLayout()
        title_lbl = QLabel("Stats")
        title_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        subtitle_lbl = QLabel("Real-Time Process Monitoring")
        subtitle_lbl.setFont(QFont("Segoe UI", 10))
        subtitle_lbl.setStyleSheet("color: #8f9bb3;")

        title_block.addWidget(title_lbl)
        title_block.addWidget(subtitle_lbl)
        top_bar.addLayout(title_block)

        top_bar.addStretch()

        self.lbl_cpu = QLabel("CPU: -- %")
        self.lbl_mem = QLabel("Memory: -- % (-- / -- GB)")
        for lbl in (self.lbl_cpu, self.lbl_mem):
            lbl.setObjectName("pillLabel")
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl.setMinimumWidth(180)
            top_bar.addWidget(lbl)

        main_layout.addLayout(top_bar)

        # ===== MAIN SPLITTER =====
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(6)
        main_layout.addWidget(self.main_splitter, stretch=1)

        # ------------------------------------------------------------------
        # LEFT CENTER: cards + process table
        # ------------------------------------------------------------------
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)

        # Stat cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        self.card_cpu = self._build_stat_card("CPU Load", "-- %", "Overall CPU usage.")
        self.card_mem = self._build_stat_card("Memory Usage", "-- %", "Current RAM utilization.")
        self.card_proc = self._build_stat_card("Processes", "--", "Total running processes.")

        cards_row.addWidget(self.card_cpu)
        cards_row.addWidget(self.card_mem)
        cards_row.addWidget(self.card_proc)

        center_layout.addLayout(cards_row)

        # Process table card
        table_card = QFrame()
        table_card.setObjectName("card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(14, 10, 14, 12)
        table_layout.setSpacing(8)

        header_row = QHBoxLayout()
        lbl_table_title = QLabel("Process List")
        lbl_table_title.setFont(QFont("Segoe UI", 11, QFont.Bold))

        header_row.addWidget(lbl_table_title)
        header_row.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search process by name…")
        self.search_box.textChanged.connect(self._filter_table)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["CPU ↓", "Memory ↓", "PID ↑"])
        self.sort_combo.currentIndexChanged.connect(self._sort_table)

        header_row.addWidget(self.search_box)
        header_row.addWidget(self.sort_combo)

        table_layout.addLayout(header_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["PID", "Name", "Status", "CPU %", "Memory (MB)", "Action"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        table_layout.addWidget(self.table)
        center_layout.addWidget(table_card, stretch=1)

        self.main_splitter.addWidget(center_container)

        # ------------------------------------------------------------------
        # RIGHT PANEL: graphs + alerts
        # ------------------------------------------------------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Graphs card
        graphs_card = QFrame()
        graphs_card.setObjectName("card")
        graphs_layout = QVBoxLayout(graphs_card)
        graphs_layout.setContentsMargins(14, 10, 14, 10)
        graphs_layout.setSpacing(6)

        lbl_graph_title = QLabel("System Activity")
        lbl_graph_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        graphs_layout.addWidget(lbl_graph_title)

        self.canvas = MplCanvas(self)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        graphs_layout.addWidget(self.canvas)

        right_layout.addWidget(graphs_card, stretch=2)

        # Alerts card
        alerts_card = QFrame()
        alerts_card.setObjectName("card")
        alerts_layout = QVBoxLayout(alerts_card)
        alerts_layout.setContentsMargins(14, 8, 14, 10)
        alerts_layout.setSpacing(6)

        lbl_alerts = QLabel("Alerts")
        lbl_alerts.setFont(QFont("Segoe UI", 11, QFont.Bold))

        self.alert_list = QListWidget()
        self.alert_list.setAlternatingRowColors(True)

        alerts_layout.addWidget(lbl_alerts)
        alerts_layout.addWidget(self.alert_list)

        right_layout.addWidget(alerts_card, stretch=1)

        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)

        # ===== Status bar =====
        status = QStatusBar()
        status.showMessage("Monitoring started")
        self.setStatusBar(status)

        # For filtering/sorting
        self._current_processes = []

        # ===== Timer =====
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh_dashboard)
        self.timer.start()

    # ==================================================================
    # Styling helpers
    # ==================================================================
    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #050710;
            }

            QWidget {
                background-color: #050710;
                color: #e5e9f0;
            }

            QLabel {
                color: #e5e9f0;
            }

            #sidebar {
                background-color: #05060c;
                border-right: 1px solid #151827;
            }

            QPushButton#iconButton {
                background-color: #101321;
                border-radius: 16px;
                border: none;
                font-size: 18px;
            }
            QPushButton#iconButton:hover {
                background-color: #181b2b;
            }

            #profileBadge {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7f5af0, stop:1 #2cb67d
                );
                border-radius: 20px;
                color: white;
                font-weight: bold;
                font-size: 11px;
            }

            QFrame#card {
                background-color: #0c1020;
                border-radius: 18px;
                border: 1px solid #15192b;
            }

            QLabel#pillLabel {
                background-color: #101524;
                border-radius: 16px;
                padding: 6px 14px;
            }

            /* Process table */
            QTableWidget {
                background-color: #0d1122;
                color: #e5e9f0;
                gridline-color: #22263a;
                border-radius: 12px;
                alternate-background-color: #101524;
            }
            QTableWidget::item {
                background-color: transparent;
            }
            QTableWidget::item:alternate {
                background-color: #101524;
            }
            QTableWidget::item:selected {
                background-color: #3b82f6;
            }

            QHeaderView::section {
                background-color: #0c1020;
                color: #aeb6cf;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #15192b;
            }

            /* Alerts list – dark, no white alt rows */
            QListWidget {
                background-color: #0d1122;
                border-radius: 12px;
                color: #e5e9f0;
                alternate-background-color: #101524;
            }
            QListView::item {
                background-color: transparent;
            }
            QListView::item:alternate {
                background-color: #101524;
            }
            QListView::item:selected {
                background-color: #3b82f6;
            }

            QLineEdit {
                background-color: #0d1122;
                border-radius: 12px;
                padding: 6px 10px;
                border: 1px solid #1b2034;
                color: #ffffff;
            }

            QComboBox {
                background-color: #0d1122;
                border-radius: 12px;
                padding: 6px 10px;
                border: 1px solid #1b2034;
                color: #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #0d1122;
                selection-background-color: #3b82f6;
            }

            /* Generic buttons */
            QPushButton {
                background-color: #3b82f6;
                border-radius: 12px;
                border: none;
                padding: 4px 10px;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4c8ff9;
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }

            /* Smaller Kill button */
            QPushButton#killButton {
                padding: 2px 6px;
                font-size: 10px;
                border-radius: 8px;
                min-width: 40px;
                max-width: 50px;
            }

            QStatusBar {
                background-color: #05060c;
                color: #9ca3af;
            }
        """)

    def _build_stat_card(self, title, value, subtitle):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        card.setStyleSheet("""
            QFrame#card {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #111827, stop:1 #1f2937
                );
                border-radius: 18px;
                border: 1px solid #1f2937;
            }
        """)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl_title.setStyleSheet("color: #9ca3af;")

        lbl_value = QLabel(value)
        lbl_value.setObjectName("cardValue")
        lbl_value.setFont(QFont("Segoe UI", 18, QFont.Bold))

        lbl_sub = QLabel(subtitle)
        lbl_sub.setFont(QFont("Segoe UI", 8))
        lbl_sub.setStyleSheet("color: #6b7280;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        layout.addStretch()
        layout.addWidget(lbl_sub)

        card.value_label = lbl_value
        return card

    # ==================================================================
    # Sidebar click handler (make it "do something")
    # ==================================================================
    def handle_sidebar_click(self, section_name: str):
        """
        Now actually focuses the relevant part of the UI + status message.
        """
        if section_name == "Graphs":
            self.canvas.setFocus()
            self.statusBar().showMessage("Graphs focused", 2000)
        elif section_name == "Processes":
            self.table.setFocus()
            self.statusBar().showMessage("Process list focused", 2000)
        elif section_name == "Alerts":
            self.alert_list.setFocus()
            self.statusBar().showMessage("Alerts focused", 2000)
        else:  # Overview
            # reset splitter to default proportions
            self.main_splitter.setSizes([3, 2])
            self.statusBar().showMessage("Overview", 2000)

    # ==================================================================
    # Refresh / update
    # ==================================================================
    def refresh_dashboard(self):
        system_stats = self.collector.get_system_stats()
        processes = self.collector.get_process_list()
        self._current_processes = processes

        self.analytics.update_history(system_stats)
        alerts = self.analytics.check_alerts(system_stats)

        self.update_system_labels_and_cards(system_stats, processes)
        self._populate_table(processes)
        self.update_charts()
        self.update_alerts(alerts)

    def update_system_labels_and_cards(self, stats: dict, processes):
        cpu = stats["cpu_percent"]
        mem_used = stats["memory_used"] / (1024 * 1024 * 1024)
        mem_total = stats["memory_total"] / (1024 * 1024 * 1024)
        mem_percent = stats["memory_percent"]
        proc_count = len(processes)

        self.lbl_cpu.setText(f"CPU: {cpu:.1f} %")
        self.lbl_mem.setText(
            f"Memory: {mem_percent:.1f} % ({mem_used:.2f} / {mem_total:.2f} GB)"
        )

        self.card_cpu.value_label.setText(f"{cpu:.1f} %")
        self.card_mem.value_label.setText(f"{mem_percent:.1f} %")
        self.card_proc.value_label.setText(str(proc_count))

        if cpu > 90:
            self.lbl_cpu.setStyleSheet("background-color:#991b1b; border-radius:16px; padding:6px 14px;")
        elif cpu > 80:
            self.lbl_cpu.setStyleSheet("background-color:#92400e; border-radius:16px; padding:6px 14px;")
        else:
            self.lbl_cpu.setStyleSheet("background-color:#101524; border-radius:16px; padding:6px 14px;")

        if mem_percent > 90:
            self.lbl_mem.setStyleSheet("background-color:#991b1b; border-radius:16px; padding:6px 14px;")
        elif mem_percent > 80:
            self.lbl_mem.setStyleSheet("background-color:#92400e; border-radius:16px; padding:6px 14px;")
        else:
            self.lbl_mem.setStyleSheet("background-color:#101524; border-radius:16px; padding:6px 14px;")

    # ==================================================================
    # Table + filter + sort
    # ==================================================================
    def _filter_table(self):
        query = self.search_box.text().strip().lower()
        if not self._current_processes:
            return

        if not query:
            self._populate_table(self._current_processes)
            return

        filtered = [
            p for p in self._current_processes
            if query in str(p["name"]).lower()
        ]
        self._populate_table(filtered)

    def _sort_table(self):
        if not self._current_processes:
            return

        idx = self.sort_combo.currentIndex()
        processes = list(self._current_processes)

        if idx == 0:  # CPU ↓
            processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
        elif idx == 1:  # Memory ↓
            processes.sort(key=lambda p: p["memory_mb"], reverse=True)
        elif idx == 2:  # PID ↑
            processes.sort(key=lambda p: p["pid"])

        query = self.search_box.text().strip().lower()
        if query:
            processes = [
                p for p in processes
                if query in str(p["name"]).lower()
            ]

        self._populate_table(processes)

    def _populate_table(self, processes):
        self.table.setRowCount(len(processes))

        for row, proc in enumerate(processes):
            item_pid = QTableWidgetItem(str(proc["pid"]))
            item_pid.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_pid)

            item_name = QTableWidgetItem(str(proc["name"]))
            self.table.setItem(row, 1, item_name)

            item_status = QTableWidgetItem(str(proc["status"]))
            self.table.setItem(row, 2, item_status)

            item_cpu = QTableWidgetItem(f"{proc['cpu_percent']:.1f}")
            item_cpu.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_cpu)

            item_mem = QTableWidgetItem(f"{proc['memory_mb']:.1f}")
            item_mem.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_mem)

            btn_kill = QPushButton("Kill")
            btn_kill.setObjectName("killButton")
            btn_kill.clicked.connect(
                lambda _, pid=proc["pid"], name=proc["name"]: self.handle_kill_process(pid, name)
            )
            self.table.setCellWidget(row, 5, btn_kill)

    # ==================================================================
    # Charts
    # ==================================================================
    def update_charts(self):
        self.canvas.axes_cpu.cla()
        self.canvas.axes_mem.cla()

        times = list(self.analytics.time_history)
        cpu_vals = list(self.analytics.cpu_history)
        mem_vals = list(self.analytics.memory_history)

        if times:
            x = list(range(len(times)))
            max_labels = 8
            step = max(1, len(times) // max_labels)
            tick_positions = x[::step]
            tick_labels = [times[i] for i in tick_positions]

            self.canvas.axes_cpu.plot(x, cpu_vals, marker='o')
            self.canvas.axes_cpu.set_ylabel("CPU %")
            self.canvas.axes_cpu.set_ylim(0, 100)
            self.canvas.axes_cpu.set_title("CPU Usage (Recent)")
            self.canvas.axes_cpu.grid(True, alpha=0.25)
            self.canvas.axes_cpu.set_xticks(tick_positions)
            self.canvas.axes_cpu.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)

            self.canvas.axes_mem.plot(x, mem_vals, marker='o')
            self.canvas.axes_mem.set_ylabel("Memory %")
            self.canvas.axes_mem.set_ylim(0, 100)
            self.canvas.axes_mem.set_xlabel("Time")
            self.canvas.axes_mem.set_title("Memory Usage (Recent)")
            self.canvas.axes_mem.grid(True, alpha=0.25)
            self.canvas.axes_mem.set_xticks(tick_positions)
            self.canvas.axes_mem.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)

            self.canvas.fig.tight_layout()

        self.canvas.draw()

    # ==================================================================
    # Alerts
    # ==================================================================
    def update_alerts(self, alerts):
        for alert in alerts:
            text = f"[{alert['time']}] [{alert['level']}] {alert['message']}"
            item = QListWidgetItem(text)

            if alert["level"] == "CRITICAL":
                item.setForeground(Qt.red)
            elif alert["level"] == "WARNING":
                item.setForeground(Qt.yellow)

            self.alert_list.addItem(item)
            self.alert_list.scrollToBottom()

    # ==================================================================
    # Process kill
    # ==================================================================
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
