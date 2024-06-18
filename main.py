import os
import shutil
import subprocess
import time
from threading import Timer, Thread
from flask import Flask, redirect, render_template, request, session

app = Flask(__name__, static_folder="song")
app.secret_key = "some_secret_key"


def delete_folder(folder_path, zip_path):
    try:
        shutil.rmtree(folder_path)
        os.remove(zip_path)
    except Exception as e:
        print(f"Error deleting folder: {e}")


def download_song(song_name, name_of_file):
    try:
        folder_path = os.path.join(app.static_folder, name_of_file)
        os.makedirs(folder_path, exist_ok=True)

        print("Downloading", name_of_file)
        subprocess.run(["spotdl", song_name], cwd=folder_path, check=True)

        # Clean up .spotdl-cache if exists
        try:
            shutil.rmtree(os.path.join(folder_path, ".spotdl-cache"))
        except FileNotFoundError:
            pass

        print("Download completed")

        # Create zip file
        print("Creating zip file")
        zip_path = shutil.make_archive(name_of_file, "zip", folder_path)
        print("Zip file created")

        # Schedule folder and zip deletion after 3 minutes
        delay_time = 60 * 3
        t = Timer(delay_time, delete_folder, args=[folder_path, zip_path])
        t.start()

        return folder_path, name_of_file, zip_path

    except subprocess.CalledProcessError as e:
        print(f"An error occurred during download: {e.stderr.decode()}")
        return None, None, None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None


@app.route("/")
def home():
    if "song_name" not in session or "name_of_file" not in session:
        return render_template("home.html")
    song_name = session["song_name"]
    name_of_file = session["name_of_file"]
    return redirect(f"/download?song_name={song_name}&name={name_of_file}")


@app.route("/download", methods=["GET", "POST"])
def download():
    if request.method == "POST":
        song_name = request.form.get("song_name")
        name_of_file = request.form.get("name_of_file")
        if not song_name or not name_of_file:
            return render_template("404.html"), 404
    else:
        song_name = request.args.get("song_name")
        name_of_file = request.args.get("name")

    if not song_name or not name_of_file:
        return render_template("404.html"), 404

    try:
        # Start the download in a separate thread
        download_thread = Thread(target=download_song, args=(song_name, name_of_file))
        download_thread.start()

        # Show download in progress page
        return render_template("download_in_progress.html")

    except Exception as e:
        return f"An error occurred: {e}", 500


@app.route("/check_download_status")
def check_download_status():
    if "song_name" not in session or "name_of_file" not in session:
        return render_template("404.html"), 404
    song_name = session["song_name"]
    name_of_file = session["name_of_file"]

    folder_path = os.path.join(app.static_folder, name_of_file)
    files = [
        {
            "name": file,
            "path": os.path.join(folder_path, file).replace("home/runner/spotify/", ""),
        }
        for file in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, file)) and file.endswith(".mp3")
    ]

    if not files:
        return "No files were found in the directory", 404

    return render_template("download.html", files=files, name_of_file=name_of_file)


if __name__ == "__main__":
    app.run(debug=False)
