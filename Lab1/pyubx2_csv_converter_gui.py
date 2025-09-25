# pyubx2_csv_converter_gui.py
"""tkinter-based GUI app to convert u‑blox UBX logs to per‑message CSV files.

Dependencies
------------
* **pyubx2** – UBX parser (``pip install pyubx2``)
* Python standard library only for GUI (``tkinter`` is built‑in)

Quick start::

    python pyubx2_csv_converter_gui.py

Features
~~~~~~~~
* Browse for an input ``.ubx`` file and an output directory.
* Runs conversion in a background **thread** so the UI stays responsive.
* **ttk Progressbar** shows real‑time progress to 100 %.
* Generates one ``<MSG>.csv`` per UBX message type (e.g. ``NAV-PVT.csv``).
"""
from __future__ import annotations

import csv
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Tuple

try:
    import pyubx2  # type: ignore
    from pyubx2 import UBXReader, UBXMessage  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "pyubx2 not installed. Run 'pip install pyubx2' and retry."
    ) from exc


def _msg_to_dict(msg: "UBXMessage") -> Dict[str, Any]:
    """Flatten UBXMessage to dict regardless of pyubx2 version."""
    if hasattr(msg, "to_dict"):
        return msg.to_dict()  # type: ignore[attr-defined]
    base = {k: v for k, v in msg.__dict__.items() if not k.startswith("_") and k not in {"payload", "raw"}}
    payload = msg.__dict__.get("payload") if isinstance(msg.__dict__.get("payload"), dict) else {}
    return {**base, **payload}


class ConvertThread(threading.Thread):
    """Background worker thread for UBX→CSV conversion."""

    def __init__(self, ubx_path: Path, out_dir: Path, q: "queue.Queue[tuple]", /):
        super().__init__(daemon=True)
        self._ubx_path = ubx_path
        self._out_dir = out_dir
        self._q = q  # communication queue to GUI

    def run(self) -> None:  # noqa: D401 – imperative mood
        try:
            size_total = self._ubx_path.stat().st_size or 1
            writers: Dict[str, Tuple[csv.DictWriter, Any]] = {}

            with self._ubx_path.open("rb") as stream:
                ubr = UBXReader(stream, protfilter=2, quitonerror=0)
                for raw, parsed in ubr:
                    row = _msg_to_dict(parsed)
                    if not row:
                        continue
                    name = parsed.identity
                    if name not in writers:
                        csv_path = self._out_dir / f"{name}.csv"
                        fh = open(csv_path, "w", newline="", encoding="utf-8")
                        writer: csv.DictWriter = csv.DictWriter(fh, fieldnames=list(row.keys()), extrasaction="ignore")
                        writer.writeheader()
                        writers[name] = (writer, fh)
                    writers[name][0].writerow(row)

                    # progress
                    pct = int(stream.tell() * 100 / size_total)
                    self._q.put(("progress", pct))

            for _, fh in writers.values():
                fh.close()
            self._q.put(("progress", 100))
            self._q.put(("done", str(self._out_dir)))
        except Exception as exc:  # pragma: no cover
            self._q.put(("error", str(exc)))


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PyUBX2 CSV Converter GUI")
        self.geometry("500x130")
        self.resizable(False, False)

        # state vars
        self._worker_q: "queue.Queue[tuple]" = queue.Queue()
        self._worker: ConvertThread | None = None

        self._build_widgets()
        self._poll_queue()  # start polling communication queue

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        pad = {"padx": 6, "pady": 4}

        # Input file row
        frm_in = ttk.Frame(self)
        frm_in.pack(fill="x", **pad)
        ttk.Label(frm_in, text="Input UBX file:").pack(side="left")
        self.entry_in = ttk.Entry(frm_in)
        self.entry_in.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ttk.Button(frm_in, text="Browse…", command=self._choose_ubx).pack(side="left", padx=(6, 0))

        # Output dir row
        frm_out = ttk.Frame(self)
        frm_out.pack(fill="x", **pad)
        ttk.Label(frm_out, text="Output folder:").pack(side="left")
        self.entry_out = ttk.Entry(frm_out)
        self.entry_out.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ttk.Button(frm_out, text="Select…", command=self._choose_out).pack(side="left", padx=(6, 0))

        # Progress bar
        self.progress = ttk.Progressbar(self, length=450, mode="determinate", maximum=100)
        self.progress.pack(fill="x", **pad)

        # Start button
        ttk.Button(self, text="Start", command=self._start).pack(**pad)

    # ------------------------------------------------------------------
    # Dialog helpers
    # ------------------------------------------------------------------
    def _choose_ubx(self) -> None:
        path = filedialog.askopenfilename(title="Select UBX file", filetypes=[("UBX files", "*.ubx"), ("All files", "*.*")])
        if path:
            self.entry_in.delete(0, tk.END)
            self.entry_in.insert(0, path)

    def _choose_out(self) -> None:
        dir_path = filedialog.askdirectory(title="Select output folder")
        if dir_path:
            self.entry_out.delete(0, tk.END)
            self.entry_out.insert(0, dir_path)

    # ------------------------------------------------------------------
    # Conversion control
    # ------------------------------------------------------------------
    def _start(self) -> None:
        ubx_path = Path(self.entry_in.get())
        out_dir = Path(self.entry_out.get())
        if not ubx_path.is_file():
            messagebox.showwarning("Input error", "Please select a valid UBX file.")
            return
        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)

        self.progress["value"] = 0
        self._worker = ConvertThread(ubx_path, out_dir, self._worker_q)
        self._worker.start()
        self._set_widgets_state(tk.DISABLED)

    def _poll_queue(self) -> None:
        try:
            while True:
                msg_type, payload = self._worker_q.get_nowait()
                if msg_type == "progress":
                    self.progress["value"] = payload
                elif msg_type == "done":
                    messagebox.showinfo("Done", f"Conversion completed. CSV files saved in:\n{payload}")
                    self._set_widgets_state(tk.NORMAL)
                elif msg_type == "error":
                    messagebox.showerror("Error", f"An error occurred during conversion:\n{payload}")
                    self._set_widgets_state(tk.NORMAL)
        except queue.Empty:
            pass  # no messages
        self.after(100, self._poll_queue)  # poll again in 100 ms

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def _set_widgets_state(self, state: str) -> None:
        for child in self.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass  # some widgets (frames) don't support state


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

def main() -> None:  # pragma: no cover
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()