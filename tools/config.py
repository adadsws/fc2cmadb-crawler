"""辅助工具的独立配置。"""

COPY_BUFFER_SIZE = 1024 * 1024
PROGRESS_BAR_WIDTH = 30

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".heic", ".heif", ".avif", ".svg", ".ico", ".psd", ".raw", ".cr2",
    ".nef", ".arw", ".dng",
}
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".ts", ".m2ts", ".mts", ".3gp", ".ogv", ".rm",
    ".rmvb", ".vob", ".asf", ".divx", ".f4v",
}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

DEFAULT_SHORTCUT_DOMAIN = "fc2cmadb.com"
SHORTCUT_PREVIEW_LIMIT = 10
DOMAIN_COUNT_LIMIT = 20
