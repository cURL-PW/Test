"""Video utilities for thumbnail generation and duration extraction."""

import os
import hashlib
from pathlib import Path
from typing import Optional
import cv2


# Supported video extensions
VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpeg", ".mpg", ".3gp", ".ogv"
}


def get_thumbnail_dir() -> Path:
    """Get the thumbnail cache directory."""
    thumb_dir = Path.home() / ".video_manager" / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    return thumb_dir


def get_video_hash(video_path: str) -> str:
    """Generate a hash for the video path for caching."""
    return hashlib.md5(video_path.encode()).hexdigest()


def get_video_duration(video_path: str) -> float:
    """Get the duration of a video in seconds using OpenCV."""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0.0

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()

        if fps > 0:
            return frame_count / fps
        return 0.0
    except Exception:
        return 0.0


def generate_thumbnail(video_path: str, size: tuple[int, int] = (320, 180),
                       position: float = 0.1) -> Optional[str]:
    """
    Generate a thumbnail for a video.

    Args:
        video_path: Path to the video file
        size: Thumbnail size (width, height)
        position: Position in video (0.0 to 1.0) to capture thumbnail

    Returns:
        Path to generated thumbnail or None if failed
    """
    try:
        video_hash = get_video_hash(video_path)
        thumb_path = get_thumbnail_dir() / f"{video_hash}.jpg"

        if thumb_path.exists():
            return str(thumb_path)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        target_frame = int(frame_count * position)

        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return None

        height, width = frame.shape[:2]
        target_w, target_h = size

        scale = min(target_w / width, target_h / height)
        new_w = int(width * scale)
        new_h = int(height * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        canvas = cv2.copyMakeBorder(
            resized,
            top=(target_h - new_h) // 2,
            bottom=(target_h - new_h + 1) // 2,
            left=(target_w - new_w) // 2,
            right=(target_w - new_w + 1) // 2,
            borderType=cv2.BORDER_CONSTANT,
            value=(0, 0, 0)
        )

        cv2.imwrite(str(thumb_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return str(thumb_path)

    except Exception:
        return None


def is_video_file(path: str) -> bool:
    """Check if a file is a video file based on extension."""
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def scan_folder_for_videos(folder_path: str) -> list[str]:
    """Scan a folder for video files (non-recursive)."""
    videos = []
    try:
        for entry in os.scandir(folder_path):
            if entry.is_file() and is_video_file(entry.path):
                videos.append(entry.path)
    except PermissionError:
        pass
    return sorted(videos)


def format_duration(seconds: float) -> str:
    """Format duration as HH:MM:SS or MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_video_info(video_path: str) -> dict:
    """Get comprehensive video information."""
    info = {
        "path": video_path,
        "filename": os.path.basename(video_path),
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "size": 0,
    }

    try:
        info["size"] = os.path.getsize(video_path)

        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            info["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            info["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            info["fps"] = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if info["fps"] > 0:
                info["duration"] = frame_count / info["fps"]
            cap.release()
    except Exception:
        pass

    return info
