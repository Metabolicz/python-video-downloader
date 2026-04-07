import os
import sys
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp


APP_TITLE   = "Video Downloader"
APP_VERSION = "1.0"
DEFAULT_OUT = str(Path.home() / "Downloads")

# ─── Dependency detection ────────────────────────────────────────────────────

# Common install paths to probe when the binary isn't on PATH yet
_FFMPEG_FALLBACKS = [
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    "/usr/local/bin/ffmpeg",
    "/opt/homebrew/bin/ffmpeg",
    "/usr/bin/ffmpeg",
]
_NODE_FALLBACKS = [
    r"C:\Program Files\nodejs\node.exe",
    r"C:\Program Files (x86)\nodejs\node.exe",
    "/usr/local/bin/node",
    "/opt/homebrew/bin/node",
    "/usr/bin/node",
]


def _find_binary(name: str, fallbacks: list[str]) -> str | None:
    """Try shutil.which first, then probe known install paths and WinGet."""
    found = shutil.which(name)
    if found:
        return found
    for path in fallbacks:
        if os.path.isfile(path):
            return path
    # Search inside the WinGet packages directory (winget install ...)
    winget_pkgs = os.path.join(
        os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages"
    )
    exe = name if name.endswith(".exe") else name + ".exe"
    if os.path.isdir(winget_pkgs):
        for root, _dirs, files in os.walk(winget_pkgs):
            if exe in files:
                return os.path.join(root, exe)
    return None


def get_ffmpeg_path() -> str | None:
    """Return the ffmpeg executable path, preferring a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        path = os.path.join(sys._MEIPASS, "ffmpeg")  # type: ignore[attr-defined]
        if os.path.isfile(path):
            return path
        path_exe = path + ".exe"
        if os.path.isfile(path_exe):
            return path_exe
    return _find_binary("ffmpeg", _FFMPEG_FALLBACKS)


def get_nodejs_path() -> str | None:
    """Return the node executable path if Node.js is installed."""
    return _find_binary("node", _NODE_FALLBACKS)


def _build_ydlp_base_opts() -> dict:
    """Return base yt-dlp options shared by every call (ffmpeg + JS runtime)."""
    opts: dict = {}
    ffmpeg = get_ffmpeg_path()
    if ffmpeg:
        opts["ffmpeg_location"] = ffmpeg
    node = get_nodejs_path()
    if node:
        # --js-runtimes is a top-level yt-dlp option (not an extractor arg)
        opts["js_runtimes"] = f"nodejs:{node}"
    return opts


# ─── UI helpers ───────────────────────────────────────────────────────────────

def _row(parent, label: str, row: int):
    """Place a right-aligned label and return the content frame."""
    tk.Label(parent, text=label, anchor="e", width=12).grid(
        row=row, column=0, sticky="e", padx=(16, 6), pady=6
    )
    frame = tk.Frame(parent)
    frame.grid(row=row, column=1, sticky="ew", padx=(0, 16), pady=6)
    return frame


# ─── Main application ─────────────────────────────────────────────────────────

class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.resizable(False, False)
        self._formats: list[dict] = []
        self._busy    = False
        self._build_ui()
        self._center()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(1, weight=1)

        # Header
        header = tk.Frame(self, bg="#1a1a2e", pady=14)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(
            header, text="⬇  Video Downloader",
            bg="#1a1a2e", fg="white",
            font=("Helvetica", 16, "bold"),
        ).pack()
        tk.Label(
            header, text="Powered by yt-dlp",
            bg="#1a1a2e", fg="#8888aa",
            font=("Helvetica", 10),
        ).pack()

        # ── URL ──────────────────────────────────────────────────────────────
        url_frame = _row(self, "Video URL:", 1)
        self.url_var   = tk.StringVar()
        self.url_entry = tk.Entry(url_frame, textvariable=self.url_var, width=44)
        self.url_entry.pack(side="left", expand=True, fill="x")
        self.url_entry.bind("<Return>", lambda _: self._fetch_formats())
        self.fetch_btn = tk.Button(
            url_frame, text="Fetch Formats →",
            command=self._fetch_formats, cursor="hand2",
        )
        self.fetch_btn.pack(side="left", padx=(8, 0))

        # ── Mode ─────────────────────────────────────────────────────────────
        mode_frame = _row(self, "Mode:", 2)
        self.mode_var = tk.StringVar(value="video")
        tk.Radiobutton(
            mode_frame, text="Video", variable=self.mode_var,
            value="video", command=self._on_mode_change,
        ).pack(side="left")
        tk.Radiobutton(
            mode_frame, text="Audio only (MP3)", variable=self.mode_var,
            value="audio", command=self._on_mode_change,
        ).pack(side="left", padx=(16, 0))

        # ── Format ───────────────────────────────────────────────────────────
        fmt_frame = _row(self, "Format:", 3)
        self.format_var   = tk.StringVar()
        self.format_combo = ttk.Combobox(
            fmt_frame, textvariable=self.format_var, state="disabled", width=54,
        )
        self.format_combo.pack(fill="x")

        # ── Save to ──────────────────────────────────────────────────────────
        out_frame = _row(self, "Save to:", 4)
        self.output_var = tk.StringVar(value=DEFAULT_OUT)
        tk.Entry(out_frame, textvariable=self.output_var, width=44).pack(side="left", expand=True, fill="x")
        tk.Button(
            out_frame, text=" Browse… ", command=self._browse, cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        # ── Progress bar ─────────────────────────────────────────────────────
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self, variable=self.progress_var, maximum=100, length=520,
        )
        self.progress_bar.grid(row=5, column=0, columnspan=2, padx=16, pady=(12, 0), sticky="ew")

        # ── Status label ─────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value='Paste a URL above and click "Fetch Formats" to begin.')
        tk.Label(
            self, textvariable=self.status_var,
            fg="#555", anchor="w", font=("Helvetica", 10),
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 0))

        # ── Download button ──────────────────────────────────────────────────
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=14)
        self.download_btn = tk.Button(
            btn_frame, text="⬇   Download", state="disabled",
            command=self._start_download, cursor="hand2",
            font=("Helvetica", 13, "bold"),
            padx=24, pady=8,
            relief="flat", bg="#1a1a2e", fg="white",
            activebackground="#2d2d5e", activeforeground="white",
        )
        self.download_btn.pack()

        # Thin separator
        ttk.Separator(self, orient="horizontal").grid(
            row=8, column=0, columnspan=2, sticky="ew", padx=16
        )
        tk.Label(
            self, text="Tip: only YouTube links are supported.",
            fg="#aaa", font=("Helvetica", 9),
        ).grid(row=9, column=0, columnspan=2, pady=(4, 10))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _set_status(self, msg: str, color: str = "#555"):
        self.status_var.set(msg)
        # Retrieve the label widget and update its color.
        for widget in self.grid_slaves(row=6):
            if isinstance(widget, tk.Label):
                widget.config(fg=color)

    def _set_busy(self, busy: bool):
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.url_entry.config(state=state)
        self.fetch_btn.config(state=state)
        # Download button is enabled only when not busy AND formats loaded (or audio mode)
        if not busy:
            self._refresh_download_btn()

    def _refresh_download_btn(self):
        audio = self.mode_var.get() == "audio"
        has_url = bool(self.url_var.get().strip())
        enabled = has_url and (audio or bool(self._formats))
        self.download_btn.config(state="normal" if enabled else "disabled")

    def _on_mode_change(self):
        audio = self.mode_var.get() == "audio"
        self.format_combo.config(state="disabled" if audio else ("readonly" if self._formats else "disabled"))
        self._refresh_download_btn()

    def _browse(self):
        path = filedialog.askdirectory(initialdir=self.output_var.get())
        if path:
            self.output_var.set(path)

    # ── Fetch formats ─────────────────────────────────────────────────────────

    def _fetch_formats(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(APP_TITLE, "Please enter a URL first.")
            return
        self._formats = []
        self.format_combo["values"] = []
        self.format_combo.config(state="disabled")
        self.download_btn.config(state="disabled")
        self._set_busy(True)
        self._set_status("Fetching video info…")
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url: str):
        try:
            opts = {"quiet": True, "noplaylist": True, **_build_ydlp_base_opts()}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            formats = info.get("formats", [])
            labels  = []
            for fmt in formats:
                res      = fmt.get("resolution") or "audio only"
                ext      = fmt.get("ext", "N/A")
                size     = fmt.get("filesize") or fmt.get("filesize_approx")
                size_str = f"{size / 1_000_000:.1f} MB" if size else "N/A"
                vcodec   = fmt.get("vcodec", "?")
                acodec   = fmt.get("acodec", "?")
                labels.append(f"{res}  |  {ext}  |  {size_str}  |  v:{vcodec} / a:{acodec}")

            title = info.get("title", "Unknown")
            self.after(0, lambda: self._on_formats_ready(formats, labels, title))

        except Exception as e:
            self.after(0, lambda err=str(e): self._on_fetch_error(err))

    def _on_formats_ready(self, formats, labels, title):
        self._formats = formats
        self.format_combo["values"] = labels
        if labels:
            self.format_combo.current(len(labels) - 1)     # default: best quality
        audio = self.mode_var.get() == "audio"
        self.format_combo.config(state="disabled" if audio else "readonly")
        self._set_busy(False)
        self._set_status(f"✅  \"{title}\"  —  Select a format and click Download.", color="#2e7d32")

    def _on_fetch_error(self, error: str):
        self._set_busy(False)
        self._set_status(f"❌  {error}", color="#c62828")
        messagebox.showerror(APP_TITLE, f"Could not fetch video info:\n\n{error}")

    # ── Download ──────────────────────────────────────────────────────────────

    def _start_download(self):
        url        = self.url_var.get().strip()
        output_dir = self.output_var.get().strip() or DEFAULT_OUT
        audio_only = self.mode_var.get() == "audio"

        if not url:
            messagebox.showwarning(APP_TITLE, "Please enter a URL.")
            return

        if not audio_only:
            idx = self.format_combo.current()
            if idx < 0 or not self._formats:
                messagebox.showwarning(APP_TITLE, "Please fetch and select a format first.")
                return
            format_id = self._formats[idx]["format_id"]
        else:
            format_id = None

        os.makedirs(output_dir, exist_ok=True)
        self.progress_var.set(0)
        self._set_busy(True)
        self._set_status("Starting download…")
        threading.Thread(
            target=self._download_thread,
            args=(url, format_id, output_dir, audio_only),
            daemon=True,
        ).start()

    def _download_thread(self, url: str, format_id: str | None, output_dir: str, audio_only: bool):
        def progress_hook(d: dict):
            if d["status"] == "downloading":
                total      = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                speed      = d.get("_speed_str", "—")
                eta        = d.get("_eta_str", "—")
                pct        = (downloaded / total * 100) if total else 0
                self.after(0, lambda p=pct, s=speed, e=eta: (
                    self.progress_var.set(p),
                    self._set_status(f"Downloading…  {p:.1f}%  |  {s}  |  ETA {e}"),
                ))
            elif d["status"] == "finished":
                self.after(0, lambda: self._set_status("Processing file…"))

        opts: dict = {
            "quiet":          True,
            "noplaylist":     True,
            "outtmpl":        os.path.join(output_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            **_build_ydlp_base_opts(),
        }

        if audio_only:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key":             "FFmpegExtractAudio",
                "preferredcodec":  "mp3",
                "preferredquality": "192",
            }]
        else:
            opts["format"] = format_id

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.after(0, lambda: self._on_done(output_dir))
        except Exception as e:
            self.after(0, lambda err=str(e): self._on_error(err))

    def _on_done(self, output_dir: str):
        self.progress_var.set(100)
        self._set_busy(False)
        self._set_status(f"✅  Download complete! Saved to: {output_dir}", color="#2e7d32")
        messagebox.showinfo(APP_TITLE, f"Download complete!\n\nSaved to:\n{output_dir}")
        # Reset for next download
        self.progress_var.set(0)
        self.url_var.set("")
        self._formats = []
        self.format_combo["values"] = []
        self.format_combo.config(state="disabled")
        self.download_btn.config(state="disabled")
        self._set_status('Paste a URL above and click "Fetch Formats" to begin.')

    def _on_error(self, error: str):
        self._set_busy(False)
        self._set_status(f"❌  {error}", color="#c62828")
        messagebox.showerror(APP_TITLE, f"Download failed:\n\n{error}")


# ─── Entry point ──────────────────────────────────────────────────────────────

def _warn_missing_deps():
    """Show a one-time warning if optional system tools are absent."""
    missing = []
    if not get_ffmpeg_path():
        missing.append(
            "• ffmpeg  —  required for merging video+audio and MP3 export.\n"
            "  Download: https://ffmpeg.org/download.html"
        )
    if not get_nodejs_path():
        missing.append(
            "• Node.js  —  recommended for full YouTube format support.\n"
            "  Download: https://nodejs.org"
        )
    if missing:
        body = (
            "Some optional dependencies were not found on your PATH.\n"
            "The downloader will still work, but some features may be limited.\n\n"
            + "\n\n".join(missing)
        )
        messagebox.showwarning(APP_TITLE, body)


if __name__ == "__main__":
    app = DownloaderApp()
    app.after(200, _warn_missing_deps)   # show warning after the window appears
    app.mainloop()
