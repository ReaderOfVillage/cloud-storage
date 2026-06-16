from fastapi import FastAPI
from fastapi import UploadFile
from fastapi import Depends
from fastapi.responses import StreamingResponse
from io import BytesIO
import mimetypes
import magic

import time
from metrics import HTTP_REQUESTS, HTTP_DURATION
from metrics import UPLOADS, UPLOAD_SIZE
from metrics import DOWNLOADS
from metrics import DELETES
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
from metrics import UPLOADS, UPLOAD_SIZE, UPLOAD_FAILURES, MINIO_ERRORS

from sqlalchemy.orm import Session

import uuid

from database import SessionLocal
from database import engine

from models import Base
from models import File

from storage import client

app = FastAPI()

Base.metadata.create_all(bind=engine)

def get_db():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@app.post("/upload")
async def upload_file(
    file: UploadFile,
    db: Session = Depends(get_db)
):
    try:
        file_id = str(uuid.uuid4())
        object_name = f"{file_id}-{file.filename}"

        data = await file.read()

        media_type = magic.from_buffer(data, mime=True)

        try:
            client.put_object(
                Bucket="cloud-storage-dev",
                Key=object_name,
                Body=data,
                ContentType=media_type
            )
        except Exception:
            MINIO_ERRORS.inc()
            raise

        new_file = File(
            id=file_id,
            filename=file.filename,
            storage_key=object_name,
            size=len(data)
        )

        db.add(new_file)
        db.commit()

        # success metrics
        UPLOADS.inc()
        UPLOAD_SIZE.observe(len(data))

        return {"id": file_id}

    except Exception:
        UPLOAD_FAILURES.inc()
        raise


@app.get("/files")
def list_files(
    db: Session = Depends(get_db)
):

    files = db.query(File).all()

    return files


@app.get("/download/{file_id}")
def download_file(
    file_id: str,
    db: Session = Depends(get_db)
):

    file = (
        db.query(File)
        .filter(File.id == file_id)
        .first()
    )

    #metrics
    DOWNLOADS.inc()

    try:
        obj = client.get_object(
            Bucket="cloud-storage-dev",
            Key=file.storage_key
        )

        stream = obj["Body"]
    except Exception:
        MINIO_ERRORS.inc()
        raise

    stat = client.head_object(
        Bucket="cloud-storage-dev",
        Key=file.storage_key
    )
    media_type = stat.get("ContentType") or "application/octet-stream"

    return StreamingResponse(
        stream,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file.filename}"'
        }
    )



@app.delete("/files/{file_id}")
def delete_file(
    file_id: str,
    db: Session = Depends(get_db)
):

    file = (
        db.query(File)
        .filter(File.id == file_id)
        .first()
    )

    if not file:
        return {"error": "file not found"}

    #metrics
    DELETES.inc()

    try:
        client.delete_object(
            Bucket="cloud-storage-dev",
            Key=file.storage_key
        )
    except Exception:
        MINIO_ERRORS.inc()
        raise


    db.delete(file)

    db.commit()

    return {
        "status": "deleted"
    }


@app.middleware("http")
async def metrics_middleware(request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    start = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        raise
    finally:
        duration = time.time() - start
        HTTP_REQUESTS.labels(
            method=request.method,
            endpoint=request.url.path,
            status=status_code
        ).inc()
        HTTP_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

    return response

@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/health")
def health():
    return {"status": "ok"}