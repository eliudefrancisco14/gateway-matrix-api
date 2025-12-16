"""
Stream Probe - Detecção de codecs, resolução e informações técnicas usando ffprobe.
"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


class StreamInfo:
    """Informações de um stream."""
    
    def __init__(self, data: Dict[str, Any]):
        self.video_codec: Optional[str] = None
        self.audio_codec: Optional[str] = None
        self.resolution: Optional[str] = None
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.fps: Optional[float] = None
        self.bitrate: Optional[int] = None
        self.duration: Optional[float] = None
        self.format_name: Optional[str] = None
        self.probe_time: datetime = datetime.utcnow()
        
        self._parse_data(data)
    
    def _parse_data(self, data: Dict[str, Any]):
        """Parse dos dados retornados pelo ffprobe."""
        try:
            # Format info
            if "format" in data:
                fmt = data["format"]
                self.format_name = fmt.get("format_name")
                self.bitrate = int(fmt.get("bit_rate", 0))
                self.duration = float(fmt.get("duration", 0))
            
            # Streams info
            if "streams" in data:
                for stream in data["streams"]:
                    codec_type = stream.get("codec_type")
                    
                    if codec_type == "video":
                        self.video_codec = stream.get("codec_name")
                        self.width = stream.get("width")
                        self.height = stream.get("height")
                        
                        if self.width and self.height:
                            self.resolution = f"{self.width}x{self.height}"
                        
                        # FPS (frame rate)
                        r_frame_rate = stream.get("r_frame_rate", "0/0")
                        if "/" in r_frame_rate:
                            num, den = map(int, r_frame_rate.split("/"))
                            if den > 0:
                                self.fps = round(num / den, 2)
                    
                    elif codec_type == "audio":
                        self.audio_codec = stream.get("codec_name")
        
        except Exception as e:
            logger.error(f"Erro ao parsear dados do ffprobe: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "resolution": self.resolution,
            "fps": self.fps,
            "bitrate_kbps": self.bitrate // 1000 if self.bitrate else None,
            "format": self.format_name,
            "duration_seconds": self.duration,
            "probed_at": self.probe_time.isoformat()
        }
    
    def is_valid(self) -> bool:
        """Verifica se o stream tem informações válidas."""
        return self.video_codec is not None or self.audio_codec is not None


class StreamProbe:
    """Utilitário para probe de streams usando ffprobe."""
    
    @staticmethod
    async def probe(
        endpoint_url: str,
        protocol: str = "unknown",
        timeout: int = 10
    ) -> Optional[StreamInfo]:
        """
        Executa probe em um stream.
        
        Args:
            endpoint_url: URL do endpoint
            protocol: Protocolo da fonte
            timeout: Timeout em segundos
        
        Returns:
            StreamInfo ou None se falhar
        """
        cmd = [
            settings.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            endpoint_url
        ]
        
        # Adicionar flags específicas por protocolo
        if protocol == "rtsp":
            cmd.insert(1, "-rtsp_transport")
            cmd.insert(2, "tcp")
        
        logger.info(f"Probing stream: {endpoint_url}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            if process.returncode != 0:
                error = stderr.decode('utf-8', errors='ignore')
                logger.error(f"ffprobe erro: {error}")
                return None
            
            # Parse JSON
            data = json.loads(stdout.decode('utf-8'))
            stream_info = StreamInfo(data)
            
            if stream_info.is_valid():
                logger.info(f"Probe sucesso: {stream_info.to_dict()}")
                return stream_info
            else:
                logger.warning("Probe retornou dados inválidos")
                return None
        
        except asyncio.TimeoutError:
            logger.error(f"Probe timeout após {timeout}s")
            return None
        
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON do ffprobe: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Erro ao executar probe: {e}")
            return None
    
    @staticmethod
    async def test_connectivity(
        endpoint_url: str,
        protocol: str = "unknown",
        timeout: int = 5
    ) -> bool:
        """
        Testa se o endpoint está acessível (teste rápido).
        
        Returns:
            True se conseguiu conectar, False caso contrário
        """
        cmd = [
            settings.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            endpoint_url
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.wait_for(process.communicate(), timeout=timeout)
            
            return process.returncode == 0
        
        except asyncio.TimeoutError:
            logger.debug(f"Connectivity test timeout: {endpoint_url}")
            return False
        
        except Exception as e:
            logger.debug(f"Connectivity test falhou: {e}")
            return False
    
    @staticmethod
    async def get_snapshot(
        endpoint_url: str,
        output_path: str,
        protocol: str = "unknown",
        timeout: int = 10
    ) -> bool:
        """
        Captura um frame (snapshot) do stream.
        
        Args:
            endpoint_url: URL do endpoint
            output_path: Caminho de saída para o JPEG
            protocol: Protocolo da fonte
            timeout: Timeout em segundos
        
        Returns:
            True se capturou com sucesso
        """
        cmd = [
            settings.ffmpeg_path,
            "-y",
            "-i", endpoint_url,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        
        # Flags específicas
        if protocol == "rtsp":
            cmd.insert(1, "-rtsp_transport")
            cmd.insert(2, "tcp")
        
        logger.info(f"Capturando snapshot: {output_path}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.wait_for(process.communicate(), timeout=timeout)
            
            if process.returncode == 0:
                logger.info(f"Snapshot capturado: {output_path}")
                return True
            else:
                logger.error("Falha ao capturar snapshot")
                return False
        
        except asyncio.TimeoutError:
            logger.error(f"Snapshot timeout após {timeout}s")
            return False
        
        except Exception as e:
            logger.error(f"Erro ao capturar snapshot: {e}")
            return False


# Instância global
stream_probe = StreamProbe()