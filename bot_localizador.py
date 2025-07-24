import logging
from datetime import datetime, timezone
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
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


async def start(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [[KeyboardButton("📞 Enviar meu telefone", request_contact=True)]]
    await update.message.reply_text(
        "👋 Olá! Antes de começarmos, por favor informe seu número de telefone:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return TELEFONE


import re  # certifique-se de ter isso no topo

async def receber_telefone(update: Update, context: CallbackContext) -> int:
    # Prioriza o número do botão, se não, usa texto manual
    telefone = update.message.contact.phone_number if update.message.contact else update.message.text.strip()

    # Remove caracteres não numéricos
    telefone_limpo = re.sub(r'\D', '', telefone)

    # Validação simples: mínimo 9 dígitos
    if len(telefone_limpo) < 9:
        await update.message.reply_text("❗ Telefone inválido. Envie no formato 11999999999 ou use o botão.")
        return TELEFONE

    # Salvar dados no contexto
    user = update.effective_user
    context.user_data["cliente_id"] = user.username or str(user.id)
    context.user_data["telefone"] = telefone_limpo
    context.user_data["canal"] = "Telegram"
    context.user_data["origem_link"] = "Campanha Bot"
    context.user_data["data_hora_contato"] = datetime.now(timezone.utc).isoformat()

    # Pede a família de produtos
    familias = obter_familias_ativas()
    reply_keyboard = [familias[i:i+2] for i in range(0, len(familias), 2)]

    await update.message.reply_text(
        "Por favor, selecione a *família de produtos*:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown",
    )
    return FAMILIA



async def escolher_familia(update: Update, context: CallbackContext) -> int:
    familia = update.message.text
    context.user_data["familia_produto"] = familia

    skus = obter_skus_por_familia(familia)
    if not skus:
        await update.message.reply_text("Ops, não encontramos SKUs para essa família. Por favor, escolha outra.")
        return FAMILIA

    reply_keyboard = [skus[i:i+2] for i in range(0, len(skus), 2)]
    await update.message.reply_text(
        f"Você escolheu: *{familia}*\nAgora selecione o *SKU*:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown",
    )
    return SKU


async def escolher_sku(update: Update, context: CallbackContext) -> int:
    sku = update.message.text
    context.user_data["sku"] = sku

    bairros = obter_bairros_por_sku(sku)
    if not bairros:
        await update.message.reply_text("Ops, não encontramos bairros para esse SKU. Por favor, escolha outro SKU.")
        return SKU

    reply_keyboard = [bairros[i:i+2] for i in range(0, len(bairros), 2)]
    await update.message.reply_text(
        "📍 Agora selecione o *bairro* onde você está localizado:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown",
    )
    return BAIRRO


async def receber_bairro(update: Update, context: CallbackContext) -> int:
    bairro = update.message.text
    context.user_data["bairro"] = bairro

    sku = context.user_data.get("sku")
    pontos = obter_pontos_venda(sku, bairro)
    context.user_data["pontos_venda_retorno"] = pontos

    lista_pontos = "\n".join(f"✅ {p}" for p in pontos) if pontos else "Nenhum ponto de venda encontrado."

    await update.message.reply_text(
        f"Encontramos os seguintes pontos de venda no bairro *{bairro}*:\n\n"
        f"{lista_pontos}\n\n"
        f"Obrigado por utilizar nosso localizador! 😊",
        parse_mode="Markdown",
    )

    try:
        interacao_id = enviar_interacao_supabase(context.user_data)
        context.user_data["interacao_id"] = interacao_id
        logging.info(f"Interação salva no Supabase com ID: {interacao_id}")
    except Exception as e:
        logging.error(f"Erro ao enviar dados para Supabase: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao registrar sua interação.")

    # Agendar mensagem de follow-up (1 minuto para testes)
    # CORREÇÃO: Usar 'data' em vez de 'context' para passar os dados para o job
    context.job_queue.run_once(enviar_followup, when=60, data={
        "chat_id": update.effective_chat.id,
        "interacao_id": context.user_data.get("interacao_id"),
    })

    return ConversationHandler.END


async def enviar_followup(context: CallbackContext):
    job_data = context.job.data # Acessar os dados do job via .data
    chat_id = job_data["chat_id"]

    keyboard = [["Sim", "Não"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Olá! Você encontrou o produto que estava procurando?",
        reply_markup=reply_markup,
    )


async def followup_resposta(update: Update, context: CallbackContext) -> int:
    resposta = update.message.text.lower()
    context.user_data["interacao_id"] = context.user_data.get("interacao_id") or "SEM_ID"
    context.user_data["encontrou_produto"] = True if resposta == "sim" else False

    if resposta == "sim":
        keyboard = [[str(i)] for i in range(11)]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("De 0 a 10, qual nota você dá para o produto?", reply_markup=reply_markup)
        return FOLLOWUP_NOTA

    elif resposta in ["não", "nao"]:
        keyboard = [["Produto não encontrado"], ["Preço"], ["Outro"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Qual foi o motivo?", reply_markup=reply_markup)
        return FOLLOWUP_MOTIVO

    await update.message.reply_text("Resposta inválida. Por favor, responda com Sim ou Não.")
    return ConversationHandler.END


async def followup_nota(update: Update, context: CallbackContext) -> int:
    try:
        nota = int(update.message.text)
        context.user_data["nota_produto"] = nota
        context.user_data["motivo_nao_encontrou"] = None
    except ValueError:
        await update.message.reply_text("Por favor, envie um número de 0 a 10.")
        return FOLLOWUP_NOTA

    salvar_resposta_followup(context.user_data)
    await update.message.reply_text("✅ Obrigado pelo seu feedback! Até a próxima.")
    return ConversationHandler.END


async def followup_motivo(update: Update, context: CallbackContext) -> int:
    motivo = update.message.text
    context.user_data["nota_produto"] = None
    context.user_data["motivo_nao_encontrou"] = motivo

    salvar_resposta_followup(context.user_data)
    await update.message.reply_text("✅ Obrigado pelo seu feedback! Vamos trabalhar para melhorar.")
    return ConversationHandler.END


async def cancelar(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "❌ Conversa cancelada.\n\n"
        "Se quiser começar de novo, digite /start.\n"
        "Se tiver dúvidas, digite /ajuda."
    )
    return ConversationHandler.END

async def ajuda(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "👋 *Olá! Eu sou o Bot Localizador de Produtos.*\n\n"
        "🛒 Te ajudo a encontrar onde comprar produtos por região.\n"
        "📍 Você seleciona a categoria, o produto e o bairro, e eu te mostro os pontos de venda mais próximos.\n\n"
        "📊 Depois, pergunto se encontrou o produto e sua opinião — isso ajuda a empresa a melhorar.\n\n"
        "✅ Use o comando /start para começar.\n"
        "❌ Use /cancel para parar a qualquer momento.",
        parse_mode="Markdown"
    )

def main():
    # Usando Application para rodar o bot
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversa principal
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TELEFONE: [MessageHandler(filters.CONTACT | filters.TEXT & ~filters.COMMAND, receber_telefone)],
            FAMILIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, escolher_familia)],
            SKU: [MessageHandler(filters.TEXT & ~filters.COMMAND, escolher_sku)],
            BAIRRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_bairro)],
        },
        fallbacks=[CommandHandler("cancel", cancelar)],
    )

    # Handler de follow-up separado
    followup_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(Sim|sim|Não|não|nao)$"), followup_resposta)],
        states={
            FOLLOWUP_NOTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, followup_nota)],
            FOLLOWUP_MOTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, followup_motivo)],
        },
        fallbacks=[CommandHandler("cancel", cancelar)],
    )

    # Adicionando handlers diretamente à application
    application.add_handler(conv_handler)
    application.add_handler(followup_handler)
    application.add_handler(CommandHandler("ajuda", ajuda))


    logging.info("🤖 Bot rodando... Pressione Ctrl+C para parar.")
    application.run_polling()


from flask_server import keep_alive

if __name__ == "__main__":
    keep_alive()  # Manter serviço vivo no Render
    main()