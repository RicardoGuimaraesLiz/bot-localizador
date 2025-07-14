    # Dockerfile
    # Use uma imagem base Python oficial. Python 3.9 é uma boa escolha estável.
    FROM python:3.9-slim-buster

    # Define o diretório de trabalho dentro do contêiner.
    # Todos os comandos subsequentes serão executados neste diretório.
    WORKDIR /app

    # Copia o arquivo requirements.txt para o diretório de trabalho no contêiner.
    # Isso permite que o pip instale as dependências.
    COPY requirements.txt .

    # Limpa o cache do pip e instala as dependências listadas em requirements.txt.
    # --no-cache-dir garante que o pip não use caches locais, forçando um download limpo.
    RUN pip cache purge && pip install --no-cache-dir -r requirements.txt

    # Copia todo o restante do código da sua aplicação para o diretório de trabalho.
    # O '.' significa "copiar tudo do diretório atual para o diretório de trabalho do contêiner".
    COPY . .

    # O comando de inicialização da aplicação será especificado no Procfile.
    # Não precisamos de um CMD aqui se o Procfile for usado.
    