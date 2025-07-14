# Dockerfile
# Use uma imagem base Python oficial. Python 3.10 é uma boa escolha estável.
FROM python:3.10-slim-buster

# Define o diretório de trabalho dentro do contêiner.
# Todos os comandos subsequentes serão executados neste diretório.
WORKDIR /app

# Copia o arquivo requirements.txt para o diretório de trabalho no contêiner.
# Isso permite que o pip instale as dependências.
COPY requirements.txt .

# Limpa o cache do pip e instala as dependências listadas em requirements.txt.
# --no-cache-dir garante que o pip não use caches locais, forçando um download limpo.
RUN pip cache purge && pip install --no-cache-dir -r requirements.txt

# Adiciona um comando para listar as bibliotecas instaladas (para depuração)
# Isso aparecerá nos logs de build do Render.
RUN pip freeze

# Copia todo o restante do código da sua aplicação para o diretório de trabalho.
# O '.' significa "copiar tudo do diretório atual para o diretório de trabalho do contêiner".
COPY . .

# Comando para iniciar a aplicação.
# O "bash -c" permite executar comandos mais complexos, e "-u" para logs não-bufferizados.
CMD ["bash", "-c", "python -u bot_localizador.py"]

