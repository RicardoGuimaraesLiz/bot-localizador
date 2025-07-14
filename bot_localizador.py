import logging
from datetime import datetime, timezone
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,  # Ajuste aqui
    ConversationHandler,
    CallbackContext,
)
from config import BOT_TOKEN
from supabase_utils import enviar_interacao_supabase, salvar_resposta_followup
from dados_dinamicos import (
    obter_familias_ativas,
    obter_skus_por_familia,
    obter_bairros_por_sku,
    obter_pontos_venda,
)

# Configuração do logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Estados da conversa
TELEFONE, FAMILIA, SKU, BAIRRO = range(4)
FOLLOWUP_NOTA, FOLLOWUP_MOTIVO = range(10, 12)

# Funções do bot (não alteradas)

def main():
    # Substituindo Updater por Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    dp = application.dispatcher

    # Conversa principal
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TELEFONE: [MessageHandler(filters.Contact | filters.Text & ~filters.COMMAND, receber_telefone)],
            FAMILIA: [MessageHandler(filters.Text & ~filters.COMMAND, escolher_familia)],
            SKU: [MessageHandler(filters.Text & ~filters.COMMAND, escolher_sku)],
            BAIRRO: [MessageHandler(filters.Text & ~filters.COMMAND, receber_bairro)],
        },
        fallbacks=[CommandHandler("cancel", cancelar)],
    )

    # Handler de follow-up separado
    followup_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(Sim|sim|Não|não|nao)$"), followup_resposta)],
        states={
            FOLLOWUP_NOTA: [MessageHandler(filters.Text & ~filters.COMMAND, followup_nota)],
            FOLLOWUP_MOTIVO: [MessageHandler(filters.Text & ~filters.COMMAND, followup_motivo)],
        },
        fallbacks=[CommandHandler("cancel", cancelar)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(followup_handler)

    logging.info("🤖 Bot rodando... Pressione Ctrl+C para parar.")
    application.run_polling()

if __name__ == "__main__":
    main()
