from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.ai.chatbot.vectorstore import (
    delete_document_group,
    ingest_document,
    list_document_groups,
    set_document_group_active,
)
from app.core.deps import get_db, require_admin
from app.models.user import User
from app.schemas.document import (
    DocumentBatchUploadItem,
    DocumentBatchUploadResponse,
    DocumentGroupResponse,
    DocumentResponse,
    DocumentToggle,
)

router = APIRouter(prefix="/documents", tags=["documents"])
SUPPORTED_DOCUMENT_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}


@router.get("", response_model=list[DocumentGroupResponse])
async def list_documents(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await list_document_groups(db)


@router.post("/upload", response_model=list[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="File rỗng")

    try:
        documents = await ingest_document(
            db,
            filename=file.filename or "document",
            data=data,
            uploaded_by=current_user.id,
            replace_existing=True,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return documents


@router.post("/upload-batch", response_model=DocumentBatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents_batch(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    files = [
        item
        for _, item in form.multi_items()
        if isinstance(item, StarletteUploadFile)
    ]
    if not files:
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" not in content_type.lower():
            raise HTTPException(
                status_code=422,
                detail="Request upload chưa đúng multipart/form-data. Hãy reload frontend mới rồi upload lại.",
            )
        raise HTTPException(status_code=422, detail="Chưa chọn file")

    results: list[DocumentBatchUploadItem] = []
    uploaded = 0
    failed = 0
    total_chunks = 0

    for upload in files:
        filename = upload.filename or "document"
        data = await upload.read()
        if not data:
            results.append(
                DocumentBatchUploadItem(filename=filename, status="failed", error="File rỗng")
            )
            failed += 1
            continue

        if filename.lower().endswith(".zip"):
            zip_results = await _ingest_zip(db, filename, data, current_user.id)
            results.extend(zip_results)
        else:
            results.append(await _ingest_single(db, filename, data, current_user.id))

    for item in results:
        if item.status == "uploaded":
            uploaded += 1
            total_chunks += item.chunks_count
        else:
            failed += 1

    return DocumentBatchUploadResponse(
        uploaded=uploaded,
        failed=failed,
        total_chunks=total_chunks,
        results=results,
    )


@router.patch("/{source_file:path}", response_model=dict)
async def toggle_document(
    source_file: str,
    payload: DocumentToggle,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    updated = await set_document_group_active(db, source_file, payload.is_active)
    if updated == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    return {"source_file": source_file, "updated": updated, "is_active": payload.is_active}


@router.delete("/{source_file:path}", response_model=dict)
async def delete_document(
    source_file: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_document_group(db, source_file)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    return {"source_file": source_file, "deleted": deleted}


async def _ingest_single(
    db: AsyncSession,
    filename: str,
    data: bytes,
    uploaded_by,
) -> DocumentBatchUploadItem:
    if PurePosixPath(filename).suffix.lower() not in SUPPORTED_DOCUMENT_SUFFIXES:
        return DocumentBatchUploadItem(
            filename=filename,
            status="failed",
            error="Định dạng không hỗ trợ. Chỉ nhận PDF, DOCX, TXT, MD hoặc ZIP.",
        )

    try:
        documents = await ingest_document(
            db,
            filename=filename,
            data=data,
            uploaded_by=uploaded_by,
            replace_existing=True,
        )
        return DocumentBatchUploadItem(
            filename=filename,
            status="uploaded",
            chunks_count=len(documents),
        )
    except (ValueError, RuntimeError) as exc:
        return DocumentBatchUploadItem(filename=filename, status="failed", error=str(exc))


async def _ingest_zip(
    db: AsyncSession,
    filename: str,
    data: bytes,
    uploaded_by,
) -> list[DocumentBatchUploadItem]:
    results: list[DocumentBatchUploadItem] = []
    try:
        with ZipFile(BytesIO(data)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                member_name = _clean_zip_member_name(member.filename)
                if not member_name:
                    continue
                if PurePosixPath(member_name).suffix.lower() not in SUPPORTED_DOCUMENT_SUFFIXES:
                    continue
                results.append(
                    await _ingest_single(
                        db,
                        member_name,
                        archive.read(member),
                        uploaded_by,
                    )
                )
    except BadZipFile:
        return [
            DocumentBatchUploadItem(
                filename=filename,
                status="failed",
                error="File ZIP không hợp lệ hoặc bị hỏng.",
            )
        ]

    if not results:
        return [
            DocumentBatchUploadItem(
                filename=filename,
                status="failed",
                error="ZIP không có file PDF, DOCX, TXT hoặc MD hợp lệ.",
            )
        ]
    return results


def _clean_zip_member_name(filename: str) -> str | None:
    path = PurePosixPath(filename.replace("\\", "/"))
    if path.is_absolute() or "__MACOSX" in path.parts or any(part == ".." for part in path.parts):
        return None
    cleaned = str(path)
    if not cleaned or cleaned.startswith("."):
        return None
    return cleaned
