from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty
from threading import Thread, Event
import os
import yt_dlp
import queue
import time
import re

# Colors for UI
COLORS = {
    'background': (0.95, 0.95, 0.95, 1),
    'primary': (0.2, 0.6, 1, 1),
    'secondary': (0.3, 0.3, 0.3, 1),
    'success': (0.1, 0.8, 0.3, 1),
    'warning': (1, 0.6, 0, 1),
    'danger': (1, 0.3, 0.3, 1),
    'text': (0.1, 0.1, 0.1, 1),
    'input_bg': (1, 1, 1, 1),
    'card_bg': (1, 1, 1, 1),
    'header_bg': (0.85, 0.85, 0.85, 1),
}

# Custom CardLayout with background color support
class CardLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLORS['card_bg'])
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class FolderChooserPopup(Popup):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select Download Folder"
        self.size_hint = (0.9, 0.7)
        self.callback = callback

        layout = BoxLayout(orientation='vertical', spacing=dp(10))
        
        self.file_chooser = FileChooserListView(
            path=os.getcwd(),
            size_hint=(1, 0.85),
            dirselect=True
        )
        layout.add_widget(self.file_chooser)
        
        btn_layout = BoxLayout(size_hint=(1, 0.15), spacing=dp(10))
        cancel_btn = Button(
            text="Cancel", 
            background_color=COLORS['danger'],
            background_normal='',
            size_hint=(0.4, 1)
        )
        cancel_btn.bind(on_press=self.dismiss)
        
        select_btn = Button(
            text="Select", 
            background_color=COLORS['success'],
            background_normal='',
            size_hint=(0.6, 1)
        )
        select_btn.bind(on_press=self.select_folder)
        
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(select_btn)
        layout.add_widget(btn_layout)
        
        self.content = layout

    def select_folder(self, instance):
        if self.file_chooser.path:
            self.callback(self.file_chooser.path)
        self.dismiss()

class VideoInfoPopup(Popup):
    def __init__(self, videos, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select Videos to Download"
        self.size_hint = (0.9, 0.8)
        self.callback = callback
        self.selected_videos = []

        layout = BoxLayout(orientation='vertical', spacing=dp(10))
        
        # Header
        header = GridLayout(cols=3, size_hint=(1, None), height=dp(40))
        header.add_widget(Label(text='', size_hint=(0.1, 1)))
        header.add_widget(Label(text='Video Title', bold=True, size_hint=(0.7, 1)))
        header.add_widget(Label(text='Duration', bold=True, size_hint=(0.2, 1)))
        layout.add_widget(header)
        
        # Scrollable list
        scroll = ScrollView(size_hint=(1, 0.8))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(5))
        grid.bind(minimum_height=grid.setter('height'))
        
        for idx, video in enumerate(videos):
            row = BoxLayout(size_hint_y=None, height=dp(40))
            
            # Checkbox
            chk = CheckBox(size_hint=(0.1, 1), active=True)
            chk.bind(active=lambda instance, value, idx=idx: self.toggle_video(idx, value))
            row.add_widget(chk)
            
            # Title (truncated)
            title = video.get('title', f'Video {idx+1}')
            if len(title) > 40:
                title = title[:37] + '...'
            row.add_widget(Label(text=title, size_hint=(0.7, 1), halign='left'))
            
            # Duration
            duration = video.get('duration', 0)
            minutes, seconds = divmod(duration, 60)
            duration_str = f'{minutes}:{seconds:02d}'
            row.add_widget(Label(text=duration_str, size_hint=(0.2, 1)))
            
            grid.add_widget(row)
            self.selected_videos.append(idx)
        
        scroll.add_widget(grid)
        layout.add_widget(scroll)
        
        # Buttons
        btn_layout = BoxLayout(size_hint=(1, 0.1), spacing=dp(10))
        select_all = Button(text='Select All', size_hint=(0.3, 1))
        select_all.bind(on_press=lambda x: self.toggle_all(True))
        select_none = Button(text='Select None', size_hint=(0.3, 1))
        select_none.bind(on_press=lambda x: self.toggle_all(False))
        download_btn = Button(text='Download Selected', size_hint=(0.4, 1), 
                             background_color=COLORS['success'])
        download_btn.bind(on_press=self.confirm_selection)
        
        btn_layout.add_widget(select_all)
        btn_layout.add_widget(select_none)
        btn_layout.add_widget(download_btn)
        layout.add_widget(btn_layout)
        
        self.content = layout
    
    def toggle_video(self, idx, active):
        if active:
            if idx not in self.selected_videos:
                self.selected_videos.append(idx)
        else:
            if idx in self.selected_videos:
                self.selected_videos.remove(idx)
    
    def toggle_all(self, select):
        self.selected_videos = list(range(len(self.selected_videos))) if select else []
        for child in self.content.children[1].children[0].children[0].children:
            if hasattr(child, 'children') and len(child.children) > 0:
                checkbox = child.children[-1]
                if isinstance(checkbox, CheckBox):
                    checkbox.active = select
    
    def confirm_selection(self, instance):
        self.callback(self.selected_videos)
        self.dismiss()

class YouTubeDownloaderUI(BoxLayout):
    is_fetching = BooleanProperty(False)
    current_progress = NumericProperty(0)
    clipboard_monitor = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(15)
        self.spacing = dp(10)
        with self.canvas.before:
            Color(*COLORS['background'])
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        # Clipboard monitoring
        self.clipboard_timer = None
        
        # Create a scrollable area
        self.scroll_view = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            bar_width=dp(10),
            bar_color=COLORS['primary'],
            bar_inactive_color=[0.5, 0.5, 0.5, 0.5]
        )
        
        # Main content layout
        self.content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(10)
        )
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        self.scroll_view.add_widget(self.content_layout)
        self.add_widget(self.scroll_view)
        
        # Status bar at bottom (outside scroll)
        self.status_bar = BoxLayout(
            size_hint=(1, None),
            height=dp(60),
            padding=dp(10)
        )
        self.status_label = Label(
            text='Ready to download',
            halign='left',
            color=COLORS['text']
        )
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint=(1, None),
            height=dp(20)
        )
        self.status_bar.add_widget(self.status_label)
        self.status_bar.add_widget(self.progress_bar)
        self.add_widget(self.status_bar)
        
        # Now build the content
        self.build_content()
        
        # Initialize download queue
        self.download_queue = queue.Queue()
        self.active_downloads = []
        self.max_simultaneous = 3  # Simultaneous downloads
        self.download_threads = []
        
        # Start download processor
        self.start_download_processor()

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def build_content(self):
        # URL Input Card
        url_card = CardLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(150),
            padding=dp(10),
            spacing=dp(5)
        )
        url_card.add_widget(Label(
            text="YouTube URLs:", 
            size_hint=(1, None), 
            height=dp(25),
            color=COLORS['text'],
            bold=True
        ))
        self.url_input = TextInput(
            hint_text='Paste one or more YouTube URLs (separate with commas or newlines)',
            size_hint=(1, 0.6),
            background_color=COLORS['input_bg'],
            foreground_color=COLORS['text'],
            padding=dp(10)
        )
        url_card.add_widget(self.url_input)
        
        # Paste from clipboard button
        paste_btn = Button(
            text='Paste from Clipboard',
            size_hint=(1, None),
            height=dp(40),
            background_color=COLORS['secondary'],
            background_normal='',
            color=(1, 1, 1, 1)
        )
        paste_btn.bind(on_press=self.paste_from_clipboard)
        url_card.add_widget(paste_btn)
        self.content_layout.add_widget(url_card)
        
        # Preview Card
        preview_card = CardLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(200),
            padding=dp(10),
            spacing=dp(5)
        )
        preview_card.add_widget(Label(
            text="Preview:", 
            size_hint=(1, None), 
            height=dp(25),
            color=COLORS['text'],
            bold=True
        ))
        
        preview_content = BoxLayout(size_hint=(1, 1))
        self.thumbnail = AsyncImage(
            size_hint=(0.3, 1),
            allow_stretch=True,
            keep_ratio=True,
            source=''
        )
        preview_content.add_widget(self.thumbnail)
        
        preview_info = BoxLayout(
            orientation='vertical',
            size_hint=(0.7, 1)
        )
        self.title_label = Label(
            text='No video selected',
            size_hint=(1, 0.3),
            color=COLORS['text'],
            halign='left',
            valign='top'
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        
        self.duration_label = Label(
            text='Duration: ',
            size_hint=(1, 0.2),
            color=COLORS['text'],
            halign='left'
        )
        
        self.resolution_label = Label(
            text='Resolutions: ',
            size_hint=(1, 0.3),
            color=COLORS['text'],
            halign='left'
        )
        self.resolution_label.bind(size=self.resolution_label.setter('text_size'))
        
        self.audio_label = Label(
            text='Audio Quality: ',
            size_hint=(1, 0.2),
            color=COLORS['text'],
            halign='left'
        )
        
        preview_info.add_widget(self.title_label)
        preview_info.add_widget(self.duration_label)
        preview_info.add_widget(self.resolution_label)
        preview_info.add_widget(self.audio_label)
        preview_content.add_widget(preview_info)
        preview_card.add_widget(preview_content)
        self.content_layout.add_widget(preview_card)
        
        # Options Card
        options_card = CardLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(250),
            padding=dp(10),
            spacing=dp(5)
        )
        options_card.add_widget(Label(
            text="Download Options:", 
            size_hint=(1, None), 
            height=dp(25),
            color=COLORS['text'],
            bold=True
        ))
        
        # Quality selection
        quality_layout = BoxLayout(size_hint=(1, 0.3))
        quality_layout.add_widget(Label(
            text="Video Quality:", 
            size_hint=(0.3, 1),
            color=COLORS['text']
        ))
        self.video_quality = Spinner(
            text='1080p',
            values=('1440p', '2160p (4K)', '1080p', '720p', '480p', '360p', 'Best Available'),
            size_hint=(0.7, 1),
            background_color=COLORS['primary'],
            background_normal='',
            color=(1, 1, 1, 1)
        )
        quality_layout.add_widget(self.video_quality)
        options_card.add_widget(quality_layout)
        
        # Audio quality
        audio_layout = BoxLayout(size_hint=(1, 0.3))
        audio_layout.add_widget(Label(
            text="Audio Quality:", 
            size_hint=(0.3, 1),
            color=COLORS['text']
        ))
        self.audio_quality = Spinner(
            text='192kbps',
            values=('320kbps', '256kbps', '192kbps', '128kbps', 'Best Available'),
            size_hint=(0.7, 1),
            background_color=COLORS['primary'],
            background_normal='',
            color=(1, 1, 1, 1)
        )
        audio_layout.add_widget(self.audio_quality)
        options_card.add_widget(audio_layout)
        
        # File naming
        file_layout = BoxLayout(size_hint=(1, 0.3))
        file_layout.add_widget(Label(
            text="Filename Format:", 
            size_hint=(0.3, 1),
            color=COLORS['text']
        ))
        self.filename_format = Spinner(
            text='Title Only',
            values=('Title Only', 'Title + Quality', 'ID + Title', 'Custom'),
            size_hint=(0.7, 1),
            background_color=COLORS['primary'],
            background_normal='',
            color=(1, 1, 1, 1)
        )
        file_layout.add_widget(self.filename_format)
        options_card.add_widget(file_layout)
        
        # Playlist options
        playlist_layout = BoxLayout(size_hint=(1, 0.3))
        playlist_layout.add_widget(Label(
            text="Playlist Handling:", 
            size_hint=(0.3, 1),
            color=COLORS['text']
        ))
        self.playlist_option = Spinner(
            text='Download All',
            values=('Download All', 'Select Videos', 'Download First'),
            size_hint=(0.7, 1),
            background_color=COLORS['primary'],
            background_normal='',
            color=(1, 1, 1, 1)
        )
        playlist_layout.add_widget(self.playlist_option)
        options_card.add_widget(playlist_layout)
        
        self.content_layout.add_widget(options_card)
        
        # Folder Card
        folder_card = CardLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(120),
            padding=dp(10),
            spacing=dp(5)
        )
        folder_card.add_widget(Label(
            text="Save Location:", 
            size_hint=(1, None), 
            height=dp(25),
            color=COLORS['text'],
            bold=True
        ))
        
        folder_layout = BoxLayout(size_hint=(1, 0.7))
        self.folder_label = Label(
            text=os.getcwd(),
            size_hint=(0.7, 1),
            color=COLORS['text'],
            halign='left',
            valign='middle'
        )
        self.folder_label.bind(size=self.folder_label.setter('text_size'))
        folder_layout.add_widget(self.folder_label)
        
        self.choose_folder_button = Button(
            text='Change',
            size_hint=(0.3, 1),
            background_color=COLORS['secondary'],
            background_normal='',
            color=(1, 1, 1, 1)
        )
        self.choose_folder_button.bind(on_press=self.choose_folder)
        folder_layout.add_widget(self.choose_folder_button)
        folder_card.add_widget(folder_layout)
        self.content_layout.add_widget(folder_card)
        
        # Download Button Card
        download_card = CardLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(80),
            padding=dp(10),
            spacing=dp(5)
        )
        self.download_button = Button(
            text='Download MP4',
            size_hint=(1, 1),
            background_color=COLORS['primary'],
            background_normal='',
            color=(1, 1, 1, 1),
            bold=True
        )
        self.download_button.bind(on_press=self.on_download)
        download_card.add_widget(self.download_button)
        self.content_layout.add_widget(download_card)
        
        # Clipboard monitoring
        clipboard_card = CardLayout(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(60),
            padding=dp(10),
            spacing=dp(5)
        )
        clipboard_layout = BoxLayout(size_hint=(1, 1))
        clipboard_layout.add_widget(Label(
            text='Monitor clipboard for YouTube URLs:',
            size_hint=(0.7, 1),
            color=COLORS['text']
        ))
        self.clipboard_toggle = CheckBox(
            size_hint=(0.1, 1),
            active=True
        )
        self.clipboard_toggle.bind(active=self.toggle_clipboard_monitor)
        clipboard_layout.add_widget(self.clipboard_toggle)
        clipboard_card.add_widget(clipboard_layout)
        self.content_layout.add_widget(clipboard_card)
        
        self.download_folder = os.getcwd()
        self.video_info = {}
        self.playlist_videos = []
        
        # Start clipboard monitoring
        self.toggle_clipboard_monitor(None, True)

    def choose_folder(self, instance):
        FolderChooserPopup(self.set_download_folder).open()

    @mainthread
    def set_download_folder(self, path):
        self.download_folder = path
        self.folder_label.text = path
        self.status_label.text = f'Folder set to: {os.path.basename(path)}'

    def paste_from_clipboard(self, instance):
        clipboard_text = Clipboard.paste()
        if clipboard_text:
            self.url_input.text = clipboard_text
            self.status_label.text = 'URLs pasted from clipboard!'

    def toggle_clipboard_monitor(self, instance, value):
        self.clipboard_monitor = value
        if value:
            if not self.clipboard_timer:
                self.clipboard_timer = Clock.schedule_interval(self.check_clipboard, 1)
        else:
            if self.clipboard_timer:
                self.clipboard_timer.cancel()
                self.clipboard_timer = None

    def check_clipboard(self, dt):
        try:
            clipboard_text = Clipboard.paste()
            if self.is_youtube_url(clipboard_text) and clipboard_text != self.url_input.text:
                self.url_input.text = clipboard_text
                self.status_label.text = 'YouTube URL detected in clipboard!'
        except:
            pass

    def is_youtube_url(self, text):
        patterns = [
            r'https?://(www\.)?youtube\.com/watch\?v=',
            r'https?://youtu\.be/',
            r'https?://(www\.)?youtube\.com/playlist\?list='
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    def on_download(self, instance):
        urls = self.url_input.text.strip()
        if not urls:
            self.set_status('Please enter YouTube URLs')
            return
            
        # Split URLs by comma or newline
        url_list = [url.strip() for url in urls.replace('\n', ',').split(',') if url.strip()]
        
        # Process each URL
        for url in url_list:
            if 'playlist?list=' in url:
                self.process_playlist(url)
            else:
                self.add_to_queue(url)

    def process_playlist(self, url):
        self.set_status(f'Fetching playlist info...')
        Thread(target=self.fetch_playlist_info, args=(url,), daemon=True).start()

    def fetch_playlist_info(self, url):
        try:
            ydl = yt_dlp.YoutubeDL({
                'quiet': True,
                'extract_flat': 'in_playlist',
                'ignoreerrors': True
            })
            info = ydl.extract_info(url, download=False)
            
            if not info or 'entries' not in info:
                self.set_status('Error: Could not fetch playlist info')
                return
                
            self.playlist_videos = []
            for entry in info['entries']:
                if entry:
                    self.playlist_videos.append({
                        'url': entry.get('url', ''),
                        'title': entry.get('title', ''),
                        'duration': entry.get('duration', 0)
                    })
            
            if self.playlist_option.text == 'Download All':
                for video in self.playlist_videos:
                    self.add_to_queue(video['url'])
            elif self.playlist_option.text == 'Download First':
                if self.playlist_videos:
                    self.add_to_queue(self.playlist_videos[0]['url'])
            else:  # Select Videos
                self.show_video_selection()
                
        except Exception as e:
            self.set_status(f'Error: {str(e)}')

    @mainthread
    def show_video_selection(self):
        if not self.playlist_videos:
            self.set_status('No videos in playlist')
            return
            
        VideoInfoPopup(
            videos=self.playlist_videos,
            callback=self.download_selected_videos
        ).open()

    def download_selected_videos(self, selected_indices):
        for idx in selected_indices:
            if idx < len(self.playlist_videos):
                self.add_to_queue(self.playlist_videos[idx]['url'])

    def add_to_queue(self, url):
        self.download_queue.put({
            'url': url,
            'video_quality': self.video_quality.text,
            'audio_quality': self.audio_quality.text,
            'filename_format': self.filename_format.text
        })
        self.set_status(f'Added to queue: {url[:50]}...')
        self.update_preview(url)

    def update_preview(self, url):
        Thread(target=self.fetch_video_info, args=(url,), daemon=True).start()

    def fetch_video_info(self, url):
        try:
            ydl = yt_dlp.YoutubeDL({
                'quiet': True,
                'ignoreerrors': True
            })
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return
                
            # Get available formats
            formats = info.get('formats', [])
            resolutions = set()
            audio_qualities = set()
            
            for f in formats:
                if f.get('vcodec') != 'none':  # Video format
                    res = f.get('format_note', '')
                    if res:
                        resolutions.add(res)
                elif f.get('acodec') != 'none':  # Audio format
                    abr = f.get('abr', 0)
                    if abr:
                        audio_qualities.add(f'{int(abr)}kbps')
            
            # Sort and format resolutions
            resolution_order = ['1440p', '1080p', '720p', '480p', '360p', '240p', '144p']
            sorted_res = sorted(resolutions, key=lambda x: resolution_order.index(x) if x in resolution_order else 100)
            res_text = ', '.join(sorted_res) if sorted_res else 'N/A'
            
            # Sort audio qualities
            sorted_audio = sorted(audio_qualities, key=lambda x: int(x.replace('kbps', '')), reverse=True)
            audio_text = ', '.join(sorted_audio) if sorted_audio else 'N/A'
            
            # Duration
            duration = info.get('duration', 0)
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            if hours > 0:
                duration_str = f'{hours}:{minutes:02d}:{seconds:02d}'
            else:
                duration_str = f'{minutes}:{seconds:02d}'
            
            # Update UI
            self.update_preview_ui(
                title=info.get('title', 'N/A'),
                duration=duration_str,
                resolutions=res_text,
                audio=audio_text,
                thumbnail=info.get('thumbnail', '')
            )
            
        except Exception as e:
            print(f"Preview error: {str(e)}")

    @mainthread
    def update_preview_ui(self, title, duration, resolutions, audio, thumbnail):
        self.title_label.text = title
        self.duration_label.text = f'Duration: {duration}'
        self.resolution_label.text = f'Available Resolutions: {resolutions}'
        self.audio_label.text = f'Available Audio: {audio}'
        self.thumbnail.source = thumbnail

    def start_download_processor(self):
        for _ in range(self.max_simultaneous):
            thread = Thread(target=self.download_worker, daemon=True)
            thread.start()
            self.download_threads.append(thread)

    def download_worker(self):
        while True:
            item = self.download_queue.get()
            if item is None:  # Exit signal
                break
            self.download_video(item)
            self.download_queue.task_done()

    def download_video(self, item):
        url = item['url']
        video_quality = item['video_quality']
        audio_quality = item['audio_quality']
        filename_format = item['filename_format']
        
        try:
            # Create the download directory if it doesn't exist
            os.makedirs(self.download_folder, exist_ok=True)
            
            # Format selection based on quality
            format_string = self.get_format_string(video_quality, audio_quality)
            
            # Filename template
            out_template = self.get_filename_template(filename_format)
            
            ydl_opts = {
                'format': format_string,
                'outtmpl': os.path.join(self.download_folder, out_template),
                'progress_hooks': [self.progress_hook],
                'restrictfilenames': True,
                'merge_output_format': 'mp4',
                'noplaylist': True,
            }

            self.set_status(f'Starting download: {url[:50]}...')
            self.set_progress(0)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            self.set_status(f'Download completed: {url[:50]}...')
            self.set_progress(100)
            
        except Exception as e:
            self.set_status(f'Error: {str(e)}')
            
        time.sleep(1)  # Brief pause between downloads

    def get_format_string(self, video_quality, audio_quality):
        # Map quality names to format specifications
        video_map = {
            '2160p (4K)': 'bestvideo[height<=2160][ext=mp4]',
            '1440p': 'bestvideo[height<=1440][ext=mp4]',
            '1080p': 'bestvideo[height<=1080][ext=mp4]',
            '720p': 'bestvideo[height<=720][ext=mp4]',
            '480p': 'bestvideo[height<=480][ext=mp4]',
            '360p': 'bestvideo[height<=360][ext=mp4]',
            'Best Available': 'bestvideo[ext=mp4]'
        }
        
        audio_map = {
            '320kbps': 'bestaudio[abr>=320]',
            '256kbps': 'bestaudio[abr>=256]',
            '192kbps': 'bestaudio[abr>=192]',
            '128kbps': 'bestaudio[abr>=128]',
            'Best Available': 'bestaudio'
        }
        
        video_fmt = video_map.get(video_quality, 'bestvideo[ext=mp4]')
        audio_fmt = audio_map.get(audio_quality, 'bestaudio')
        
        return f'{video_fmt}+{audio_fmt}/best'

    def get_filename_template(self, format_option):
        templates = {
            'Title Only': '%(title)s.%(ext)s',
            'Title + Quality': '%(title)s [%(resolution)s].%(ext)s',
            'ID + Title': '%(id)s - %(title)s.%(ext)s',
            'Custom': '%(title)s.%(ext)s'  # Default if custom not implemented
        }
        return templates.get(format_option, '%(title)s.%(ext)s')

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '').replace('%', '').strip()
            try:
                percent_float = float(percent_str)
                self.set_progress(percent_float)
                self.set_status(f"Downloading... {percent_float:.1f}%")
            except:
                pass
        elif d['status'] == 'finished':
            self.set_status('Finalizing MP4 file...')

    @mainthread
    def set_status(self, message):
        self.status_label.text = message

    @mainthread
    def set_progress(self, value):
        self.current_progress = value

class YouTubeDownloaderApp(App):
    def build(self):
        Window.minimum_width = dp(800)
        Window.minimum_height = dp(700)
        return YouTubeDownloaderUI()
    
    def on_stop(self):
        # Clean up clipboard monitoring
        if self.root.clipboard_timer:
            self.root.clipboard_timer.cancel()


if __name__ == '__main__':
    YouTubeDownloaderApp().run()
