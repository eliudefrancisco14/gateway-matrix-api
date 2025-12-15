"""
Rotas de streaming HLS/DASH.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from pathlib import Path
from app.core.database import get_db
from app.services.channel_service import ChannelService
from app.utils.storage_manager import storage_manager

router = APIRouter(prefix="/stream", tags=["streaming"])


@router.get("/{slug}/manifest.m3u8")
async def get_hls_manifest(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Retorna o manifest HLS de um canal.
    
    Args:
        slug: Slug do canal
    """
    # Buscar canal
    channel = ChannelService.get_channel_by_slug(db, slug)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    if channel.status != "live":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canal não está live"
        )
    
    # Caminho do manifest
    hls_path = storage_manager.get_hls_output_path(slug)
    manifest_path = hls_path / "manifest.m3u8"
    
    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest HLS não encontrado"
        )
    
    return FileResponse(
        path=str(manifest_path),
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.get("/{slug}/manifest.mpd")
async def get_dash_manifest(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Retorna o manifest DASH de um canal.
    
    Args:
        slug: Slug do canal
    """
    # Buscar canal
    channel = ChannelService.get_channel_by_slug(db, slug)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    if channel.status != "live":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canal não está live"
        )
    
    if channel.output_format not in ["dash", "both"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canal não está configurado para DASH"
        )
    
    # Caminho do manifest DASH
    hls_path = storage_manager.get_hls_output_path(slug)
    manifest_path = hls_path / "manifest.mpd"
    
    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest DASH não encontrado"
        )
    
    return FileResponse(
        path=str(manifest_path),
        media_type="application/dash+xml",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.get("/{slug}/{filename}")
async def get_segment(
    slug: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """
    Retorna um segmento de vídeo (HLS .ts ou DASH .m4s).
    
    Args:
        slug: Slug do canal
        filename: Nome do ficheiro do segmento
    """
    # Validar filename (segurança)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de ficheiro inválido"
        )
    
    # Buscar canal
    channel = ChannelService.get_channel_by_slug(db, slug)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    # Caminho do segmento
    hls_path = storage_manager.get_hls_output_path(slug)
    segment_path = hls_path / filename
    
    if not segment_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segmento não encontrado"
        )
    
    # Determinar media type
    if filename.endswith('.ts'):
        media_type = "video/mp2t"
    elif filename.endswith('.m4s'):
        media_type = "video/iso.segment"
    elif filename.endswith('.mp4'):
        media_type = "video/mp4"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=str(segment_path),
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "bytes"
        }
    )


@router.get("/{slug}/info")
async def get_stream_info(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Retorna informações sobre o stream de um canal.
    
    Args:
        slug: Slug do canal
    """
    channel = ChannelService.get_channel_by_slug(db, slug)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canal não encontrado"
        )
    
    # URLs de streaming
    hls_url = f"/stream/{slug}/manifest.m3u8" if channel.output_format in ["hls", "both"] else None
    dash_url = f"/stream/{slug}/manifest.mpd" if channel.output_format in ["dash", "both"] else None
    
    return {
        "channel_id": str(channel.id),
        "name": channel.name,
        "slug": channel.slug,
        "status": channel.status,
        "output_format": channel.output_format,
        "hls_url": hls_url,
        "dash_url": dash_url,
        "thumbnail_url": channel.thumbnail_url,
        "is_live": channel.status == "live"
    }