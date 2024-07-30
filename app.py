from flask import Flask, request, render_template, send_from_directory
import os
import subprocess
import torch
import whisper
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
from moviepy.config import change_settings
import tempfile
import shutil

# Set the path to the ImageMagick executable
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

# Check if GPU is available and set the device accordingly
device = "cuda" if torch.cuda.is_available() else "cpu"

print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Current Device:", torch.cuda.current_device())
    print("Device Name:", torch.cuda.get_device_name(0))

# Load the main Whisper model
model = whisper.load_model("large", device=device)

app = Flask(__name__)

# Function to convert video to audio
def video2mp3(video_file, output_ext="mp3"):
    filename, ext = os.path.splitext(video_file)
    output_path = f"{filename}.{output_ext}"
    
    try:
        subprocess.call(
            ["ffmpeg", "-y", "-i", video_file, output_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT
        )
    except FileNotFoundError:
        raise Exception("ffmpeg not found. Please ensure ffmpeg is installed and in your PATH.")
    
    return output_path

# Function to split video into frame-wise clips
def split_video_framewise(video_path, clip_length_sec=5):
    clips = []
    output_dir = tempfile.mkdtemp()

    video_clip = VideoFileClip(video_path)
    frame_rate = video_clip.fps
    total_frames = int(video_clip.fps * video_clip.duration)
    
    for start_frame in range(0, total_frames, int(frame_rate * clip_length_sec)):
        end_frame = min(start_frame + int(frame_rate * clip_length_sec), total_frames)
        
        start_time = start_frame / frame_rate
        end_time = end_frame / frame_rate
        
        clip_path = os.path.join(output_dir, f"clip_{start_frame}_{end_frame}.mp4")
        video_clip.subclip(start_time, end_time).write_videofile(clip_path, codec="libx264", audio_codec="aac")
        clips.append(clip_path)
    
    return clips, output_dir

# Function to transcribe audio and translate to English
def transcribe_and_translate(audio_file):
    result = model.transcribe(audio_file, task="translate")
    return result['text']

# Function to add subtitles with styling
def add_subtitles(video_clip_path, subtitle_text):
    video_clip = VideoFileClip(video_clip_path)

    # Create the TextClip with border
    subtitle = TextClip(
        subtitle_text, fontsize=15, color='white', size=(video_clip.size[0] - 40, None),
        method='caption', align='center'
    ).set_position(('center', 'bottom')).set_duration(video_clip.duration)
    
    # Add a black border
    subtitle = subtitle.on_color(
        size=(subtitle.w + 10, subtitle.h + 10),
        color=(0, 0, 0), pos=('center', 'center')
    ).set_position(('center', 'bottom')).set_duration(video_clip.duration)

    video_with_subtitle = CompositeVideoClip([video_clip, subtitle])
    output_path = video_clip_path.replace(".mp4", "_with_subtitle.mp4")
    video_with_subtitle.write_videofile(output_path, codec="libx264", audio_codec="aac")
    return output_path

# Function to transcribe video
def translate(video_file):
    input_path = video_file
    clips, temp_dir = split_video_framewise(input_path)
    all_texts = []

    final_video_clips = []
    for clip in clips:
        audio_file = video2mp3(clip)
        result = transcribe_and_translate(audio_file)
        all_texts.append(result)
        video_with_subtitle = add_subtitles(clip, result)
        final_video_clips.append(video_with_subtitle)

    # Concatenate all the subtitle-added video clips into one
    final_clip = concatenate_videoclips([VideoFileClip(clip) for clip in final_video_clips], method="compose")
    final_output_path = os.path.join('static', "final_output.mp4")  # Save to the static directory
    final_clip.write_videofile(final_output_path, codec="libx264", audio_codec="aac")
    
    # Cleanup temporary files
    shutil.rmtree(temp_dir)
    
    return final_output_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        file_path = os.path.join(tempfile.mkdtemp(), file.filename)
        file.save(file_path)
        output_path = translate(file_path)
        return send_from_directory(directory='static', path="final_output.mp4", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
