"""System utilities - filesystem browser."""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/system", tags=["system"])


class ListDirRequest(BaseModel):
    path: str


class DirItem(BaseModel):
    name: str
    path: str
    type: str  # "dir" | "file"
    size: Optional[int] = None
    extension: Optional[str] = None


class ListDirResponse(BaseModel):
    path: str
    parent: Optional[str]
    items: List[DirItem]
    error: Optional[str] = None


@router.post("/list-directory")
def list_directory(req: ListDirRequest) -> ListDirResponse:
    """List contents of any directory path."""
    folder = Path(req.path)
    if not folder.exists():
        return ListDirResponse(path=req.path, parent=None, items=[], error="Path does not exist")
    if not folder.is_dir():
        return ListDirResponse(path=req.path, parent=None, items=[], error="Path is not a directory")
    
    try:
        parent = str(folder.parent) if folder.parent != folder else None
        items = []
        for item in sorted(folder.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                stat = item.stat()
                items.append(DirItem(
                    name=item.name,
                    path=str(item),
                    type="dir" if item.is_dir() else "file",
                    size=stat.st_size if item.is_file() else None,
                    extension=item.suffix.lower() if item.is_file() else None,
                ))
            except PermissionError:
                continue
        return ListDirResponse(path=str(folder), parent=parent, items=items)
    except PermissionError:
        return ListDirResponse(path=req.path, parent=None, items=[], error="Permission denied")
    except Exception as e:
        return ListDirResponse(path=req.path, parent=None, items=[], error=str(e))
