"""
install_window.py — Full-screen install backdrop for Omega GUI Wizard.

Implements the same ``create / update / iscanceled / close`` interface as
``xbmcgui.DialogProgress`` so that ``downloader.py`` and ``extract.py`` need
zero code changes — just pass an ``InstallWindow`` instance where they
currently receive a ``DialogProgress``.

Visual layout (1280 × 720)
--------------------------
┌──────────────────────────────────┐
│  [full-screen fanart background] │
│                                  │
│   ┌──────────────────────────┐   │
│   │  [addon title / logo]    │   │
│   │  [step label     ………]  │   │
│   │  [progress bar   ██░░░░] │   │
│   │  [   pct %    speed/ETA] │   │
│   │  [detail line            │   │
│   └──────────────────────────┘   │
└──────────────────────────────────┘
"""

import os
import xbmc
import xbmcgui

from .. import config


# Screen constants
_W = 1280
_H = 720

# Overlay panel dimensions (centred horizontally, sits in the lower 60 %)
_PAN_W = 900
_PAN_H = 320
_PAN_X = (_W - _PAN_W) // 2      # 190
_PAN_Y = (_H - _PAN_H) // 2 + 60  # ~240

# Control IDs — must not clash with xbmcgui built-ins (0–99 are safe)
_ID_BG       = 100
_ID_PANEL    = 101
_ID_TITLE    = 102
_ID_STEP     = 103
_ID_PROGRESS = 104
_ID_PCT      = 105
_ID_DETAIL   = 106


class InstallWindow(xbmcgui.WindowDialog):
    """Full-screen install backdrop with a centred progress overlay.

    Usage::

        win = InstallWindow()
        win.create('Installing My Build', 'Downloading…')
        # …pass win to downloader / extract as the progress callback…
        win.close()

    The ``update(percent, line1, line2='')`` / ``iscanceled()`` / ``close()``
    interface is intentionally identical to ``xbmcgui.DialogProgress``.
    """

    def __init__(self):
        super().__init__()
        self._cancelled = False
        self._cancel_locked = False
        self._built = False

    # ------------------------------------------------------------------
    # DialogProgress-compatible API
    # ------------------------------------------------------------------
    def create(self, heading: str, message: str = '') -> None:
        """Build controls, show the window, and set the initial heading."""
        if not self._built:
            self._build_controls()
            self._built = True
        self._set_label(_ID_STEP, heading)
        self._set_label(_ID_DETAIL, message)
        self._set_label(_ID_PCT, '0%')
        self._set_progress(0)
        self._cancelled = False
        self.show()

    def update(self, percent: int, line1: str = '', line2: str = '') -> None:
        """Update progress.  percent=0–100; line1 = step; line2 = detail."""
        pct = max(0, min(100, percent))
        if line1:
            self._set_label(_ID_STEP, line1)
        self._set_label(_ID_PCT, '%d%%' % pct)
        self._set_progress(pct)
        if line2:
            self._set_label(_ID_DETAIL, line2)

    def iscanceled(self) -> bool:
        """Return True if the user pressed Back/Cancel."""
        return self._cancelled and not self._cancel_locked

    def close(self) -> None:
        """Hide and destroy the window."""
        super().close()

    # ------------------------------------------------------------------
    # Extra methods beyond the DialogProgress interface
    # ------------------------------------------------------------------
    def lock_cancel(self) -> None:
        """Prevent user cancellation (use during ZIP extraction)."""
        self._cancel_locked = True
        self._set_label(_ID_DETAIL, 'Extracting — please wait…')

    def unlock_cancel(self) -> None:
        """Re-allow user cancellation."""
        self._cancel_locked = False

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------
    def onAction(self, action) -> None:
        action_id = action.getId()
        if action_id in (
            xbmcgui.ACTION_NAV_BACK,
            xbmcgui.ACTION_PREVIOUS_MENU,
            xbmcgui.ACTION_STOP,
        ):
            if not self._cancel_locked:
                self._cancelled = True

    # ------------------------------------------------------------------
    # Control construction
    # ------------------------------------------------------------------
    def _build_controls(self) -> None:
        # 1. Full-screen fanart background
        bg_img = config.FANART if os.path.exists(config.FANART) else ''
        bg = xbmcgui.ControlImage(0, 0, _W, _H, bg_img)
        self.addControl(bg)

        # 2. Dark semi-transparent overlay panel
        panel_img = os.path.join(config.ART, 'LoadingPanel.png')
        if not os.path.exists(panel_img):
            panel_img = ''
        panel = xbmcgui.ControlImage(_PAN_X, _PAN_Y, _PAN_W, _PAN_H, panel_img)
        self.addControl(panel)

        # 3. Addon title (top of panel)
        title_lbl = xbmcgui.ControlLabel(
            _PAN_X + 20, _PAN_Y + 16, _PAN_W - 40, 40,
            config.ADDONTITLE,
            font='Font13', textColor='0xFFFFFFFF',
            alignment=0x00000006,  # centre
        )
        self.addControl(title_lbl)

        # 4. Step label
        step_lbl = xbmcgui.ControlLabel(
            _PAN_X + 20, _PAN_Y + 70, _PAN_W - 40, 36,
            '',
            font='Font12', textColor='0xFFDDDDDD',
        )
        self.addControl(step_lbl)
        self._step_ctrl = step_lbl

        # 5. Progress bar track + fill
        bar_x = _PAN_X + 20
        bar_y = _PAN_Y + 120
        bar_w = _PAN_W - 40
        bar_h = 24

        # Track (grey background)
        track_img = os.path.join(config.ART, 'ProgressBarTrack.png')
        if not os.path.exists(track_img):
            track_img = ''
        track = xbmcgui.ControlImage(bar_x, bar_y, bar_w, bar_h, track_img)
        self.addControl(track)

        # Fill (progress indicator)
        fill_img = os.path.join(config.ART, 'ProgressBar.png')
        if not os.path.exists(fill_img):
            fill_img = ''
        self._fill = xbmcgui.ControlImage(bar_x, bar_y, 0, bar_h, fill_img)
        self.addControl(self._fill)
        self._bar_x = bar_x
        self._bar_max_w = bar_w

        # 6. Percentage label
        pct_lbl = xbmcgui.ControlLabel(
            bar_x, bar_y + bar_h + 6, 120, 30,
            '0%',
            font='Font12', textColor='0xFFFFFFFF',
        )
        self.addControl(pct_lbl)
        self._pct_ctrl = pct_lbl

        # 7. Detail / speed-ETA label
        detail_lbl = xbmcgui.ControlLabel(
            bar_x + 130, bar_y + bar_h + 6, bar_w - 130, 30,
            '',
            font='Font12', textColor='0xFFAAAAAA',
        )
        self.addControl(detail_lbl)
        self._detail_ctrl = detail_lbl

    # ------------------------------------------------------------------
    # Control helpers
    # ------------------------------------------------------------------
    def _set_label(self, ctrl_id_or_ctrl, text: str) -> None:
        if isinstance(ctrl_id_or_ctrl, xbmcgui.ControlLabel):
            ctrl = ctrl_id_or_ctrl
        else:
            ctrl = self.getControl(ctrl_id_or_ctrl) if False else None
            # Use stored references — avoids getControl() overhead
            ctrl = {
                _ID_STEP:   getattr(self, '_step_ctrl',   None),
                _ID_PCT:    getattr(self, '_pct_ctrl',    None),
                _ID_DETAIL: getattr(self, '_detail_ctrl', None),
            }.get(ctrl_id_or_ctrl)

        if ctrl is not None:
            ctrl.setLabel(str(text))

    def _set_progress(self, pct: int) -> None:
        if hasattr(self, '_fill'):
            w = int(self._bar_max_w * pct / 100)
            self._fill.setWidth(w)
