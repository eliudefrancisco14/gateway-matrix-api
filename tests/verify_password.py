from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)

# 1. Hash da senha
password = "under2025"
hashed = pwd_context.hash(password)
print(f"Hash gerado: {hashed}")
print(f"Tamanho do hash: {len(hashed)} caracteres")

# 2. Verificar senha correta
is_valid = pwd_context.verify("under2025", hashed)
print(f"Senha 'under2025' é válida: {is_valid}")

# 3. Verificar senha incorreta
is_invalid = pwd_context.verify("senha_errada", hashed)
print(f"Senha 'senha_errada' é válida: {is_invalid}")

# 4. Testar limite de 72 bytes
long_password = "a" * 72
long_hash = pwd_context.hash(long_password)
print(f"\nSenha de 72 caracteres: OK")

try:
    too_long = "a" * 73
    pwd_context.hash(too_long)
except ValueError as e:
    print(f"Senha de 73 caracteres: ERRO (esperado) - {e}")
