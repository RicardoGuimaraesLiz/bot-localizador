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

# Comando para iniciar a aplicação.
# Adicionamos a flag -u para garantir que os logs sejam exibidos imediatamente,
# e um sleep antes de rodar o bot para dar tempo de inicialização (debug).
# O erro ainda aponta para Updater, o que é bizarro. Vamos tentar um CMD mais robusto.
CMD ["bash", "-c", "python -u bot_localizador.py"]
