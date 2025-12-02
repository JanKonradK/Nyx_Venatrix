import asyncio
import os
import sys
import time
from datetime import datetime
from typing import List, Dict

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

# Add services to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'services')))

# Mock data for now, will connect to DB later
MOCK_SESSIONS = [
    {"id": "sess_001", "status": "active", "apps": 12, "success": 8, "failed": 1, "start_time": "10:00"},
    {"id": "sess_002", "status": "completed", "apps": 45, "success": 40, "failed": 5, "start_time": "09:00"},
]

MOCK_LOGS = [
    "[10:05:23] INFO: Starting application for Senior Engineer",
    "[10:05:25] INFO: Match score computed: 0.89",
    "[10:05:26] INFO: Effort level set to MEDIUM",
    "[10:05:30] SUCCESS: Form filled successfully",
]

class Dashboard:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.setup_layout()

    def setup_layout(self):
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        self.layout["main"].split_row(
            Layout(name="sessions", ratio=1),
            Layout(name="logs", ratio=2)
        )

    def generate_header(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="right")
        grid.add_row(
            "🚀 Nyx Venatrix - Autonomous Browser Agent",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        return Panel(grid, style="bold white on blue")

    def generate_sessions_table(self) -> Panel:
        table = Table(expand=True, border_style="cyan")
        table.add_column("Session ID", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Apps", justify="right")
        table.add_column("Success", justify="right", style="green")

        for sess in MOCK_SESSIONS:
            status_style = "green" if sess["status"] == "active" else "dim"
            table.add_row(
                sess["id"],
                Text(sess["status"], style=status_style),
                str(sess["apps"]),
                str(sess["success"])
            )

        return Panel(table, title="Active Sessions", border_style="cyan")

    def generate_logs_panel(self) -> Panel:
        log_text = Text()
        for log in MOCK_LOGS[-10:]:
            if "SUCCESS" in log:
                log_text.append(log + "\n", style="green")
            elif "ERROR" in log:
                log_text.append(log + "\n", style="red")
            elif "INFO" in log:
                log_text.append(log + "\n", style="white")
            else:
                log_text.append(log + "\n", style="dim")

        return Panel(log_text, title="Live Logs", border_style="yellow")

    def generate_footer(self) -> Panel:
        return Panel(
            Align.center("Press Ctrl+C to exit"),
            style="dim"
        )

    def update(self):
        self.layout["header"].update(self.generate_header())
        self.layout["sessions"].update(self.generate_sessions_table())
        self.layout["logs"].update(self.generate_logs_panel())
        self.layout["footer"].update(self.generate_footer())

    def run(self):
        with Live(self.layout, refresh_per_second=4, screen=True):
            while True:
                self.update()
                time.sleep(0.25)
                # In real app, we would fetch DB updates here

if __name__ == "__main__":
    try:
        dashboard = Dashboard()
        dashboard.run()
    except KeyboardInterrupt:
        print("Exiting dashboard...")
