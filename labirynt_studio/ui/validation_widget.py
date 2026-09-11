"""Panel walidacji wyświetlający błędy i ostrzeżenia w projekcie."""

from typing import List, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt, Signal
from ..validation.validator import ValidationIssue


class ValidationWidget(QWidget):
    issue_activated = Signal(str, int, int)  # screen_id, x, y

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.summary_label = QLabel("Status walidacji: OK")
        font = self.summary_label.font()
        font.setBold(True)
        self.summary_label.setFont(font)
        layout.addWidget(self.summary_label)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)

    def set_issues(self, issues: List[ValidationIssue]):
        self.list_widget.clear()

        errors_count = sum(1 for i in issues if i.severity == "ERROR")
        warnings_count = sum(1 for i in issues if i.severity == "WARNING")

        if errors_count == 0 and warnings_count == 0:
            self.summary_label.setText("Status walidacji: Brak błędów (OK)")
            self.summary_label.setStyleSheet("color: #4CAF50;")
            return

        status_text = f"Status walidacji: {errors_count} błędów, {warnings_count} ostrzeżeń"
        color = "#F44336" if errors_count > 0 else "#FF9800"
        self.summary_label.setText(status_text)
        self.summary_label.setStyleSheet(f"color: {color};")

        for issue in issues:
            prefix = "[BŁĄD]" if issue.severity == "ERROR" else "[OSTRZEŻENIE]"
            screen_info = f"[{issue.screen_id}] " if issue.screen_id else ""
            item = QListWidgetItem(f"{prefix} {screen_info}{issue.message}")
            
            if issue.severity == "ERROR":
                item.setForeground(QColor(230, 60, 60))
            else:
                item.setForeground(QColor(240, 160, 30))

            item.setData(Qt.ItemDataRole.UserRole, (issue.screen_id, issue.x, issue.y))
            self.list_widget.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            screen_id, x, y = data
            if screen_id:
                self.issue_activated.emit(screen_id, x if x is not None else 0, y if y is not None else 0)
