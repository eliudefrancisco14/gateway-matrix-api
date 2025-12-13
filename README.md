# Broadcast Streaming API - Documentação de Execução Local

Esta documentação detalha os passos necessários para configurar e executar a **Broadcast Streaming API** na sua máquina local. A API foi desenvolvida em Python com o *framework* FastAPI e utiliza PostgreSQL como base de dados.

## 1. Pré-requisitos

Certifique-se de que os seguintes softwares estão instalados no seu sistema:

*   **Python 3.10+**
*   **pip** (gerenciador de pacotes do Python)
*   **PostgreSQL** (versão 12 ou superior recomendada)
*   **git** (para clonar o repositório, se aplicável)

## 2. Configuração do Ambiente

### 2.1. Variáveis de Ambiente

Crie um ficheiro chamado `.env` na raiz do projeto, copiando o conteúdo de `.env.example`. Este ficheiro contém as variáveis de ambiente necessárias para a aplicação.

```bash
cp .env.example .env
```

**Conteúdo de `.env` (Exemplo):**

```ini
# Configuração do PostgreSQL
DATABASE_URL=postgresql://postgres:password@localhost:5432/broadcast_db

# Configuração JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Configuração da API
API_TITLE=Broadcast Streaming API
API_VERSION=1.0.0
API_DESCRIPTION=API FastAPI para Sistema de Ingestão de Streams Broadcast
DEBUG=True

# Configuração de CORS
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Configuração de Logging
LOG_LEVEL=INFO
```

**Atenção à Segurança:** A `SECRET_KEY` deve ser alterada para uma string longa e aleatória em ambientes de produção.

### 2.2. Instalação de Dependências

Recomenda-se a criação de um ambiente virtual para isolar as dependências do projeto.

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
```

## 3. Configuração da Base de Dados

### 3.1. Criação da Base de Dados

A API requer uma base de dados PostgreSQL. Utilize o cliente `psql` ou uma ferramenta gráfica (como pgAdmin) para criar a base de dados especificada na variável `DATABASE_URL` (neste exemplo, `broadcast_db`).

```bash
# Exemplo de comando psql (assumindo que o utilizador 'postgres' existe)
psql -U postgres -c "CREATE DATABASE broadcast_db;"
```

### 3.2. Aplicação do Schema e Seeds Iniciais

O ficheiro `schema.sql` contém todas as instruções `CREATE TABLE` e os dados iniciais, incluindo o utilizador administrador.

**Nota Importante sobre a Senha do Admin:**

O utilizador inicial é:
*   **Email:** `efrancisco@underall.com`
*   **Senha:** `under2025`
*   **Role:** `admin`

O `schema.sql` contém um *hash* de senha **placeholder** (SHA-256 com prefixo bcrypt) devido à impossibilidade de instalar a biblioteca `bcrypt` no ambiente de geração. **Para a segurança e funcionalidade correta do login, você DEVE gerar um hash bcrypt real e substituir o valor no ficheiro `schema.sql` antes de o aplicar.**

**Passos para gerar o hash bcrypt (custo 12):**

1.  Instale a biblioteca `passlib` com suporte a `bcrypt`:
    ```bash
    pip install passlib[bcrypt]
    ```
2.  Execute um script Python para gerar o hash (exemplo):
    ```python
    from passlib.hash import bcrypt
    
    password = "under2025"
    # Custo mínimo 12, conforme especificação
    password_hash = bcrypt.using(rounds=12).hash(password)
    
    print(password_hash)
    ```
3.  Copie o hash gerado (ex: `$2b$12$XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`) e substitua o valor na linha `INSERT INTO users` no ficheiro `schema.sql`.

**Aplicação do Schema:**

Após a substituição do *hash* bcrypt, aplique o ficheiro `schema.sql` à sua base de dados:

```bash
psql -U postgres -d broadcast_db -f schema.sql
```

Se estiver em docker:

```bash
# Copiar para dentro do container
	docker cp .\schema.sql open-gateway-open-gateway-db-1:/tmp/schema.sql

# Aplicar o schema.sql
	psql -U postgres -d broadcast_db -f /tmp/schema.sql
```



## 4. Execução da API

Com as dependências instaladas e a base de dados configurada, inicie o servidor FastAPI:

```bash
# Certifique-se de que o ambiente virtual está ativo
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

A API estará acessível em `http://localhost:8000`.

## 5. Acesso à Documentação

A documentação interativa da API (Swagger UI) estará disponível em:

*   **Swagger UI:** `http://localhost:8000/docs`
*   **Redoc:** `http://localhost:8000/redoc`

Utilize o endpoint `/auth/login` com as credenciais do admin (`efrancisco@underall.com` e `under2025` - após a atualização do hash) para obter um token de acesso e testar os endpoints protegidos.
