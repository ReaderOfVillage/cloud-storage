from prometheus_client import Counter, Histogram, Gauge

# HTTP
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)

# File operations
UPLOADS = Counter(
    "file_uploads_total",
    "Total file uploads"
)

DOWNLOADS = Counter(
    "file_downloads_total",
    "Total file downloads"
)

DELETES = Counter(
    "file_deletes_total",
    "Total file deletions"
)

UPLOAD_SIZE = Histogram(
    "file_upload_size_bytes",
    "Uploaded file sizes"
)

UPLOAD_FAILURES = Counter(
    "upload_failures_total",
    "Number of failed file uploads"
)

MINIO_ERRORS = Counter(
    "minio_errors_total",
    "Number of MinIO errors"
)