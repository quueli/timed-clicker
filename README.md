# timed-clicker

![ci](https://github.com/quueli/timed-clicker/actions/workflows/ci.yml/badge.svg)

windows tool: pick a point on screen, type a time, it clicks that point at that time and exits. made for a friend who needed to be first in a queue that opened at 10:00:00 sharp.

the whole trick is in app/scheduler.py. sleeping until 10:00 with time.sleep lands you 15-50ms late, so it sleeps in coarse chunks and for the last half second spins on perf_counter, then fires with SendInput. on my machine thats within about 1ms.

any number of monitors works (coordinates are in virtual desktop space) and per-monitor dpi is handled by setting dpi awareness before qt starts. the point is picked with a fullscreen crosshair overlay.

## run

    pip install -r requirements.txt
    python main.py

there is a pyinstaller spec if you want a single exe: `pyinstaller timed_clicker.spec`. tests run qt offscreen: `pytest`.

timezone defaults to utc, set TZ in .env (was Europe/Moscow in the original).
