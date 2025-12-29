import os
import sys
import subprocess
import json

def has_ytdlp() -> bool:
    """
    Check if yt-dlp is installed. Return True if installed, False otherwise.
    """
    try:
        subprocess.run(["yt-dlp", "-h"], check=True, stdout=subprocess.DEVNULL, \
                       stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def select_format(url: str) -> str:
    """
    List available download format and return selected format ID.
    """
    format_ids = []

    # Fetch video info using yt-dlp.
    try:
        output = subprocess.run(['yt-dlp', url, '--dump-json'], capture_output=True, text=True, check=True)
        output = json.loads(output.stdout)
    except subprocess.CalledProcessError as e:
        print(f"No video available for that url.\n{e.returncode}: {e.stderr}")
        return ""

    if "formats" not in output:
        print("No available options to download.")
        return ""

    # List available formats.
    for video in enumerate(output["formats"]):
        print(f"{video[0]} - {video[1]['resolution']} - {video[1]['ext']}")
        format_ids.append(video[1]["format_id"])

    # Prompt user to select resolution.
    while True:
        choice = input("Select resolution by number [q to quit]: ")

        if choice == "q":
            return ""
        elif not choice.isdigit():
            print("Option must be a non-negative number. Please try again.")
            continue

        choice = int(choice)
        if choice >= len(format_ids):
            print("Invalid choice. Please try again.")
        else:
            return format_ids[choice]

def confirm_download() -> bool:
    """
    Confirm download with user. Return True if confirmed, False otherwise.
    """
    while True:
        confirm = input("Download? [Y/n]: ")

        if confirm.lower() == 'n':
            return False
        elif confirm.lower() in ['y', '']:
            return True

def download_video(url: str, format_id: str) -> None:
    """
    Run yt-dlp to download the video with the specified format ID.
    """
    command = ['yt-dlp', url, '-f', format_id]
    try:
        subprocess.run(command, check=True, text=True)
        print("Download complete!")
    except subprocess.CalledProcessError as e:
        print(f"Error during download.\n{e.returncode}: {e.stderr}{e.stderr}")
        pause()

def pause():
    """
    Pause the program until user presses a key.
    """
    os.system("pause") if os.name == 'nt' else os.system("read -p 'Press Enter to continue...'")

def main():
    # Check for ytdlp installation.
    if not has_ytdlp():
        print("⚠️  yt-dlp is not installed.")
        sys.exit()

    # Prompt user for video URL.
    url = input("Enter video URL [q to exit]: ")

    if url.lower() == 'q':
        sys.exit()

    # List available download format for user to choose.
    format_id = select_format(url)

    # Confirm download and download video.
    if format_id != "":
        confirm = confirm_download()
        if not confirm:
            print("Download cancelled.")
        else:
            download_video(url, format_id)
    main()

if __name__ == "__main__":
    main()
