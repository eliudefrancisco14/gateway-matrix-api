"""
Script de teste para validar yt-dlp.
"""
import subprocess
import sys
from pathlib import Path

YT_DLP_PATH = r"C:\Users\Call Center_3.DESKTOP-K28JJ02\AppData\Local\Programs\Python\Python312\Scripts\yt-dlp.exe"
TEST_URL = "https://www.youtube.com/watch?v=jfKfPfyJRdk"  # Livestream 24/7

def test_ytdlp():
    print("="*60)
    print("TESTE DE yt-dlp")
    print("="*60)
    
    # 1. Verificar se executável existe
    if not Path(YT_DLP_PATH).exists():
        print(f"❌ ERRO: yt-dlp não encontrado em:")
        print(f"   {YT_DLP_PATH}")
        print("\nSoluções:")
        print("1. pip install yt-dlp")
        print("2. Verifique o caminho no .env")
        return False
    
    print(f"✓ yt-dlp encontrado: {YT_DLP_PATH}\n")
    
    # 2. Testar extração de URL
    print(f"Testando URL: {TEST_URL}")
    print("Aguarde 15-30 segundos...\n")
    
    cmd = [
        YT_DLP_PATH,
        "--no-check-certificates",
        "--no-warnings",
        "-f", "best",
        "-g",
        TEST_URL
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        
        if result.returncode == 0:
            stream_url = result.stdout.strip()
            print("✓ SUCESSO! URL extraída:")
            print(f"  {stream_url[:100]}...")
            print(f"\n  Tamanho: {len(stream_url)} caracteres")
            return True
        else:
            print("❌ ERRO ao extrair URL:")
            print(result.stderr)
            return False
    
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT (30s)")
        return False
    
    except Exception as e:
        print(f"❌ ERRO: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_ytdlp()
    sys.exit(0 if success else 1)