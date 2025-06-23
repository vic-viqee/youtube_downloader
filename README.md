YouTube Downloader GUI

A feature-rich desktop application for downloading YouTube videos in MP4 format with a user-friendly interface. Built with Python and Kivy.

https://screenshot.png
Features

    🎥 Multiple Quality Options: Download in 4K, 1440p, 1080p, 720p, 480p or 360p

    🔊 Audio Quality Selection: Choose between 128kbps, 192kbps, 256kbps or 320kbps

    📋 Playlist Support: Download entire playlists or select specific videos

    🚀 Batch Processing: Download multiple videos simultaneously

    📋 Clipboard Monitoring: Auto-detect YouTube URLs in your clipboard

    🖼️ Thumbnail Preview: See video details before downloading

    📁 File Management: Customizable filename formats

    ⏯️ Resume Support: Continue interrupted downloads

    🖥️ Responsive UI: Adapts to different screen sizes

Installation
Prerequisites

    Python 3.7+

    pip

Steps

    Clone the repository:

bash

git clone https://github.com/yourusername/youtube-downloader-gui.git
cd youtube-downloader-gui

    Install required dependencies:

bash

pip install -r requirements.txt

    Run the application:

bash

python youtube_downloader_gui.py

Usage

    Paste YouTube URL(s) in the input field (multiple URLs separated by commas)

    Select video and audio quality

    Choose filename format

    Select download folder

    Click "Download MP4"

    Monitor progress in the status bar

For playlists:

    Paste playlist URL

    Choose "Select Videos" to pick specific videos

    Choose "Download All" for entire playlists

    Choose "Download First" for the first video only

Configuration

The application supports these configuration options:

    Video quality selection (1440p, 1080p, 720p, etc.)

    Audio quality selection (128kbps to 320kbps)

    Filename formats:

        Title Only

        Title + Quality

        ID + Title

    Playlist handling options

    Download folder selection

    Clipboard monitoring (enable/disable)

Contributing

Contributions are welcome! Please follow these steps:

    Fork the repository

    Create a new branch (git checkout -b feature/your-feature)

    Commit your changes (git commit -am 'Add some feature')

    Push to the branch (git push origin feature/your-feature)

    Open a pull request

License

This project is licensed under the MIT License - see the LICENSE file for details.
Support

If you encounter any issues or have questions, please open an issue.

Created with ❤️ in Python
