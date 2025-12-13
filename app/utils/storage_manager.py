"""
Storage Manager - Gestão de storage local para recordings, segments e thumbnails.
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import aiofiles
import asyncio

logger = logging.getLogger(__name__)


class StorageManager:
    """Gerenciador de storage local."""
    
    def __init__(self, base_path: str = "/var/broadcast/storage"):
        self.base_path = Path(base_path)
        self._ensure_structure()
    
    def _ensure_structure(self):
        """Garante que a estrutura de diretórios existe."""
        directories = [
            self.base_path / "recordings",
            self.base_path / "segments",
            self.base_path / "thumbnails",
            self.base_path / "temp"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Diretório garantido: {directory}")
    
    def get_recording_path(self, channel_slug: str, recording_id: str) -> Path:
        """Retorna o caminho para uma gravação."""
        path = self.base_path / "recordings" / channel_slug / recording_id
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_segment_path(self, channel_slug: str, segment_id: str) -> Path:
        """Retorna o caminho para um segmento."""
        path = self.base_path / "segments" / channel_slug / segment_id
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_thumbnail_path(self, channel_slug: str) -> Path:
        """Retorna o caminho para thumbnails de um canal."""
        path = self.base_path / "thumbnails" / channel_slug
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_temp_path(self) -> Path:
        """Retorna o caminho temporário."""
        return self.base_path / "temp"
    
    def get_hls_output_path(self, channel_slug: str) -> Path:
        """Retorna o caminho de saída HLS para um canal (streaming live)."""
        path = self.base_path / "hls" / channel_slug
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    async def save_file(self, source_path: str, dest_path: str) -> bool:
        """
        Copia um ficheiro de forma assíncrona.
        
        Args:
            source_path: Caminho de origem
            dest_path: Caminho de destino
        
        Returns:
            True se sucesso
        """
        try:
            # Garantir que o diretório de destino existe
            Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Copiar de forma assíncrona
            async with aiofiles.open(source_path, 'rb') as src:
                async with aiofiles.open(dest_path, 'wb') as dst:
                    content = await src.read()
                    await dst.write(content)
            
            logger.info(f"Ficheiro copiado: {source_path} -> {dest_path}")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao copiar ficheiro: {e}")
            return False
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Remove um ficheiro.
        
        Args:
            file_path: Caminho do ficheiro
        
        Returns:
            True se sucesso
        """
        try:
            path = Path(file_path)
            if path.exists():
                await asyncio.to_thread(path.unlink)
                logger.info(f"Ficheiro removido: {file_path}")
                return True
            return False
        
        except Exception as e:
            logger.error(f"Erro ao remover ficheiro: {e}")
            return False
    
    async def delete_directory(self, dir_path: str, recursive: bool = True) -> bool:
        """
        Remove um diretório.
        
        Args:
            dir_path: Caminho do diretório
            recursive: Se True, remove recursivamente
        
        Returns:
            True se sucesso
        """
        try:
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                if recursive:
                    await asyncio.to_thread(shutil.rmtree, str(path))
                else:
                    await asyncio.to_thread(path.rmdir)
                
                logger.info(f"Diretório removido: {dir_path}")
                return True
            return False
        
        except Exception as e:
            logger.error(f"Erro ao remover diretório: {e}")
            return False
    
    def list_files(self, directory: str, pattern: str = "*") -> List[Path]:
        """
        Lista ficheiros em um diretório.
        
        Args:
            directory: Caminho do diretório
            pattern: Padrão de glob (ex: "*.ts", "*.mp4")
        
        Returns:
            Lista de Path
        """
        try:
            path = Path(directory)
            if path.exists() and path.is_dir():
                return sorted(path.glob(pattern))
            return []
        
        except Exception as e:
            logger.error(f"Erro ao listar ficheiros: {e}")
            return []
    
    def get_directory_size(self, directory: str) -> int:
        """
        Calcula o tamanho total de um diretório em bytes.
        
        Args:
            directory: Caminho do diretório
        
        Returns:
            Tamanho em bytes
        """
        try:
            path = Path(directory)
            if path.exists() and path.is_dir():
                total_size = sum(
                    f.stat().st_size 
                    for f in path.rglob('*') 
                    if f.is_file()
                )
                return total_size
            return 0
        
        except Exception as e:
            logger.error(f"Erro ao calcular tamanho: {e}")
            return 0
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Obtém informações sobre um ficheiro.
        
        Returns:
            Dict com size, created_at, modified_at ou None
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                stat = path.stat()
                return {
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime),
                    "path": str(path)
                }
            return None
        
        except Exception as e:
            logger.error(f"Erro ao obter info do ficheiro: {e}")
            return None
    
    async def cleanup_old_segments(self, channel_slug: str, keep_latest: int = 10):
        """
        Remove segmentos antigos de um canal (mantém apenas os N mais recentes).
        
        Args:
            channel_slug: Slug do canal
            keep_latest: Número de segmentos a manter
        """
        try:
            hls_path = self.get_hls_output_path(channel_slug)
            segments = self.list_files(str(hls_path), "*.ts")
            
            if len(segments) > keep_latest:
                segments_to_delete = segments[:-keep_latest]
                
                for segment in segments_to_delete:
                    await self.delete_file(str(segment))
                
                logger.info(f"Removidos {len(segments_to_delete)} segmentos antigos de {channel_slug}")
        
        except Exception as e:
            logger.error(f"Erro ao limpar segmentos: {e}")
    
    def get_storage_stats(self) -> dict:
        """
        Retorna estatísticas de uso de storage.
        
        Returns:
            Dict com tamanhos por categoria
        """
        try:
            return {
                "recordings_bytes": self.get_directory_size(str(self.base_path / "recordings")),
                "segments_bytes": self.get_directory_size(str(self.base_path / "segments")),
                "thumbnails_bytes": self.get_directory_size(str(self.base_path / "thumbnails")),
                "hls_bytes": self.get_directory_size(str(self.base_path / "hls")),
                "total_bytes": self.get_directory_size(str(self.base_path))
            }
        
        except Exception as e:
            logger.error(f"Erro ao obter stats de storage: {e}")
            return {}


# Instância global
storage_manager = StorageManager()