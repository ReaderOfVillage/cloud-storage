from fastapi import FastAPI
from fastapi import UploadFile
from fastapi import Depends
from fastapi.responses import StreamingResponse
from io import BytesIO

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

    file_id = str(uuid.uuid4())

    object_name = (
        f"{file_id}-{file.filename}"
    )

    data = await file.read()

    client.put_object(
        "uploads",
        object_name,
        data=BytesIO(data),
        length=len(data)
    )

    new_file = File(
        id=file_id,
        filename=file.filename,
        storage_key=object_name,
        size=len(data)
    )

    db.add(new_file)

    db.commit()

    return {
        "id": file_id
    }


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

    obj = client.get_object(
        "uploads",
        file.storage_key
    )

    return StreamingResponse(
        obj,
        media_type="application/octet-stream"
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

    client.remove_object(
        "uploads",
        file.storage_key
    )

    db.delete(file)

    db.commit()

    return {
        "status": "deleted"
    }
