"""
Wrapper para FFmpeg - Gestão de processos de ingestão, transcodificação e segmentação.
Suporta: SRT, UDP, RTSP, HLS, HTTP_TS, DASH, YouTube
COMPATÍVEL COM WINDOWS
"""
import asyncio
import subprocess
import logging
import os
import sys
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import signal
from app.core.config import settings

logger = logging.getLogger(__name__)


class FFmpegProcess:
    """Representa um processo FFmpeg ativo."""
    
    def __init__(self, process: asyncio.subprocess.Process, command: str):
        self.process = process
        self.command = command
        self.is_running = True
        self.error_message: Optional[str] = None
    
    async def terminate(self):
        """Termina o processo de forma graciosa."""
        if self.process and self.is_running:
            try:
                # Windows: usar terminate() diretamente
                self.process.terminate()
                
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
                self.is_running = False
                logger.info("Processo FFmpeg terminado graciosamente")
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
                self.is_running = False
                logger.warning("Processo FFmpeg forçado a terminar (SIGKILL)")
    
    async def wait(self) -> int:
        """Aguarda o término do processo."""
        return await self.process.wait()


class FFmpegWrapper:
    """Wrapper para operações FFmpeg."""
    
    def __init__(self):
        self.active_processes: Dict[str, FFmpegProcess] = {}
        self._validate_executables()
    
    def _validate_executables(self):
        """Valida que FFmpeg e yt-dlp estão acessíveis."""
        # Validar FFmpeg
        if not Path(settings.ffmpeg_path).exists():
            logger.warning(f"FFmpeg não encontrado em: {settings.ffmpeg_path}")
        else:
            logger.info(f"FFmpeg encontrado: {settings.ffmpeg_path}")
        
        # Validar yt-dlp
        if not Path(settings.yt_dlp_path).exists():
            logger.warning(f"yt-dlp não encontrado em: {settings.yt_dlp_path}")
        else:
            logger.info(f"yt-dlp encontrado: {settings.yt_dlp_path}")
    
    @staticmethod
    async def _extract_youtube_url(youtube_url: str) -> Optional[str]:
        """
        Extrai URL de stream do YouTube usando yt-dlp.
        
        Args:
            youtube_url: URL do vídeo/live do YouTube
        
        Returns:
            URL do stream ou None se falhar
        """
        try:
            # Comando yt-dlp com argumentos corretos
            cmd = [
                settings.yt_dlp_path,
                "--no-check-certificates",  # Ignora problemas de SSL
                "--no-warnings",
                "--quiet",
                "-f", "best",  # Melhor formato disponível
                "-g",  # Retornar apenas URL
                youtube_url
            ]
            
            logger.info(f"Executando yt-dlp: {' '.join(cmd)}")
            
            # WINDOWS FIX: Usar subprocess.run ao invés de asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
            )
            
            # Verificar resultado
            if result.returncode == 0:
                stream_url = result.stdout.strip()
                if stream_url:
                    logger.info(f"✓ YouTube URL extraída com sucesso ({len(stream_url)} caracteres)")
                    logger.debug(f"Stream URL: {stream_url[:100]}...")
                    return stream_url
                else:
                    logger.error("yt-dlp retornou vazio")
                    return None
            else:
                error = result.stderr
                logger.error(f"yt-dlp falhou (código {result.returncode}): {error}")
                
                # Tentar formato alternativo (livestream)
                logger.info("Tentando formato alternativo para livestream...")
                return await FFmpegWrapper._extract_youtube_url_alternative(youtube_url)
        
        except FileNotFoundError:
            logger.error(f"❌ yt-dlp não encontrado em: {settings.yt_dlp_path}")
            logger.error("Instale com: pip install yt-dlp")
            return None
        
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp timeout (30s)")
            return None
        
        except Exception as e:
            logger.error(f"Erro ao extrair URL do YouTube: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    @staticmethod
    async def _extract_youtube_url_alternative(youtube_url: str) -> Optional[str]:
        """Tenta extrair URL com formato alternativo (para livestreams)."""
        try:
            cmd = [
                settings.yt_dlp_path,
                "--no-check-certificates",
                "--no-warnings",
                "--quiet",
                "-f", "worst",  # Usar worst para garantir compatibilidade
                "-g",
                youtube_url
            ]
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
            )
            
            if result.returncode == 0:
                stream_url = result.stdout.strip()
                if stream_url:
                    logger.info(f"✓ URL alternativa extraída: {stream_url[:100]}...")
                    return stream_url
            
            return None
        
        except Exception as e:
            logger.error(f"Formato alternativo falhou: {e}")
            return None
    
    @staticmethod
    async def _build_input_args(protocol: str, endpoint_url: str, connection_params: Optional[Dict] = None) -> list:
        """Constrói argumentos de input baseado no protocolo."""
        args = []
        params = connection_params or {}
        
        if protocol == "youtube":
            # YouTube: extrair URL real do stream
            logger.info(f"🎥 Processando YouTube: {endpoint_url}")
            stream_url = await FFmpegWrapper._extract_youtube_url(endpoint_url)
            
            if not stream_url:
                raise ValueError("Falha ao extrair URL do stream do YouTube")
            
            # Usar URL extraída
            args.extend(["-i", stream_url])
            logger.info("✓ YouTube: URL pronta para ingestão")
        
        elif protocol == "srt":
            # SRT: srt://host:port?mode=caller&latency=200
            latency = params.get("latency", 200)
            mode = params.get("mode", "caller")
            args.extend([
                "-i", f"{endpoint_url}?mode={mode}&latency={latency}"
            ])
        
        elif protocol == "udp":
            # UDP: udp://host:port
            buffer_size = params.get("buffer_size", 212992)
            args.extend([
                "-buffer_size", str(buffer_size),
                "-i", endpoint_url
            ])
            
            # Multicast (se especificado)
            if "multicast_group" in params:
                logger.info(f"UDP Multicast: {params['multicast_group']}")
        
        elif protocol == "rtsp":
            # RTSP: rtsp://host:port/path
            rtsp_transport = params.get("transport", "tcp")
            args.extend([
                "-rtsp_transport", rtsp_transport,
                "-i", endpoint_url
            ])
        
        elif protocol in ["hls", "http_ts", "dash"]:
            # HLS/HTTP/DASH: http://host/path/playlist.m3u8
            args.extend(["-i", endpoint_url])
        
        else:
            # Protocolo desconhecido: tentar como file/http genérico
            args.extend(["-i", endpoint_url])
        
        return args
    
    @staticmethod
    def _build_output_args(output_format: str, output_path: str, transcoding_profile: Optional[str] = None) -> list:
        """Constrói argumentos de output para HLS/DASH."""
        args = []
        
        # Garantir que usamos codecs compatíveis
        video_codec = "libx264" if transcoding_profile else "copy"
        audio_codec = "aac" if transcoding_profile else "copy"
        
        if output_format in ["hls", "both"]:
            # HLS: Segmentação adaptativa
            hls_time = 2  # 2 segundos por segmento
            hls_list_size = 5  # Manter 5 segmentos no manifest
            
            # Converter caminhos Windows para formato Unix (FFmpeg prefere)
            output_path_unix = output_path.replace("\\", "/")
            
            args.extend([
                "-c:v", video_codec,
                "-c:a", audio_codec,
                "-f", "hls",
                "-hls_time", str(hls_time),
                "-hls_list_size", str(hls_list_size),
                "-hls_flags", "delete_segments+append_list",
                "-hls_segment_filename", f"{output_path_unix}/segment_%03d.ts",
                f"{output_path_unix}/manifest.m3u8"
            ])
        
        if output_format in ["dash", "both"]:
            # DASH: Segmentação MPEG-DASH
            output_path_unix = output_path.replace("\\", "/")
            
            args.extend([
                "-c:v", video_codec,
                "-c:a", audio_codec,
                "-f", "dash",
                "-seg_duration", "2",
                "-use_template", "1",
                "-use_timeline", "1",
                "-init_seg_name", "init-$RepresentationID$.m4s",
                "-media_seg_name", "chunk-$RepresentationID$-$Number%05d$.m4s",
                f"{output_path_unix}/manifest.mpd"
            ])
        
        return args
    
    async def start_ingest(
        self,
        source_id: str,
        protocol: str,
        endpoint_url: str,
        output_path: str,
        output_format: str = "hls",
        connection_params: Optional[Dict] = None,
        transcoding_profile: Optional[str] = None,
        on_error: Optional[Callable] = None
    ) -> FFmpegProcess:
        """
        Inicia processo de ingestão de uma fonte.
        
        Args:
            source_id: ID único da fonte
            protocol: Protocolo da fonte (srt, udp, rtsp, youtube, etc)
            endpoint_url: URL do endpoint
            output_path: Caminho de saída dos segmentos
            output_format: Formato de saída (hls, dash, both)
            connection_params: Parâmetros de conexão específicos
            transcoding_profile: Perfil de transcodificação (se necessário)
            on_error: Callback para erros
        """
        # Criar diretório de saída
        Path(output_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Diretório criado: {output_path}")
        
        # Construir comando FFmpeg
        cmd = [settings.ffmpeg_path, "-y", "-loglevel", "info"]  # -y: overwrite, log verbose
        
        # Input args (com suporte a YouTube)
        try:
            input_args = await self._build_input_args(protocol, endpoint_url, connection_params)
            cmd.extend(input_args)
        except ValueError as e:
            logger.error(f"Erro ao construir argumentos de input: {e}")
            if on_error:
                await on_error(str(e))
            raise
        
        # Output args
        cmd.extend(self._build_output_args(output_format, output_path, transcoding_profile))
        
        # Log do comando completo (mascarar URLs sensíveis)
        safe_cmd = " ".join(cmd)
        for i, part in enumerate(cmd):
            if part.startswith(("http://", "https://", "srt://", "rtsp://", "udp://")):
                safe_cmd = safe_cmd.replace(part, "<STREAM_URL>")
        
        logger.info(f"🚀 Comando FFmpeg:\n{safe_cmd}")
        
        try:
            # Iniciar processo
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            ffmpeg_proc = FFmpegProcess(process, safe_cmd)
            self.active_processes[source_id] = ffmpeg_proc
            
            logger.info(f"✓ Processo FFmpeg iniciado (PID: {process.pid})")
            
            # Monitorar stderr em background
            asyncio.create_task(self._monitor_stderr(source_id, process, on_error))
            
            return ffmpeg_proc
        
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar FFmpeg: {type(e).__name__}: {e}")
            if on_error:
                await on_error(str(e))
            raise
    
    async def _monitor_stderr(self, source_id: str, process: asyncio.subprocess.Process, on_error: Optional[Callable]):
        """Monitora stderr do FFmpeg para detectar erros."""
        try:
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                
                line_str = line.decode('utf-8', errors='ignore').strip()
                
                # Log todas as mensagens (útil para debug)
                if line_str:
                    logger.debug(f"FFmpeg [{source_id}]: {line_str}")
                
                # Detectar erros críticos
                if any(err in line_str.lower() for err in ["error", "failed", "invalid"]):
                    logger.error(f"⚠️ FFmpeg [{source_id}]: {line_str}")
                    if on_error:
                        await on_error(line_str)
                
                # Detectar sucesso na conexão
                if "Stream mapping:" in line_str or "Output #0" in line_str:
                    logger.info(f"✓ FFmpeg [{source_id}]: Stream iniciado com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao monitorar stderr: {e}")
    
    async def stop_ingest(self, source_id: str) -> bool:
        """Para a ingestão de uma fonte."""
        if source_id in self.active_processes:
            ffmpeg_proc = self.active_processes[source_id]
            await ffmpeg_proc.terminate()
            del self.active_processes[source_id]
            logger.info(f"⏹️ Ingestão parada: {source_id}")
            return True
        return False
    
    async def restart_ingest(self, source_id: str) -> bool:
        """Reinicia a ingestão de uma fonte."""
        await self.stop_ingest(source_id)
        logger.info(f"🔄 Ingestão reiniciada: {source_id}")
        return True
    
    def is_running(self, source_id: str) -> bool:
        """Verifica se a ingestão está ativa."""
        return source_id in self.active_processes and self.active_processes[source_id].is_running
    
    async def get_process_stats(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Obtém estatísticas do processo FFmpeg."""
        if source_id not in self.active_processes:
            return None
        
        ffmpeg_proc = self.active_processes[source_id]
        
        return {
            "is_running": ffmpeg_proc.is_running,
            "command": ffmpeg_proc.command,
            "error": ffmpeg_proc.error_message
        }
    
    async def shutdown_all(self):
        """Para todos os processos FFmpeg ativos."""
        logger.info(f"⏹️ Parando {len(self.active_processes)} processos FFmpeg")
        
        tasks = [
            self.stop_ingest(source_id) 
            for source_id in list(self.active_processes.keys())
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("✓ Todos os processos FFmpeg parados")


# Instância global
ffmpeg_wrapper = FFmpegWrapper()