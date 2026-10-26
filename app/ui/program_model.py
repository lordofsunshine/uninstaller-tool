from __future__ import annotations

from PySide6.QtCore import (
    QAbstractListModel,
    QEvent,
    QModelIndex,
    QRect,
    QSize,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from app.models.program import Program, ProgramStatus

PROGRAM_ROLE = int(Qt.ItemDataRole.UserRole) + 1
KEY_ROLE = int(Qt.ItemDataRole.UserRole) + 2
META_ROLE = int(Qt.ItemDataRole.UserRole) + 3
STATUS_ROLE = int(Qt.ItemDataRole.UserRole) + 4
STATUS_TEXT_ROLE = int(Qt.ItemDataRole.UserRole) + 5

STATUS_TEXTS = {
    ProgramStatus.RUNNING.value: "Removing…",
    ProgramStatus.SUCCESS.value: "Removed",
    ProgramStatus.ERROR.value: "Failed",
}

_EMPTY_INDEX = QModelIndex()


class ProgramModel(QAbstractListModel):
    checked_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._programs: list[Program] = []
        self._index_by_key: dict[str, int] = {}
        self._checkable = True

    def rowCount(self, parent=_EMPTY_INDEX) -> int:
        return 0 if parent.isValid() else len(self._programs)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._programs):
            return None
        program = self._programs[index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.AccessibleTextRole):
            return program.name
        if role == PROGRAM_ROLE:
            return program
        if role == KEY_ROLE:
            return program.key
        if role == META_ROLE:
            return program.meta_text()
        if role == STATUS_ROLE:
            return program.status.value
        if role == STATUS_TEXT_ROLE:
            return STATUS_TEXTS.get(program.status.value, "")
        if role == Qt.ItemDataRole.ToolTipRole:
            return program.install_location or program.name
        if role == Qt.ItemDataRole.AccessibleDescriptionRole:
            return program.meta_text()
        if role == Qt.ItemDataRole.CheckStateRole and self._checkable:
            return (
                Qt.CheckState.Checked
                if program.checked
                else Qt.CheckState.Unchecked
            )
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemNeverHasChildren
        )
        if self._checkable:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def setData(
        self,
        index: QModelIndex,
        value,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role != Qt.ItemDataRole.CheckStateRole or not index.isValid():
            return False
        if not self._checkable:
            return False
        if not 0 <= index.row() < len(self._programs):
            return False
        program = self._programs[index.row()]
        checked = Qt.CheckState(value) == Qt.CheckState.Checked
        if program.checked == checked:
            return True
        program.checked = checked
        self.dataChanged.emit(
            index,
            index,
            [Qt.ItemDataRole.CheckStateRole],
        )
        self.checked_changed.emit()
        return True

    def set_programs(self, programs: list[Program]) -> None:
        self.beginResetModel()
        self._programs = list(programs)
        self._index_by_key = {
            program.key: index for index, program in enumerate(self._programs)
        }
        self.endResetModel()
        self.checked_changed.emit()

    def set_checkable(self, checkable: bool) -> None:
        if self._checkable == checkable:
            return
        self._checkable = checkable
        if self._programs:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._programs) - 1, 0),
                [Qt.ItemDataRole.CheckStateRole],
            )

    def program_at(self, index: QModelIndex | None) -> Program | None:
        if index is None or not index.isValid():
            return None
        row = index.row()
        if 0 <= row < len(self._programs):
            return self._programs[row]
        return None

    def index_for_key(self, key: str) -> QModelIndex:
        row = self._index_by_key.get(key)
        if row is None or not 0 <= row < len(self._programs):
            return QModelIndex()
        return self.index(row, 0)

    def program_for_key(self, key: str) -> Program | None:
        row = self._index_by_key.get(key)
        if row is None:
            return None
        return self._programs[row]

    def set_status(self, key: str, status: ProgramStatus) -> None:
        row = self._index_by_key.get(key)
        if row is None:
            return
        program = self._programs[row]
        if program.status is status:
            return
        program.status = status
        index = self.index(row, 0)
        self.dataChanged.emit(
            index,
            index,
            [STATUS_ROLE, STATUS_TEXT_ROLE],
        )

    def checked_programs(self) -> list[Program]:
        return [program for program in self._programs if program.checked]

    def checked_keys(self) -> set[str]:
        return {program.key for program in self._programs if program.checked}

    def set_checked_keys(self, keys: set[str]) -> None:
        changed = False
        for program in self._programs:
            checked = program.key in keys
            if program.checked != checked:
                program.checked = checked
                changed = True
        if changed and self._programs:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._programs) - 1, 0),
                [Qt.ItemDataRole.CheckStateRole],
            )
            self.checked_changed.emit()

    def clear(self) -> None:
        self.set_programs([])


class ProgramFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = ""
        self._sort_mode = 0
        self.setDynamicSortFilter(True)

    def set_filter_text(self, text: str) -> None:
        query = str(text or "").strip().casefold()
        if query == self._query:
            return
        self._query = query
        self.invalidateFilter()

    def set_sort_mode(self, mode: int) -> None:
        self._sort_mode = int(mode)
        self.invalidate()
        self.sort(0, Qt.SortOrder.AscendingOrder)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._query:
            return True
        model = self.sourceModel()
        if model is None:
            return False
        index = model.index(source_row, 0, source_parent)
        program = model.program_at(index)
        if program is None:
            return False
        haystack = f"{program.name} {program.publisher} {program.version}".casefold()
        return self._query in haystack

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        model = self.sourceModel()
        a = model.program_at(left) if model is not None else None
        b = model.program_at(right) if model is not None else None
        if a is None or b is None:
            return False
        if self._sort_mode == 1:
            return (a.size_kb, a.name.casefold()) > (b.size_kb, b.name.casefold())
        if self._sort_mode == 2:
            return (a.install_date, a.name.casefold()) > (
                b.install_date,
                b.name.casefold(),
            )
        if self._sort_mode == 3:
            return (a.publisher.casefold(), a.name.casefold()) < (
                b.publisher.casefold(),
                b.name.casefold(),
            )
        return a.name.casefold() < b.name.casefold()

    def program_at(self, index: QModelIndex) -> Program | None:
        if index is None or not index.isValid():
            return None
        source = self.mapToSource(index)
        model = self.sourceModel()
        return model.program_at(source) if model is not None else None

    def index_for_key(self, key: str) -> QModelIndex:
        model = self.sourceModel()
        if model is None:
            return QModelIndex()
        source = model.index_for_key(key)
        if not source.isValid():
            return QModelIndex()
        return self.mapFromSource(source)


class ProgramDelegate(QStyledItemDelegate):
    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self._colors = colors

    def set_colors(self, colors) -> None:
        self._colors = colors

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(240, 76)

    def _card_rect(self, rect: QRect) -> QRect:
        return rect.adjusted(2, 4, -2, -4)

    @staticmethod
    def _checkbox_rect(card: QRect) -> QRect:
        return QRect(card.left() + 14, card.center().y() - 10, 20, 20)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = self._colors
        card = self._card_rect(option.rect)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        focused = bool(option.state & QStyle.StateFlag.State_HasFocus)

        background = QColor(colors["surface_alt"] if selected else colors["surface"])
        border = QColor(
            colors["primary"] if selected or focused else colors["border_hover"] if hovered else colors["border"]
        )
        painter.setBrush(background)
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(card.adjusted(0, 0, -1, -1), 14, 14)

        checkbox = self._checkbox_rect(card)
        state = index.data(Qt.ItemDataRole.CheckStateRole)
        self._draw_checkbox(
            painter,
            checkbox,
            state == Qt.CheckState.Checked,
            hovered,
            colors,
            state is not None,
        )

        text_left = checkbox.right() + 16
        status = str(index.data(STATUS_ROLE) or ProgramStatus.IDLE.value)
        status_text = str(index.data(STATUS_TEXT_ROLE) or "")
        text_right = card.right() - 14
        if status != ProgramStatus.IDLE.value and status_text:
            pill = QRect(card.right() - 12 - 96, card.center().y() - 12, 96, 24)
            self._draw_status(painter, pill, status, status_text, colors)
            text_right = pill.left() - 12

        name_rect = QRect(text_left, card.top() + 10, max(20, text_right - text_left), 20)
        meta_rect = QRect(text_left, card.top() + 31, max(20, text_right - text_left), 18)

        name_font = QFont(option.font)
        name_font.setPixelSize(14)
        name_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(name_font)
        painter.setPen(QColor(colors["text"]))
        name = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        name = QFontMetrics(name_font).elidedText(name, Qt.TextElideMode.ElideRight, name_rect.width())
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        meta_font = QFont(option.font)
        meta_font.setPixelSize(12)
        meta_font.setWeight(QFont.Weight.Normal)
        painter.setFont(meta_font)
        painter.setPen(QColor(colors["text_secondary"]))
        meta = str(index.data(META_ROLE) or "")
        meta = QFontMetrics(meta_font).elidedText(meta, Qt.TextElideMode.ElideRight, meta_rect.width())
        painter.drawText(meta_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, meta)

        if focused and not selected:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(colors["primary"]), 1))
            painter.drawRoundedRect(card.adjusted(0, 0, -1, -1), 14, 14)
        painter.restore()

    @staticmethod
    def _draw_checkbox(
        painter: QPainter,
        rect: QRect,
        checked: bool,
        hovered: bool,
        colors,
        enabled: bool,
    ) -> None:
        if enabled:
            border = QColor(colors["primary"] if hovered or checked else colors["scroll_handle"])
            fill = colors["primary"] if checked else colors["surface"]
        else:
            border = QColor(colors["border"])
            fill = colors["surface_alt"]
        painter.setPen(QPen(border, 2))
        painter.setBrush(QColor(fill))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)
        if not checked:
            return
        mark = "#FFFFFF" if enabled else colors["text_tertiary"]
        pen = QPen(QColor(mark), 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        left = rect.left()
        top = rect.top()
        painter.drawLine(left + 5, top + 10, left + 9, top + 14)
        painter.drawLine(left + 9, top + 14, left + 15, top + 6)

    @staticmethod
    def _draw_status(
        painter: QPainter,
        rect: QRect,
        status: str,
        text: str,
        colors,
    ) -> None:
        backgrounds = {
            ProgramStatus.RUNNING.value: colors["primary_soft"],
            ProgramStatus.SUCCESS.value: colors["success_bg"],
            ProgramStatus.ERROR.value: colors["error_bg"],
        }
        foregrounds = {
            ProgramStatus.RUNNING.value: colors["primary"],
            ProgramStatus.SUCCESS.value: colors["success"],
            ProgramStatus.ERROR.value: colors["error"],
        }
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(backgrounds.get(status, colors["primary_soft"])))
        painter.drawRoundedRect(rect, 10, 10)
        font = QFont(painter.font())
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(foregrounds.get(status, colors["primary"])))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def editorEvent(self, event, model, option, index) -> bool:
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            card = self._card_rect(option.rect)
            if self._checkbox_rect(card).contains(event.pos()):
                current = index.data(Qt.ItemDataRole.CheckStateRole)
                if current is None:
                    return False
                target = (
                    Qt.CheckState.Unchecked
                    if current == Qt.CheckState.Checked
                    else Qt.CheckState.Checked
                )
                return model.setData(index, target, Qt.ItemDataRole.CheckStateRole)
        return super().editorEvent(event, model, option, index)


class ProgramListView(QListView):
    uninstall_requested = Signal()
    info_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("programList")
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setUniformItemSizes(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setAccessibleName("Installed programs")
        self.setAccessibleDescription(
            "Use the arrow keys to move, Space to mark a program, Delete to uninstall, and F5 to refresh."
        )

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space:
            self._toggle_current()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Delete:
            self.uninstall_requested.emit()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.info_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _toggle_current(self) -> None:
        index = self.currentIndex()
        if not index.isValid():
            return
        current = index.data(Qt.ItemDataRole.CheckStateRole)
        target = (
            Qt.CheckState.Unchecked
            if current == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        self.model().setData(index, target, Qt.ItemDataRole.CheckStateRole)
