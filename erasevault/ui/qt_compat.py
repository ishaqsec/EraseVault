"""
PySide6 import layer with headless test-harness fallback for CI environments
where a display server or PySide6 binary wheel is not installed.
On Windows/Desktop with PySide6 installed, all classes resolve directly to native PySide6.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

try:
    from PySide6.QtCore import (
        QEvent,
        QMimeData,
        QObject,
        QPoint,
        QRect,
        QRectF,
        QSize,
        Qt,
        QThread,
        QTimer,
        QUrl,
        Signal,
        Slot,
    )
    from PySide6.QtGui import (
        QAction,
        QBrush,
        QColor,
        QCursor,
        QDragEnterEvent,
        QDropEvent,
        QFont,
        QFontDatabase,
        QGuiApplication,
        QIcon,
        QLinearGradient,
        QMouseEvent,
        QPainter,
        QPainterPath,
        QPalette,
        QPen,
        QPixmap,
        QRegion,
        QResizeEvent,
        QScreen,
    )
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizeGrip,
        QSizePolicy,
        QSpacerItem,
        QSpinBox,
        QStackedWidget,
        QStyledItemDelegate,
        QTableWidget,
        QTableWidgetItem,
        QTextBrowser,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    HAS_PYSIDE6 = True

except ImportError:
    HAS_PYSIDE6 = False

    class _BoundSignal:
        def __init__(self) -> None:
            self._slots: List[Callable[..., Any]] = []

        def connect(self, slot: Callable[..., Any]) -> None:
            if slot not in self._slots:
                self._slots.append(slot)

        def disconnect(self, slot: Optional[Callable[..., Any]] = None) -> None:
            if slot is None:
                self._slots.clear()
            elif slot in self._slots:
                self._slots.remove(slot)

        def emit(self, *args: Any, **kwargs: Any) -> None:
            import inspect
            for s in list(self._slots):
                try:
                    sig = inspect.signature(s)
                    params = [
                        p for p in sig.parameters.values()
                        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
                    ]
                    has_varargs = any(p.kind == p.VAR_POSITIONAL for p in sig.parameters.values())
                    if has_varargs:
                        s(*args, **kwargs)
                    else:
                        s(*args[:len(params)], **kwargs)
                except Exception:
                    s(*args, **kwargs)

    class Signal:  # type: ignore[no-redef]
        def __init__(self, *types: Any) -> None:
            self._types = types
            self._name = ""

        def __set_name__(self, owner: Any, name: str) -> None:
            self._name = f"_sig_{name}"

        def __get__(self, instance: Any, owner: Any = None) -> Any:
            if instance is None:
                return self
            sig = getattr(instance, self._name, None)
            if sig is None:
                sig = _BoundSignal()
                setattr(instance, self._name, sig)
            return sig

    def Slot(*types: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:  # type: ignore[no-redef]
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn
        return decorator

    class Qt:  # type: ignore[no-redef]
        class WindowType:
            FramelessWindowHint = 0x00000800
            Window = 0x00000001
            Dialog = 0x00000002
            WindowSystemMenuHint = 0x00002000
            WindowMinimizeButtonHint = 0x00004000
            WindowMaximizeButtonHint = 0x00008000
            WindowMinMaxButtonsHint = 0x0000C000
            WindowCloseButtonHint = 0x08000000
            CustomizeWindowHint = 0x02000000

        FramelessWindowHint = WindowType.FramelessWindowHint
        Window = WindowType.Window
        Dialog = WindowType.Dialog
        WindowSystemMenuHint = WindowType.WindowSystemMenuHint
        WindowMinimizeButtonHint = WindowType.WindowMinimizeButtonHint
        WindowMaximizeButtonHint = WindowType.WindowMaximizeButtonHint
        WindowMinMaxButtonsHint = WindowType.WindowMinMaxButtonsHint
        WindowCloseButtonHint = WindowType.WindowCloseButtonHint
        CustomizeWindowHint = WindowType.CustomizeWindowHint

        class WidgetAttribute:
            WA_TranslucentBackground = 120
            WA_StyledBackground = 93
            WA_TransparentForMouseEvents = 51

        WA_TranslucentBackground = WidgetAttribute.WA_TranslucentBackground
        WA_StyledBackground = WidgetAttribute.WA_StyledBackground
        WA_TransparentForMouseEvents = WidgetAttribute.WA_TransparentForMouseEvents

        class AlignmentFlag:
            AlignLeft = 0x0001
            AlignRight = 0x0002
            AlignHCenter = 0x0004
            AlignTop = 0x0020
            AlignBottom = 0x0040
            AlignVCenter = 0x0080
            AlignCenter = AlignHCenter | AlignVCenter

        AlignLeft = AlignmentFlag.AlignLeft
        AlignRight = AlignmentFlag.AlignRight
        AlignHCenter = AlignmentFlag.AlignHCenter
        AlignTop = AlignmentFlag.AlignTop
        AlignBottom = AlignmentFlag.AlignBottom
        AlignVCenter = AlignmentFlag.AlignVCenter
        AlignCenter = AlignmentFlag.AlignCenter

        class CursorShape:
            PointingHandCursor = 13
            ArrowCursor = 0
            SizeVerCursor = 5
            SizeHorCursor = 6
            SizeBDiagCursor = 7
            SizeFDiagCursor = 8

        PointingHandCursor = CursorShape.PointingHandCursor
        ArrowCursor = CursorShape.ArrowCursor
        SizeVerCursor = CursorShape.SizeVerCursor
        SizeHorCursor = CursorShape.SizeHorCursor
        SizeBDiagCursor = CursorShape.SizeBDiagCursor
        SizeFDiagCursor = CursorShape.SizeFDiagCursor

        class AspectRatioMode:
            KeepAspectRatio = 1
            IgnoreAspectRatio = 0
            KeepAspectRatioByExpanding = 2

        KeepAspectRatio = AspectRatioMode.KeepAspectRatio
        IgnoreAspectRatio = AspectRatioMode.IgnoreAspectRatio

        class TransformationMode:
            SmoothTransformation = 1

        SmoothTransformation = TransformationMode.SmoothTransformation

        class MouseButton:
            LeftButton = 1
            RightButton = 2
            NoButton = 0

        LeftButton = MouseButton.LeftButton
        RightButton = MouseButton.RightButton
        NoButton = MouseButton.NoButton

        class PenStyle:
            NoPen = 0
            SolidLine = 1
            DashLine = 2

        NoPen = PenStyle.NoPen
        SolidLine = PenStyle.SolidLine
        DashLine = PenStyle.DashLine

        class ItemDataRole:
            UserRole = 0x0100
            DisplayRole = 0

        UserRole = ItemDataRole.UserRole
        DisplayRole = ItemDataRole.DisplayRole

        class ItemFlag:
            ItemIsEnabled = 32
            ItemIsSelectable = 1

        ItemIsEnabled = ItemFlag.ItemIsEnabled
        ItemIsSelectable = ItemFlag.ItemIsSelectable

    class QPoint:  # type: ignore[no-redef]
        def __init__(self, x: int = 0, y: int = 0) -> None:
            self._x = int(x)
            self._y = int(y)
        def x(self) -> int: return self._x
        def y(self) -> int: return self._y
        def __sub__(self, other: "QPoint") -> "QPoint":
            return QPoint(self._x - other._x, self._y - other._y)
        def __add__(self, other: "QPoint") -> "QPoint":
            return QPoint(self._x + other._x, self._y + other._y)

    class QSize:  # type: ignore[no-redef]
        def __init__(self, w: int = 0, h: int = 0) -> None:
            self._w = int(w)
            self._h = int(h)
        def width(self) -> int: return self._w
        def height(self) -> int: return self._h

    class QRect:  # type: ignore[no-redef]
        def __init__(self, x: int = 0, y: int = 0, w: int = 0, h: int = 0) -> None:
            self._x, self._y, self._w, self._h = int(x), int(y), int(w), int(h)
        def x(self) -> int: return self._x
        def y(self) -> int: return self._y
        def width(self) -> int: return self._w
        def height(self) -> int: return self._h
        def left(self) -> int: return self._x
        def top(self) -> int: return self._y
        def right(self) -> int: return self._x + self._w
        def bottom(self) -> int: return self._y + self._h
        def topLeft(self) -> QPoint: return QPoint(self._x, self._y)
        def center(self) -> QPoint: return QPoint(self._x + self._w // 2, self._y + self._h // 2)
        def adjusted(self, dx1: int, dy1: int, dx2: int, dy2: int) -> "QRect":
            return QRect(self._x + dx1, self._y + dy1, self._w - dx1 + dx2, self._h - dy1 + dy2)

    class QRectF(QRect):  # type: ignore[no-redef]
        pass

    class QUrl:  # type: ignore[no-redef]
        def __init__(self, url: str = "") -> None:
            self._url = url
        @staticmethod
        def fromLocalFile(path: str) -> "QUrl":
            return QUrl(path)
        def toLocalFile(self) -> str:
            return self._url.replace("file://", "")
        def isLocalFile(self) -> bool:
            return True

    class QObject:  # type: ignore[no-redef]
        def __init__(self, parent: Optional[Any] = None) -> None:
            self._parent = parent
            self._object_name = ""
            self._properties: dict = {}
        def setObjectName(self, name: str) -> None:
            self._object_name = name
        def objectName(self) -> str:
            return self._object_name
        def setProperty(self, k: str, v: Any) -> None:
            self._properties[k] = v
        def property(self, k: str) -> Any:
            return self._properties.get(k)

    class QStyledItemDelegate(QObject):  # type: ignore[no-redef]
        pass

    class QThread(QObject):  # type: ignore[no-redef]
        started = Signal()
        finished = Signal()
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._running = False
        def start(self) -> None:
            self._running = True
            self.started.emit()
            self.run()
            self._running = False
            self.finished.emit()
        def run(self) -> None:
            pass
        def isRunning(self) -> bool:
            return self._running
        def wait(self, msecs: int = 0) -> bool:
            return True

    class QTimer(QObject):  # type: ignore[no-redef]
        timeout = Signal()
        @staticmethod
        def singleShot(msec: int, callback: Callable[[], None]) -> None:
            callback()

    class QColor:  # type: ignore[no-redef]
        def __init__(self, *args: Any) -> None:
            self.args = args

    class QPalette:  # type: ignore[no-redef]
        class ColorRole:
            Window = 10
            WindowText = 0
            Base = 9
            AlternateBase = 16
            ToolTipBase = 18
            ToolTipText = 19
            Text = 6
            Button = 1
            ButtonText = 8
            BrightText = 7
            Highlight = 12
            HighlightedText = 13
        Window = ColorRole.Window
        WindowText = ColorRole.WindowText
        Base = ColorRole.Base
        AlternateBase = ColorRole.AlternateBase
        ToolTipBase = ColorRole.ToolTipBase
        ToolTipText = ColorRole.ToolTipText
        Text = ColorRole.Text
        Button = ColorRole.Button
        ButtonText = ColorRole.ButtonText
        BrightText = ColorRole.BrightText
        Highlight = ColorRole.Highlight
        HighlightedText = ColorRole.HighlightedText
        def setColor(self, *args: Any) -> None: pass

    class QFont:  # type: ignore[no-redef]
        class Weight:
            Normal = 400
            Medium = 500
            DemiBold = 600
            Bold = 700
            ExtraBold = 800
        Bold = Weight.Bold
        DemiBold = Weight.DemiBold
        Normal = Weight.Normal
        def __init__(self, family: str = "Segoe UI", size: int = 10, weight: int = 400) -> None:
            self.family = family
            self.size = size
            self.weight = weight
        def setBold(self, b: bool) -> None: pass
        def setPixelSize(self, s: int) -> None: self.size = s
        def setPointSize(self, s: int) -> None: self.size = s
        def setWeight(self, w: Any) -> None: self.weight = w

    class QPixmap:  # type: ignore[no-redef]
        def __init__(self, path: str = "") -> None:
            self.path = path
            self._w = 64
            self._h = 64
        def isNull(self) -> bool:
            import os
            return not (self.path and os.path.exists(self.path))
        def scaled(self, *args: Any, **kwargs: Any) -> "QPixmap":
            cp = QPixmap(self.path)
            if args and isinstance(args[0], QSize):
                cp._w, cp._h = args[0].width(), args[0].height()
            elif len(args) >= 2 and isinstance(args[0], int):
                cp._w, cp._h = args[0], args[1]
            return cp
        def width(self) -> int: return self._w
        def height(self) -> int: return self._h

    class QIcon:  # type: ignore[no-redef]
        def __init__(self, pixmap_or_path: Any = None) -> None:
            self.source = pixmap_or_path
        def isNull(self) -> bool:
            return self.source is None

    class QPainter:  # type: ignore[no-redef]
        class RenderHint:
            Antialiasing = 1
            SmoothPixmapTransform = 2
        Antialiasing = RenderHint.Antialiasing
        SmoothPixmapTransform = RenderHint.SmoothPixmapTransform
        def __init__(self, *args: Any) -> None: pass
        def setRenderHint(self, *args: Any) -> None: pass
        def setPen(self, *args: Any) -> None: pass
        def setBrush(self, *args: Any) -> None: pass
        def drawRoundedRect(self, *args: Any) -> None: pass
        def drawPixmap(self, *args: Any) -> None: pass
        def end(self) -> None: pass

    class QPen:  # type: ignore[no-redef]
        def __init__(self, *args: Any) -> None: pass
        def setWidth(self, w: int) -> None: pass
        def setStyle(self, s: Any) -> None: pass

    class QBrush:  # type: ignore[no-redef]
        def __init__(self, *args: Any) -> None: pass

    class QPainterPath:  # type: ignore[no-redef]
        def addRoundedRect(self, *args: Any) -> None: pass
        def toFillPolygon(self) -> Any: return None

    class QRegion:  # type: ignore[no-redef]
        def __init__(self, *args: Any) -> None: pass

    class QLinearGradient:  # type: ignore[no-redef]
        def __init__(self, *args: Any) -> None: pass
        def setColorAt(self, *args: Any) -> None: pass

    class QCursor:  # type: ignore[no-redef]
        @staticmethod
        def pos() -> QPoint:
            return QPoint(500, 500)

    class QEvent:  # type: ignore[no-redef]
        pass

    class QMouseEvent(QEvent):  # type: ignore[no-redef]
        pass

    class QResizeEvent(QEvent):  # type: ignore[no-redef]
        def __init__(self, size: QSize, old_size: Optional[QSize] = None) -> None:
            self._size = size
            self._old = old_size or size
        def size(self) -> QSize: return self._size
        def oldSize(self) -> QSize: return self._old

    class QDragEnterEvent(QEvent):  # type: ignore[no-redef]
        pass

    class QDropEvent(QEvent):  # type: ignore[no-redef]
        pass

    class QMimeData:  # type: ignore[no-redef]
        pass

    class QScreen:  # type: ignore[no-redef]
        def __init__(self, w: int = 1920, h: int = 1080, avail_h: Optional[int] = None) -> None:
            self._geom = QRect(0, 0, w, h)
            self._avail = QRect(0, 0, w, avail_h if avail_h is not None else (h - 40))
        def geometry(self) -> QRect:
            return self._geom
        def availableGeometry(self) -> QRect:
            return self._avail

    class QGuiApplication:  # type: ignore[no-redef]
        _screen: QScreen = QScreen(1920, 1080, 1040)
        @classmethod
        def primaryScreen(cls) -> QScreen:
            return cls._screen
        @classmethod
        def screenAt(cls, pos: QPoint) -> QScreen:
            return cls._screen

    class QFontDatabase:  # type: ignore[no-redef]
        @staticmethod
        def addApplicationFont(path: str) -> int:
            return 0

    class QAction(QObject):  # type: ignore[no-redef]
        triggered = Signal()
        def __init__(self, text: str = "", parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._text = text
        def text(self) -> str: return self._text

    class QWidget(QObject):  # type: ignore[no-redef]
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._geometry = QRect(0, 0, 100, 100)
            self._min_size = QSize(0, 0)
            self._max_size = QSize(16777215, 16777215)
            self._visible = True
            self._enabled = True
            self._maximized = False
            self._window_flags = 0
            self._style_sheet = ""
            self._tooltip = ""
            self._accept_drops = False
            self._layout: Optional[Any] = None
            self._children: List[Any] = []
            self._mask: Optional[Any] = None
            if parent is not None and hasattr(parent, "_children"):
                parent._children.append(self)

        def setGeometry(self, *args: Any) -> None:
            if len(args) == 1 and isinstance(args[0], QRect):
                r = args[0]
                old_sz = QSize(self._geometry.width(), self._geometry.height())
                self._geometry = QRect(r.x(), r.y(), r.width(), r.height())
            else:
                x, y, w, h = args[:4]
                old_sz = QSize(self._geometry.width(), self._geometry.height())
                self._geometry = QRect(int(x), int(y), int(w), int(h))
            new_sz = QSize(self._geometry.width(), self._geometry.height())
            if (old_sz.width() != new_sz.width() or old_sz.height() != new_sz.height()) and hasattr(self, "resizeEvent"):
                self.resizeEvent(QResizeEvent(new_sz, old_sz))

        def geometry(self) -> QRect: return self._geometry
        def frameGeometry(self) -> QRect: return self._geometry
        def rect(self) -> QRect: return QRect(0, 0, self._geometry.width(), self._geometry.height())
        def x(self) -> int: return self._geometry.x()
        def y(self) -> int: return self._geometry.y()
        def width(self) -> int: return self._geometry.width()
        def height(self) -> int: return self._geometry.height()
        def size(self) -> QSize: return QSize(self._geometry.width(), self._geometry.height())
        def setFixedSize(self, w: Any, h: Optional[int] = None) -> None:
            if isinstance(w, QSize):
                nw, nh = w.width(), w.height()
            else:
                nw, nh = int(w), int(h if h is not None else w)
            self._min_size = QSize(nw, nh)
            self._max_size = QSize(nw, nh)
            self.resize(nw, nh)
        def setFixedWidth(self, w: int) -> None:
            self.setGeometry(self._geometry.x(), self._geometry.y(), int(w), self._geometry.height())
        def setFixedHeight(self, h: int) -> None:
            self.setGeometry(self._geometry.x(), self._geometry.y(), self._geometry.width(), int(h))
        def setMinimumSize(self, w: int, h: int) -> None:
            self._min_size = QSize(int(w), int(h))
        def minimumWidth(self) -> int: return self._min_size.width()
        def minimumHeight(self) -> int: return self._min_size.height()
        def setMaximumSize(self, w: int, h: int) -> None:
            self._max_size = QSize(int(w), int(h))
        def setMinimumWidth(self, w: int) -> None:
            self._min_size = QSize(int(w), self._min_size.height())
        def setMinimumHeight(self, h: int) -> None:
            self._min_size = QSize(self._min_size.width(), int(h))
        def resize(self, w: Any, h: Optional[int] = None) -> None:
            if isinstance(w, QSize):
                nw, nh = w.width(), w.height()
            else:
                nw, nh = int(w), int(h if h is not None else w)
            self.setGeometry(self._geometry.x(), self._geometry.y(), nw, nh)
        def move(self, x: Any, y: Optional[int] = None) -> None:
            if isinstance(x, QPoint):
                nx, ny = x.x(), x.y()
            else:
                nx, ny = int(x), int(y or 0)
            self._geometry = QRect(nx, ny, self._geometry.width(), self._geometry.height())
        def setStyleSheet(self, ss: str) -> None: self._style_sheet = ss
        def styleSheet(self) -> str: return self._style_sheet
        def setToolTip(self, t: str) -> None: self._tooltip = t
        def toolTip(self) -> str: return self._tooltip
        def setCursor(self, c: Any) -> None: pass
        def unsetCursor(self) -> None: pass
        def setMouseTracking(self, on: bool) -> None: pass
        def setAttribute(self, attr: Any, on: bool = True) -> None: pass
        def setWindowFlags(self, flags: Any) -> None: self._window_flags = int(flags)
        def windowFlags(self) -> int: return self._window_flags
        def setWindowTitle(self, title: str) -> None: self._window_title = title
        def windowTitle(self) -> str: return getattr(self, "_window_title", "")
        def setWindowIcon(self, icon: Any) -> None: pass
        def setAcceptDrops(self, on: bool) -> None: self._accept_drops = on
        def acceptDrops(self) -> bool: return self._accept_drops
        def setMask(self, mask: Any) -> None: self._mask = mask
        def clearMask(self) -> None: self._mask = None
        def setVisible(self, v: bool) -> None: self._visible = v
        def isVisible(self) -> bool: return self._visible
        def show(self) -> None: self._visible = True
        def hide(self) -> None: self._visible = False
        def close(self) -> bool:
            self._visible = False
            return True
        def showMinimized(self) -> None: pass
        def showMaximized(self) -> None:
            self._maximized = True
            scr = QApplication.primaryScreen().availableGeometry()
            self.setGeometry(scr.x(), scr.y(), scr.width(), scr.height())
        def showNormal(self) -> None:
            self._maximized = False
        def isMaximized(self) -> bool: return self._maximized
        def window(self) -> "QWidget":
            curr: Any = self
            while getattr(curr, "_parent", None) is not None:
                curr = curr._parent
            return curr
        def setEnabled(self, e: bool) -> None: self._enabled = e
        def isEnabled(self) -> bool: return self._enabled
        def update(self) -> None: pass
        def repaint(self) -> None: pass
        def setLayout(self, layout: Any) -> None: self._layout = layout
        def layout(self) -> Any: return self._layout
        def setSizePolicy(self, *args: Any) -> None: pass
        def setContentsMargins(self, *args: Any) -> None: pass

    class QFrame(QWidget):  # type: ignore[no-redef]
        class Shape:
            NoFrame = 0
            StyledPanel = 6
        NoFrame = Shape.NoFrame
        StyledPanel = Shape.StyledPanel
        def setFrameShape(self, s: Any) -> None: pass

    class QMainWindow(QWidget):  # type: ignore[no-redef]
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._central: Optional[QWidget] = None
        def setCentralWidget(self, w: QWidget) -> None:
            self._central = w
        def centralWidget(self) -> Optional[QWidget]:
            return self._central

    class QLabel(QFrame):  # type: ignore[no-redef]
        def __init__(self, text: Any = "", parent: Optional[Any] = None) -> None:
            if isinstance(text, QWidget) and parent is None:
                parent = text
                text = ""
            super().__init__(parent)
            self._text = str(text)
            self._pixmap: Optional[QPixmap] = None
        def setText(self, t: str) -> None: self._text = str(t)
        def text(self) -> str: return self._text
        def setPixmap(self, p: QPixmap) -> None: self._pixmap = p
        def pixmap(self) -> Optional[QPixmap]: return self._pixmap
        def setAlignment(self, a: Any) -> None: pass
        def setWordWrap(self, w: bool) -> None: pass
        def setFont(self, f: QFont) -> None: pass
        def setScaledContents(self, s: bool) -> None: pass
        def setOpenExternalLinks(self, o: bool) -> None: pass

    class QPushButton(QWidget):  # type: ignore[no-redef]
        clicked = Signal(bool)
        def __init__(self, text: Any = "", parent: Optional[Any] = None) -> None:
            if isinstance(text, QWidget) and parent is None:
                parent = text
                text = ""
            super().__init__(parent)
            self._text = str(text)
            self._icon: Optional[QIcon] = None
            self._icon_size = QSize(24, 24)
            self._checkable = False
            self._checked = False
        def setText(self, t: str) -> None: self._text = str(t)
        def text(self) -> str: return self._text
        def setIcon(self, icon: QIcon) -> None: self._icon = icon
        def icon(self) -> Optional[QIcon]: return self._icon
        def setIconSize(self, sz: QSize) -> None: self._icon_size = sz
        def iconSize(self) -> QSize: return self._icon_size
        def setCheckable(self, c: bool) -> None: self._checkable = c
        def setChecked(self, c: bool) -> None: self._checked = c
        def isChecked(self) -> bool: return self._checked
        def setFlat(self, f: bool) -> None: pass
        def setFont(self, f: QFont) -> None: pass
        def click(self) -> None:
            if not self._enabled:
                return
            if self._checkable:
                self._checked = not self._checked
            self.clicked.emit(self._checked)

    class QComboBox(QWidget):  # type: ignore[no-redef]
        currentIndexChanged = Signal(int)
        currentTextChanged = Signal(str)
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._items: List[Tuple[str, Any]] = []
            self._idx = -1
        def addItem(self, *args: Any) -> None:
            if len(args) == 1:
                text, user_data = str(args[0]), None
            elif isinstance(args[0], QIcon):
                text = str(args[1])
                user_data = args[2] if len(args) > 2 else None
            else:
                text, user_data = str(args[0]), args[1]
            self._items.append((text, user_data))
            if self._idx == -1:
                self._idx = 0
        def clear(self) -> None:
            self._items.clear()
            self._idx = -1
        def count(self) -> int:
            return len(self._items)
        def currentIndex(self) -> int:
            return self._idx
        def setCurrentIndex(self, idx: int) -> None:
            if 0 <= idx < len(self._items) and idx != self._idx:
                self._idx = idx
                self.currentIndexChanged.emit(idx)
                self.currentTextChanged.emit(self._items[idx][0])
            elif 0 <= idx < len(self._items):
                self._idx = idx
        def currentText(self) -> str:
            if 0 <= self._idx < len(self._items):
                return self._items[self._idx][0]
            return ""
        def currentData(self, role: int = 0) -> Any:
            if 0 <= self._idx < len(self._items):
                return self._items[self._idx][1]
            return None
        def itemData(self, idx: int, role: int = 0) -> Any:
            if 0 <= idx < len(self._items):
                return self._items[idx][1]
            return None
        def findData(self, data: Any) -> int:
            for i, (_, d) in enumerate(self._items):
                if d == data:
                    return i
            return -1
        def setIconSize(self, sz: QSize) -> None: pass
        def setItemIcon(self, idx: int, icon: QIcon) -> None: pass
        def setItemText(self, idx: int, text: str) -> None:
            if 0 <= idx < len(self._items):
                self._items[idx] = (str(text), self._items[idx][1])
        def itemText(self, idx: int) -> str:
            if 0 <= idx < len(self._items):
                return self._items[idx][0]
            return ""
        def setItemDelegate(self, delegate: Any) -> None: pass

    class QCheckBox(QPushButton):  # type: ignore[no-redef]
        stateChanged = Signal(int)
        toggled = Signal(bool)
        def __init__(self, text: Any = "", parent: Optional[Any] = None) -> None:
            super().__init__(text, parent)
            self._checkable = True
        def setChecked(self, c: bool) -> None:
            changed = (self._checked != c)
            self._checked = c
            if changed:
                self.toggled.emit(c)
                self.stateChanged.emit(2 if c else 0)

    class QSpinBox(QWidget):  # type: ignore[no-redef]
        valueChanged = Signal(int)
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._val = 0
            self._min = 0
            self._max = 999999
            self._suffix = ""
        def setRange(self, mn: int, mx: int) -> None:
            self._min, self._max = mn, mx
        def setMinimum(self, mn: int) -> None: self._min = mn
        def setMaximum(self, mx: int) -> None: self._max = mx
        def setValue(self, v: int) -> None:
            v = max(self._min, min(self._max, v))
            self._val = v
            self.valueChanged.emit(v)
        def value(self) -> int: return self._val
        def setSuffix(self, s: str) -> None: self._suffix = s

    class QLineEdit(QWidget):  # type: ignore[no-redef]
        textChanged = Signal(str)
        def __init__(self, text: Any = "", parent: Optional[Any] = None) -> None:
            if isinstance(text, QWidget) and parent is None:
                parent = text
                text = ""
            super().__init__(parent)
            self._text = str(text)
            self._placeholder = ""
        def setText(self, t: str) -> None:
            self._text = str(t)
            self.textChanged.emit(self._text)
        def text(self) -> str: return self._text
        def setPlaceholderText(self, p: str) -> None: self._placeholder = p
        def setReadOnly(self, r: bool) -> None: pass

    class QTextEdit(QWidget):  # type: ignore[no-redef]
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._text = ""
        def setPlainText(self, t: str) -> None: self._text = t
        def toPlainText(self) -> str: return self._text
        def setHtml(self, h: str) -> None: self._text = h
        def setReadOnly(self, r: bool) -> None: pass

    class QTextBrowser(QTextEdit):  # type: ignore[no-redef]
        def setOpenExternalLinks(self, b: bool) -> None: pass

    class QProgressBar(QWidget):  # type: ignore[no-redef]
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._val = 0
            self._min = 0
            self._max = 100
        def setRange(self, mn: int, mx: int) -> None: self._min, self._max = mn, mx
        def setValue(self, v: int) -> None: self._val = v
        def value(self) -> int: return self._val
        def setFormat(self, f: str) -> None: pass
        def setTextVisible(self, v: bool) -> None: self._text_vis = bool(v)
        def isTextVisible(self) -> bool: return getattr(self, "_text_vis", True)
        def setAlignment(self, a: Any) -> None: pass

    class QStackedWidget(QWidget):  # type: ignore[no-redef]
        currentChanged = Signal(int)
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._pages: List[QWidget] = []
            self._curr = 0
        def addWidget(self, w: QWidget) -> int:
            self._pages.append(w)
            return len(self._pages) - 1
        def setCurrentIndex(self, idx: int) -> None:
            if 0 <= idx < len(self._pages):
                self._curr = idx
                self.currentChanged.emit(idx)
        def setCurrentWidget(self, w: QWidget) -> None:
            if w in self._pages:
                self.setCurrentIndex(self._pages.index(w))
        def currentIndex(self) -> int: return self._curr
        def currentWidget(self) -> Optional[QWidget]:
            return self._pages[self._curr] if self._pages else None
        def count(self) -> int: return len(self._pages)
        def widget(self, idx: int) -> QWidget: return self._pages[idx]

    class QTableWidgetItem:  # type: ignore[no-redef]
        def __init__(self, text: str = "") -> None:
            self._text = str(text)
            self._data: dict = {}
        def text(self) -> str: return self._text
        def setText(self, t: str) -> None: self._text = str(t)
        def setData(self, role: int, val: Any) -> None: self._data[role] = val
        def data(self, role: int) -> Any: return self._data.get(role)
        def setForeground(self, b: Any) -> None: pass
        def setTextAlignment(self, a: Any) -> None: pass
        def setFlags(self, f: Any) -> None: pass
        def setToolTip(self, t: str) -> None: pass

    class QHeaderView:  # type: ignore[no-redef]
        class ResizeMode:
            Stretch = 1
            ResizeToContents = 3
            Fixed = 2
            Interactive = 0
        Stretch = ResizeMode.Stretch
        ResizeToContents = ResizeMode.ResizeToContents
        Fixed = ResizeMode.Fixed
        Interactive = ResizeMode.Interactive
        def setSectionResizeMode(self, *args: Any) -> None: pass
        def setStretchLastSection(self, s: bool) -> None: pass
        def setVisible(self, v: bool) -> None: pass
        def setDefaultSectionSize(self, s: int) -> None: pass

    class QAbstractItemView:  # type: ignore[no-redef]
        class SelectionBehavior:
            SelectRows = 1
        class SelectionMode:
            SingleSelection = 1
            ExtendedSelection = 3
        class EditTrigger:
            NoEditTriggers = 0
        SelectRows = SelectionBehavior.SelectRows
        SingleSelection = SelectionMode.SingleSelection
        ExtendedSelection = SelectionMode.ExtendedSelection
        NoEditTriggers = EditTrigger.NoEditTriggers

    class QTableWidget(QWidget):  # type: ignore[no-redef]
        itemSelectionChanged = Signal()
        cellDoubleClicked = Signal(int, int)
        def __init__(self, rows: int = 0, cols: int = 0, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._rows = rows
            self._cols = cols
            self._cells: dict = {}
            self._cell_widgets: dict = {}
            self._selected_row = -1
        def setColumnCount(self, c: int) -> None: self._cols = c
        def columnCount(self) -> int: return self._cols
        def setRowCount(self, r: int) -> None:
            self._rows = r
            if r == 0:
                self._cells.clear()
                self._cell_widgets.clear()
                self._selected_row = -1
        def rowCount(self) -> int: return self._rows
        def insertRow(self, r: int) -> None:
            self._rows += 1
        def removeRow(self, r: int) -> None:
            if self._rows > 0:
                self._rows -= 1
        def setHorizontalHeaderLabels(self, labels: List[str]) -> None: pass
        def horizontalHeader(self) -> QHeaderView: return QHeaderView()
        def verticalHeader(self) -> QHeaderView: return QHeaderView()
        def setSelectionBehavior(self, b: Any) -> None: pass
        def setSelectionMode(self, m: Any) -> None: pass
        def setEditTriggers(self, e: Any) -> None: pass
        def setAlternatingRowColors(self, a: bool) -> None: pass
        def setShowGrid(self, g: bool) -> None: pass
        def setFocusPolicy(self, p: Any) -> None: pass
        def setItem(self, r: int, c: int, item: QTableWidgetItem) -> None:
            self._cells[(r, c)] = item
        def item(self, r: int, c: int) -> Optional[QTableWidgetItem]:
            return self._cells.get((r, c))
        def setCellWidget(self, r: int, c: int, w: QWidget) -> None:
            self._cell_widgets[(r, c)] = w
        def cellWidget(self, r: int, c: int) -> Optional[QWidget]:
            return self._cell_widgets.get((r, c))
        def selectRow(self, r: int) -> None:
            if 0 <= r < self._rows:
                self._selected_row = r
                self.itemSelectionChanged.emit()
        def currentRow(self) -> int:
            return self._selected_row if self._selected_row >= 0 else (0 if self._rows > 0 else -1)
        def setColumnWidth(self, c: int, w: int) -> None: pass

    class QScrollArea(QFrame):  # type: ignore[no-redef]
        def setWidgetResizable(self, r: bool) -> None: pass
        def setWidget(self, w: QWidget) -> None: self._w = w

    class QSizeGrip(QWidget):  # type: ignore[no-redef]
        pass

    class QSizePolicy:  # type: ignore[no-redef]
        class Policy:
            Expanding = 7
            Fixed = 0
            Minimum = 1
            Preferred = 5
        Expanding = Policy.Expanding
        Fixed = Policy.Fixed
        Minimum = Policy.Minimum
        Preferred = Policy.Preferred
        def __init__(self, *args: Any) -> None: pass

    class QSpacerItem:  # type: ignore[no-redef]
        def __init__(self, *args: Any) -> None: pass

    class _BaseLayout:
        def __init__(self, parent: Optional[QWidget] = None) -> None:
            self._items: List[Any] = []
            if parent is not None:
                parent.setLayout(self)
        def setContentsMargins(self, *args: Any) -> None: pass
        def setSpacing(self, s: int) -> None: pass
        def addWidget(self, w: Any, *args: Any, **kwargs: Any) -> None:
            self._items.append(w)
        def addLayout(self, l: Any, *args: Any) -> None:
            self._items.append(l)
        def addStretch(self, s: int = 0) -> None: pass
        def addSpacing(self, s: int) -> None: pass
        def addItem(self, it: Any) -> None: pass

    class QVBoxLayout(_BaseLayout):  # type: ignore[no-redef]
        pass

    class QHBoxLayout(_BaseLayout):  # type: ignore[no-redef]
        pass

    class QGridLayout(_BaseLayout):  # type: ignore[no-redef]
        def setHorizontalSpacing(self, s: int) -> None: pass
        def setVerticalSpacing(self, s: int) -> None: pass

    class QMenu(QWidget):  # type: ignore[no-redef]
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._actions: List[QAction] = []
        def addAction(self, text: str) -> QAction:
            act = QAction(text, self)
            self._actions.append(act)
            return act
        def exec(self, *args: Any) -> Optional[QAction]:
            return self._actions[0] if self._actions else None

    class QDialog(QWidget):  # type: ignore[no-redef]
        class DialogCode:
            Accepted = 1
            Rejected = 0
        Accepted = DialogCode.Accepted
        Rejected = DialogCode.Rejected
        def __init__(self, parent: Optional[Any] = None) -> None:
            super().__init__(parent)
            self._result = 0
        def accept(self) -> None:
            self._result = self.Accepted
            self.close()
        def reject(self) -> None:
            self._result = self.Rejected
            self.close()
        def exec(self) -> int:
            return self._result
        def setModal(self, m: bool) -> None: pass

    class QFileDialog:  # type: ignore[no-redef]
        _next_files: List[str] = []
        _next_dir: str = ""
        _next_save: str = ""
        @classmethod
        def getOpenFileNames(cls, *args: Any, **kwargs: Any) -> Tuple[List[str], str]:
            return (list(cls._next_files), "All Files (*)")
        @classmethod
        def getOpenFileName(cls, *args: Any, **kwargs: Any) -> Tuple[str, str]:
            return (cls._next_files[0] if cls._next_files else "", "All Files (*)")
        @classmethod
        def getExistingDirectory(cls, *args: Any, **kwargs: Any) -> str:
            return cls._next_dir
        @classmethod
        def getSaveFileName(cls, *args: Any, **kwargs: Any) -> Tuple[str, str]:
            return (cls._next_save, "")

    class QMessageBox:  # type: ignore[no-redef]
        class StandardButton:
            Yes = 16384
            No = 65536
            Ok = 1024
            Cancel = 4194304
        Yes = StandardButton.Yes
        No = StandardButton.No
        Ok = StandardButton.Ok
        Cancel = StandardButton.Cancel
        @staticmethod
        def information(*args: Any, **kwargs: Any) -> int: return 1024
        @staticmethod
        def warning(*args: Any, **kwargs: Any) -> int: return 1024
        @staticmethod
        def critical(*args: Any, **kwargs: Any) -> int: return 1024
        @staticmethod
        def question(*args: Any, **kwargs: Any) -> int: return 16384

    class QInputDialog:  # type: ignore[no-redef]
        @staticmethod
        def getText(*args: Any, **kwargs: Any) -> Tuple[str, bool]:
            return ("CONFIRM", True)

    class QListWidget(QWidget):  # type: ignore[no-redef]
        pass

    class QListWidgetItem:  # type: ignore[no-redef]
        pass

    class QApplication(QGuiApplication):  # type: ignore[no-redef]
        _inst: Optional["QApplication"] = None
        def __init__(self, argv: Optional[List[str]] = None) -> None:
            QApplication._inst = self
        @classmethod
        def instance(cls) -> Optional["QApplication"]:
            return cls._inst
        def setApplicationName(self, name: str) -> None: pass
        def setOrganizationName(self, name: str) -> None: pass
        def setApplicationVersion(self, ver: str) -> None: pass
        def setFont(self, f: QFont) -> None: pass
        def setStyle(self, style: str) -> None: pass
        def setPalette(self, pal: QPalette) -> None: pass
        def setStyleSheet(self, ss: str) -> None: pass
        def exec(self) -> int: return 0
        @staticmethod
        def processEvents() -> None: pass
