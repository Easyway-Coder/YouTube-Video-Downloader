from pytubefix import YouTube
from customtkinter import *
from requests import get
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import showwarning, showinfo
from PIL import Image
import io, re, asyncio, aiohttp
from urllib.request import urlopen
from urllib.parse import quote

query_cache = {}

async def fetch_video_meta(session, video_id):
    """Fetch HTML and check if the video is a YouTube Short."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        async with session.get(url) as response:
            html = await response.text()

            #* Check if it's a Shorts video
            is_shorts = '"isShortsEligible":true' in html
            return video_id, is_shorts
    except Exception as e:
        print(f"Error checking video ID {video_id}: {e}")
        return video_id, False  #* assume not Shorts on error

async def filter_out_reels(video_ids):
    """Filter out Shorts by checking 'isShortsVideo' flag."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_video_meta(session, video_id) for video_id in video_ids]
        results = await asyncio.gather(*tasks)
        return [video_id for video_id, is_shorts in results if not is_shorts]

def convert_to_ffmpeg_mp3(file_path):
    """Convert a file to pure MP3 format using ffmpeg."""
    try:
        temp_file = file_path.replace(".mp3", " - TEMP.mp3")
        command = f"ffmpeg -i \"{file_path}\" \"{temp_file}\""
        os.system(command)
        os.replace(temp_file, file_path)  #* replace original with converted file
    except Exception as e:
        print(f"Error converting to MP3: {e}")
        return None


def get_video_ids(query: str):
    """Fetch video IDs from YouTube search results and filter out reels."""
    query = query.lower().strip()
    if query in query_cache:
        return query_cache[query]
    try:
        search_results = get(f"https://www.youtube.com/results?search_query={quote(query)}").text
        pattern = r'"videoId":"([a-zA-Z0-9_-]{11})"'
        video_ids = list(set(re.findall(pattern, search_results)))
        filtered_video_ids = list(set(asyncio.run(filter_out_reels(video_ids))))
        query_cache[query] = filtered_video_ids
        return filtered_video_ids
    except Exception as e:
        print(f"Error fetching video IDs for query: {e}")
        return []

def select_video(query, video_index=0):
    if not query:
        showwarning("Error", "Please enter a search term or paste a URL.")
        return

    #* Clear previously loaded content
    for widget in screen.winfo_children():
        if widget not in (search_bar, download_button, background_label):
            widget.destroy()

    if "youtube.com/watch?v=" in query or "youtu.be/" in query:
        url = query
    else:
        video_urls = get_video_ids(query)
        if not video_urls:
            showwarning("No Results", f"No videos found for '{query}'.")
            return
        if video_index >= len(video_urls):
            video_index = 0
        url = f"https://www.youtube.com/watch?v={video_urls[video_index]}"

    #* Create video object
    video = YouTube(url)

    #* Buttons (Audio/Video)
    audio_button = CTkButton(screen, font=("Roboto", 20, "bold"), text="Audio", width=125, fg_color="#0d77b6", command=lambda: download_video(video, audio=True))
    video_button = CTkButton(screen, font=("Roboto", 20, "bold"), text="Video", width=125, fg_color="#0d77b6", command=lambda: download_video(video, audio=False))

    #* Thumbnail
    thumbnail_url = video.thumbnail_url
    thumbnail_data = urlopen(thumbnail_url).read()
    thumbnail_image = Image.open(io.BytesIO(thumbnail_data))
    img = CTkImage(thumbnail_image, size=(450, 400))
    thumbnail_label = CTkLabel(screen, text="", image=img)
    thumbnail_label.place(x=175, y=240)

    #* Arrows
    left_arrow = CTkImage(Image.open(r"Images\left-arrow.png"), size=(75, 75))
    right_arrow = CTkImage(Image.open(r"Images\right-arrow.png"), size=(75, 75))

    left_button = CTkButton(screen, image=left_arrow, text="", width=2, fg_color="#CCCCCC", border_width=0, corner_radius=100, command=lambda: select_video(query, video_index - 1))
    right_button = CTkButton(screen, image=right_arrow, text="", width=2, fg_color="#CCCCCC", border_width=0, corner_radius=100, command=lambda: select_video(query, video_index + 1))

    left_button.place(x=10, y=360)
    right_button.place(x=680, y=360)
    audio_button.place(x=225, y=200)
    video_button.place(x=450, y=200)

def download_video(video: YouTube, audio=False):
    if video is None:
        showwarning("Error", "No video selected.")
        return

    #* Clear screen
    for widget in screen.winfo_children():
        if widget not in (search_bar, download_button, background_label):
            widget.destroy()

    download_label = CTkLabel(screen, text="DOWNLOADING...", font=("Bahnschrift", 60, "bold"), text_color="white", fg_color="#3F8F29", width=500)
    download_label.place(x=150, y=300)
    title = video.title
    if audio:
        stream = video.streams.get_audio_only()
        file = asksaveasfilename(defaultextension=".mp3", filetypes=[("Audio Files", "*.mp3")], initialfile=f"{title}.mp3")
    else:
        stream = video.streams.get_highest_resolution()
        file = asksaveasfilename(defaultextension=".mp4", filetypes=[("Video Files", "*.mp4")], initialfile=f"{title}.mp4")

    if file:
        elements = file.split("/")
        path = "/".join(elements[:-1])
        filename = elements[-1]
        stream.download(output_path=path, filename=filename)
        # if audio:
        #    convert_to_ffmpeg_mp3(file)
        showinfo("Success", f"Downloaded {title} successfully!")
    else:
        showwarning("Cancelled", "Download cancelled.")
    download_label.destroy()

if __name__ == "__main__":
    screen = CTk()

    #* Background Image
    bg_img = CTkImage(Image.open("Images/YouTube.png"), size=(800, 600))
    background_label = CTkLabel(screen, text="", image=bg_img)
    background_label.place(x=0, y=0)

    #* Search Bar
    query = StringVar()
    search_bar = CTkEntry(screen, border_color="white", fg_color="white", bg_color="black", width=770, font=("Arial", 34), corner_radius=75, text_color="black", textvariable=query)
    search_bar.bind("<Return>", lambda event: select_video(query.get()))
    search_bar.place(x=12, y=144)

    #* Download Button
    download_img = CTkImage(Image.open("Images/downloading.png"), size=(30, 30))
    download_button = CTkButton(screen, width=200, border_width=3, border_color="#144369", text_color="white", height=46, text="Download", image=download_img, corner_radius=75, font=("Roboto", 24, "bold"), bg_color="white", command=lambda: select_video(query.get()))
    download_button.place(x=600, y=144)

    screen.geometry("800x600")
    screen.title("YouTube Video Downloader")
    screen.resizable(False, False)

    try:
        screen.iconbitmap(r"Images/icon.ico")
    except:
        print("Icon not found, continuing without it.")

    screen.mainloop()
