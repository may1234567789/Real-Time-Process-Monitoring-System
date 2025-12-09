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
    """Matplotlib canvas embedded in PyQt."""
    def __init__(self, parent=None):
        fig = Figure()
        # store fig on self so other code can access it
        self.fig = fig
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

        # apply dark modern styles
        self._apply_styles()

        # central layout
        central = QWidget()
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(central)

        # ----------------- LEFT SIDEBAR -----------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(80)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 20, 10, 20)
        side_layout.setSpacing(18)

        logo = QLabel("⚙️")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFont(QFont("Segoe UI Emoji", 26))
        side_layout.addWidget(logo)

        # nav items (icon, label)
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
            # bind the label in default arg to avoid late binding trap
            btn.clicked.connect(lambda _, s=label: self.handle_sidebar_click(s))
            side_layout.addWidget(btn, alignment=Qt.AlignHCenter)

        side_layout.addStretch()

        profile = QLabel("MB")
        profile.setObjectName("profileBadge")
        profile.setAlignment(Qt.AlignCenter)
        profile.setFixedSize(40, 40)
        side_layout.addWidget(profile, alignment=Qt.AlignHCenter)

        root_layout.addWidget(sidebar)

        # ----------------- MAIN AREA -----------------
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(16, 14, 16, 10)
        main_layout.setSpacing(12)
        root_layout.addWidget(main_area)

        # Top bar (title + pills)
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

        # ---------- Splitter: left = center_container, right = right_panel ----------
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(6)
        main_layout.addWidget(self.main_splitter, stretch=1)

        # ----- LEFT CENTER CONTAINER -----
        self.center_container = QWidget()
        center_layout = QVBoxLayout(self.center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)

        # stat cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self.card_cpu = self._build_stat_card("CPU Load", "-- %", "Overall CPU usage.")
        self.card_mem = self._build_stat_card("Memory Usage", "-- %", "Current RAM utilization.")
        self.card_proc = self._build_stat_card("Processes", "--", "Total running processes.")
        cards_row.addWidget(self.card_cpu)
        cards_row.addWidget(self.card_mem)
        cards_row.addWidget(self.card_proc)
        center_layout.addLayout(cards_row)

        # process list card
        self.table_card = QFrame()
        self.table_card.setObjectName("card")
        table_layout = QVBoxLayout(self.table_card)
        table_layout.setContentsMargins(14, 10, 14, 12)
        table_layout.setSpacing(8)

        header_row = QHBoxLayout()
        lbl_table_title = QLabel("Process List")
        lbl_table_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_row.addWidget(lbl_table_title)
        header_row.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search process...")
        self.search_box.textChanged.connect(self._filter_table)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["CPU ↓", "Memory ↓", "PID ↑"])
        self.sort_combo.currentIndexChanged.connect(self._sort_table)

        header_row.addWidget(self.search_box)
        header_row.addWidget(self.sort_combo)
        table_layout.addLayout(header_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["PID", "Name", "Status", "CPU %", "Memory (MB)", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # sensible initial column widths (PID & Action narrower)
        self.table.setColumnWidth(0, 80)   # PID
        self.table.setColumnWidth(3, 80)   # CPU %
        self.table.setColumnWidth(4, 110)  # Memory
        self.table.setColumnWidth(5, 100)  # Action (Kill)

        table_layout.addWidget(self.table)
        center_layout.addWidget(self.table_card, stretch=1)

        # add center container to splitter
        self.main_splitter.addWidget(self.center_container)

        # ----- RIGHT PANEL (graphs + alerts) -----
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # graphs card
        self.graphs_card = QFrame()
        self.graphs_card.setObjectName("card")
        graphs_layout = QVBoxLayout(self.graphs_card)
        graphs_layout.setContentsMargins(14, 10, 14, 10)
        graphs_layout.setSpacing(6)

        lbl_graph_title = QLabel("System Activity")
        lbl_graph_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        graphs_layout.addWidget(lbl_graph_title)

        self.canvas = MplCanvas(self)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        graphs_layout.addWidget(self.canvas)
        right_layout.addWidget(self.graphs_card, stretch=2)

        # alerts card
        self.alerts_card = QFrame()
        self.alerts_card.setObjectName("card")
        alerts_layout = QVBoxLayout(self.alerts_card)
        alerts_layout.setContentsMargins(14, 8, 14, 10)
        alerts_layout.setSpacing(6)

        lbl_alerts = QLabel("Alerts")
        lbl_alerts.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.alert_list = QListWidget()
        self.alert_list.setAlternatingRowColors(True)
        alerts_layout.addWidget(lbl_alerts)
        alerts_layout.addWidget(self.alert_list)
        right_layout.addWidget(self.alerts_card, stretch=1)

        self.main_splitter.addWidget(self.right_panel)

        # Give initial left-heavy ratio for Overview
        # left ~850px, right ~600px (tweak as desired)
        self.center_container.setMinimumWidth(600)
        self.center_container.setMaximumWidth(16777215)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setSizes([850, 600])

        # status bar
        status = QStatusBar()
        status.showMessage("Monitoring started")
        self.setStatusBar(status)

        # internal
        self._current_processes = []
        self.current_view = "Overview"
        self.set_view_mode("Overview")

        # timer
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.refresh_dashboard)
        self.timer.start()

    # ----------------- Styling -----------------
    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #050710; }
            QWidget { background-color: #050710; color: #e5e9f0; }
            QLabel { color: #e5e9f0; }

            #sidebar { background-color: #05060c; border-right: 1px solid #151827; }

            QPushButton#iconButton {
                background-color: #101321; border-radius: 16px; border: none; font-size: 18px;
            }
            QPushButton#iconButton:hover { background-color: #181b2b; }

            #profileBadge {
                background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #7f5af0, stop:1 #2cb67d);
                border-radius: 20px; color: white; font-weight: bold; font-size: 11px;
            }

            QFrame#card { background-color: #0c1020; border-radius: 18px; border: 1px solid #15192b; }

            QLabel#pillLabel {
                background-color: #101524; border-radius: 16px; padding: 6px 14px;
            }

            /* Process table */
            QTableWidget {
                background-color: #0d1122; color: #e5e9f0; gridline-color: #22263a; border-radius: 12px;
                alternate-background-color: #101524;
            }
            QTableWidget::item { background-color: transparent; }
            QTableWidget::item:alternate { background-color: #101524; }
            QTableWidget::item:selected { background-color: #3b82f6; }

            QHeaderView::section {
                background-color: #0c1020; color: #aeb6cf; padding: 6px; border: none;
                border-bottom: 1px solid #15192b;
            }

            /* Alerts dark */
            QListWidget {
                background-color: #0d1122; border-radius: 12px; color: #e5e9f0; alternate-background-color: #101524;
            }
            QListView::item { background-color: transparent; }
            QListView::item:alternate { background-color: #101524; }
            QListView::item:selected { background-color: #3b82f6; }

            QLineEdit, QComboBox {
                background-color: #0d1122; border-radius: 12px; padding: 6px 10px; border: 1px solid #1b2034; color: #ffffff;
            }

            QPushButton {
                background-color: #3b82f6; border-radius: 12px; border: none; padding: 4px 10px; color: white; font-weight: 500;
            }
            QPushButton:hover { background-color: #4c8ff9; }
            QPushButton:pressed { background-color: #2563eb; }

            /* Kill button styling */
            QPushButton#killButton {
                background-color: #2563eb; border-radius: 16px; padding: 6px 14px;
                font-size: 12px; font-weight: 700; min-width: 56px; max-width: 72px;
            }
            QPushButton#killButton:hover { background-color: #3b82f6; }
            QPushButton#killButton:pressed { background-color: #1d4ed8; }

            QStatusBar { background-color: #05060c; color: #9ca3af; }
        """)

    # ----------------- Helper: stat card -----------------
    def _build_stat_card(self, title, value, subtitle):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        card.setStyleSheet("""
            QFrame#card {
                background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #111827, stop:1 #1f2937);
                border-radius: 18px; border: 1px solid #1f2937;
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

    # ----------------- View mode handling -----------------
    def set_view_mode(self, mode: str):
        """
        Modes:
          - Overview: everything visible (left-heavy)
          - Graphs: only graphs (right panel full)
          - Processes: only process list (left panel full)
          - Alerts: only alerts (right panel full)
        """
        self.current_view = mode

        if mode == "Overview":
            self.center_container.show()
            self.right_panel.show()
            self.graphs_card.show()
            self.alerts_card.show()

            # allow left panel expansion and prefer left-heavy ratio
            self.center_container.setMinimumWidth(600)
            self.center_container.setMaximumWidth(16777215)
            self.main_splitter.setStretchFactor(0, 3)
            self.main_splitter.setStretchFactor(1, 2)
            self.main_splitter.setSizes([850, 600])

        elif mode == "Graphs":
            # hide left so right gets all space
            self.center_container.hide()
            self.center_container.setMinimumWidth(0)
            self.center_container.setMaximumWidth(0)

            self.right_panel.show()
            self.graphs_card.show()
            self.alerts_card.hide()
            self.main_splitter.setSizes([0, 1])

        elif mode == "Processes":
            # show only left, allow it to expand fully
            self.center_container.show()
            self.right_panel.hide()
            self.graphs_card.show()
            self.alerts_card.show()

            self.center_container.setMinimumWidth(0)
            self.center_container.setMaximumWidth(16777215)
            self.main_splitter.setStretchFactor(0, 3)
            self.main_splitter.setStretchFactor(1, 1)
            self.main_splitter.setSizes([900, 0])

        elif mode == "Alerts":
            # show only alerts
            self.center_container.hide()
            self.center_container.setMinimumWidth(0)
            self.center_container.setMaximumWidth(0)

            self.right_panel.show()
            self.graphs_card.hide()
            self.alerts_card.show()
            self.main_splitter.setSizes([0, 1])

        # show feedback
        self.statusBar().showMessage(f"{mode} view", 1200)

    def handle_sidebar_click(self, section_name: str):
        self.set_view_mode(section_name)

    # ----------------- Refresh / update -----------------
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
        self.lbl_mem.setText(f"Memory: {mem_percent:.1f} % ({mem_used:.2f} / {mem_total:.2f} GB)")

        self.card_cpu.value_label.setText(f"{cpu:.1f} %")
        self.card_mem.value_label.setText(f"{mem_percent:.1f} %")
        self.card_proc.value_label.setText(str(proc_count))

        # pill colors
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

    # ----------------- Table population -----------------
    def _filter_table(self):
        query = self.search_box.text().strip().lower()
        if not self._current_processes:
            return
        if not query:
            self._populate_table(self._current_processes)
            return
        filtered = [p for p in self._current_processes if query in str(p["name"]).lower()]
        self._populate_table(filtered)

    def _sort_table(self):
        if not self._current_processes:
            return
        idx = self.sort_combo.currentIndex()
        processes = list(self._current_processes)
        if idx == 0:
            processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
        elif idx == 1:
            processes.sort(key=lambda p: p["memory_mb"], reverse=True)
        elif idx == 2:
            processes.sort(key=lambda p: p["pid"])
        query = self.search_box.text().strip().lower()
        if query:
            processes = [p for p in processes if query in str(p["name"]).lower()]
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

            # Kill button (centered in cell)
            btn_kill = QPushButton("Kill")
            btn_kill.setObjectName("killButton")
            # center in a widget layout
            cell_widget = QWidget()
            h_layout = QHBoxLayout(cell_widget)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.addStretch()
            h_layout.addWidget(btn_kill)
            h_layout.addStretch()

            # ensure proper binding of pid/name in the callback
            btn_kill.clicked.connect(lambda _, p=proc["pid"], n=proc["name"]: self.handle_kill_process(p, n))
            self.table.setCellWidget(row, 5, cell_widget)

        # keep action column narrow so name column can be wide
        self.table.setColumnWidth(5, 110)
        self.table.setColumnWidth(0, 80)

    # ----------------- Charts -----------------
    # ----------------- Charts -----------------
    def update_charts(self):
        """Update CPU and memory charts with error handling."""
        try:
            # Check if canvas exists and has valid size
            if not self.canvas or self.canvas.width() <= 0 or self.canvas.height() <= 0:
                return
            
            if not self.analytics.time_history or len(self.analytics.cpu_history) == 0:
                return
            
            self.canvas.axes_cpu.clear()
            self.canvas.axes_mem.clear()

            times = list(self.analytics.time_history)
            cpu_vals = list(self.analytics.cpu_history)
            mem_vals = list(self.analytics.memory_history)

            x = list(range(len(times)))
            max_labels = 8
            step = max(1, len(times) // max_labels)
            tick_positions = x[::step]
            tick_labels = [times[i] for i in tick_positions]

            # CPU chart
            self.canvas.axes_cpu.plot(x, cpu_vals, marker='o', linewidth=2, color='#3b82f6')
            self.canvas.axes_cpu.set_ylabel("CPU %")
            self.canvas.axes_cpu.set_ylim(0, 100)
            self.canvas.axes_cpu.set_title("CPU Usage (Recent)")
            self.canvas.axes_cpu.grid(True, alpha=0.25)
            self.canvas.axes_cpu.set_xticks(tick_positions)
            self.canvas.axes_cpu.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)

            # Memory chart
            self.canvas.axes_mem.plot(x, mem_vals, marker='o', linewidth=2, color='#ef4444')
            self.canvas.axes_mem.set_ylabel("Memory %")
            self.canvas.axes_mem.set_ylim(0, 100)
            self.canvas.axes_mem.set_xlabel("Time")
            self.canvas.axes_mem.set_title("Memory Usage (Recent)")
            self.canvas.axes_mem.grid(True, alpha=0.25)
            self.canvas.axes_mem.set_xticks(tick_positions)
            self.canvas.axes_mem.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)

            # Use subplots_adjust instead of tight_layout (avoids singular matrix error)
            self.canvas.fig.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.15, hspace=0.7)
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating charts: {e}")
            # Continue running even if chart update fails
            pass

    # ----------------- Alerts -----------------
    def update_alerts(self, alerts):
        MAX_ALERTS = 100
        for alert in alerts:
            text = f"[{alert['time']}] [{alert['level']}] {alert['message']}"
            item = QListWidgetItem(text)
            if alert["level"] == "CRITICAL":
                item.setForeground(Qt.red)
            elif alert["level"] == "WARNING":
                item.setForeground(Qt.yellow)
            self.alert_list.addItem(item)
            self.alert_list.scrollToBottom()
        
        # Remove old alerts if list gets too large
        while self.alert_list.count() > MAX_ALERTS:
            self.alert_list.takeItem(0)
    # ----------------- Process kill -----------------
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
