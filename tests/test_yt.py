import subprocess
import sys
import os
import shutil
from app.core.config import settings

def test_yt_dlp():
    """Testa se o yt-dlp está funcionando corretamente."""
    
    print("🧪 Testando yt-dlp...")
    
    # Verificar múltiplos caminhos
    possible_paths = [
        "yt-dlp.exe",
        "yt-dlp",
        os.path.join(os.path.dirname(sys.executable), "Scripts", "yt-dlp.exe"),
        os.path.join(os.path.dirname(sys.executable), "Scripts", "yt-dlp"),
        shutil.which("yt-dlp"),
        shutil.which("yt-dlp.exe"),
    ]
    
    print("Possíveis caminhos para yt-dlp:")
    for path in possible_paths:
        if path:
            exists = os.path.exists(path) if os.path.isabs(path) else shutil.which(path) is not None
            print(f"  {'✅' if exists else '❌'} {path}")
    
    # Encontrar yt-dlp
    for path in possible_paths:
        if path and (os.path.exists(path) if os.path.isabs(path) else shutil.which(path)):
            settings.yt_dlp_path = path
            break
    
    if not settings.yt_dlp_path:
        print("❌ yt-dlp não encontrado!")
        print("💡 Instale com: pip install yt-dlp")
        return False
    
    print(f"\n✅ yt-dlp encontrado em: {settings.yt_dlp_path}")
    
    # Testar versão
    print("\n🧪 Testando versão do yt-dlp...")
    try:
        result = subprocess.run([settings.yt_dlp_path, "--version"], 
                              capture_output=True, 
                              text=True,
                              timeout=10)
        if result.returncode == 0:
            print(f"✅ Versão: {result.stdout.strip()}")
        else:
            print(f"❌ Erro ao verificar versão: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Erro ao executar yt-dlp: {e}")
        return False
    
    # Testar extração de URL (pode ser demorado)
    test_url = "https://www.youtube.com/watch?v=WqInuiJZn1Q"
    print(f"\n🧪 Testando extração de URL: {test_url}")
    
    try:
        cmd = [
            settings.yt_dlp_path,
            "--no-warnings",
            "--quiet",
            "--no-check-certificates",
            "-f", "best[ext=mp4]",
            "-g",
            test_url
        ]
        
        print(f"Comando: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, 
                              capture_output=True, 
                              text=True,
                              timeout=30)
        
        if result.returncode == 0:
            url = result.stdout.strip()
            if url:
                print(f"✅ URL extraída com sucesso!")
                print(f"URL (primeiros 100 chars): {url[:100]}...")
                print(f"Tamanho total: {len(url)} caracteres")
                
                # Verificar se é uma URL válida
                if url.startswith(('http://', 'https://')):
                    print("✅ URL parece válida")
                    return True
                else:
                    print(f"⚠ URL não começa com http:// ou https://: {url[:50]}")
                    return False
            else:
                print("❌ yt-dlp retornou string vazia")
                return False
        else:
            print(f"❌ Erro ao extrair URL:")
            print(f"Código: {result.returncode}")
            print(f"Stderr: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout ao extrair URL (30s)")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_yt_dlp()
    sys.exit(0 if success else 1)