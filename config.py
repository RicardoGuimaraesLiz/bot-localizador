import os

# Carrega o token do bot de uma variável de ambiente
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Carrega a URL e a chave do Supabase de variáveis de ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Opcional: Adicione verificações para garantir que as variáveis foram carregadas
# Estas mensagens aparecerão nos logs se as variáveis não estiverem definidas
if not BOT_TOKEN:
    print("Erro: BOT_TOKEN não configurado como variável de ambiente!")
if not SUPABASE_URL:
    print("Erro: SUPABASE_URL não configurado como variável de ambiente!")
if not SUPABASE_KEY:
    print("Erro: SUPABASE_KEY não configurado como variável de ambiente!")

