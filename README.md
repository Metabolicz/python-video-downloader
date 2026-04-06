# 🎬 Video Downloader

A user-friendly, cross-platform video and audio downloader application powered by [`yt-dlp`](https://github.com/yt-dlp/yt-dlp). Built with Python and Tkinter, it provides a simple graphical interface suitable for users of all experience levels to easily download media from YouTube and supported sites.

![Interface Demo](https://img.shields.io/badge/GUI-Tkinter-blue?style=flat-square&logo=python) ![Powered By yt-dlp](https://img.shields.io/badge/Powered_by-yt--dlp-red?style=flat-square) ![macOS Build](https://img.shields.io/badge/macOS-App_Bundle-lightgrey?style=flat-square&logo=apple)

## ✨ Features

- **Intuitive Interface**: Clean and simple graphical interface built with Tkinter. No terminal commands required!
- **Format Selection**: Automatically fetches and lists available video formats, displaying resolution, file size, format, and codecs.
- **Audio-Only Mode**: Quickly download and convert media directly to MP3 audio.
- **Progress Tracking**: Real-time progress bar with download speed and ETA.
- **Smart Directory Picker**: Choose exactly where to save your files (defaults to your `Downloads` folder).
- **Standalone App Support**: Can be built into a standalone `.app` bundle for macOS, making it perfectly portable without installing Python.

---

## 🛠️ Prerequisites (For Running from Source)

If you are running the application directly via Python, you will need:

- **Python 3.9+**
- **FFmpeg**: Required for audio conversion and merging video/audio streams.
  - **macOS:** `brew install ffmpeg`
  - **Windows:** Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or install via winget (`winget install ffmpeg`)
  - **Linux:** `sudo apt install ffmpeg`

---

## 🚀 Quick Start (Running script)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Metabolicz/python-video-downloader.git
   cd python-video-downloader
   ```

2. **Set up a virtual environment (recommended):**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows use: env\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python downloader.py
   ```

---

## 🍎 Building a Standalone macOS App (`.app` bundle)

If you want to package the application to share it with non-technical users on macOS (e.g., your parents), use the included build script! This will create an application that can be run with a simple double-click.

1. Open your terminal on a Mac.
2. Navigate to the project directory.
3. Run the automated build script:
   ```bash
   bash build_mac.sh
   ```

The script will automatically grab dependencies, use PyInstaller to package the app, and bundle FFmpeg inside it. 

Once finished, locate the **`Video Downloader.app`** inside the newly created `dist/` folder. You can drag and drop this to your `/Applications` directory!

> **Note:** The first time you open the app on a new Mac, you may need to bypass Gatekeeper by right-clicking the `.app` and selecting **Open**.

---

## 📜 License & Disclaimer

This project is intended strictly for personal and educational use. Always respect copyright laws and the terms of service of the platforms you are downloading from.