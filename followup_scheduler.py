import logging
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Bot, ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler, filters, ConversationHandler
)
from config import BOT_TOKEN
# Adicionando obter_pontos_venda e enviar_interacao_supabase à importação
from supabase_utils import buscar_interacoes_para_followup, salvar_resposta_followup, obter_pontos_venda, enviar_interacao_supabase

logging.basicConfig(level=logging.INFO)

AGUARDANDO_RESPOSTA, NOTA_AVALIACAO, MOTIVO_NAO_ENCONTROU = range(3)
interacoes_pendentes = {}

async def verificar_e_enviar_followups(bot: Bot):
    interacoes = buscar_interacoes_para_followup()
    for interacao in interacoes:
        chat_id = interacao["chat_id"]
        interacao_id = interacao["id"]

        if chat_id in interacoes_pendentes:
            continue  # evitar envio duplicado

        try:
            await bot.send_message(
                chat_id=chat_id,
                text="Olá! Você encontrou o produto que estava procurando?"
            )
            interacoes_pendentes[chat_id] = interacao_id
        except Exception as e:
            logging.error(f"Erro ao enviar follow-up para {chat_id}: {e}")

async def start_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    texto = update.message.text.strip().lower()

    if chat_id not in interacoes_pendentes:
        await update.message.reply_text("⚠️ Essa interação já foi registrada ou não é válida.")
        return ConversationHandler.END

    interacao_id = interacoes_pendentes.pop(chat_id)
    context.user_data["interacao_id"] = interacao_id

    if texto in ["sim", "s"]:
        context.user_data["encontrou_produto"] = True
        await update.message.reply_text("✨ Que bom! De 0 a 10, qual a sua nota para o produto?")
        return NOTA_AVALIACAO

    elif texto in ["não", "nao", "n"]:
        context.user_data["encontrou_produto"] = False
        reply_keyboard = [["Produto não disponível", "Preço", "Outro"]]
        await update.message.reply_text(
            "😕 Que pena. Pode nos dizer o motivo?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return MOTIVO_NAO_ENCONTROU

    else:
        await update.message.reply_text("❓ Por favor, responda com *Sim* ou *Não*.")
        return AGUARDANDO_RESPOSTA

async def receber_nota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nota = int(update.message.text.strip())
        if nota < 0 or nota > 10:
            raise ValueError

        context.user_data["nota_produto"] = nota
        context.user_data["data_resposta"] = datetime.utcnow().isoformat()

        salvar_resposta_followup(context.user_data)
        await update.message.reply_text("✅ Obrigado pela sua avaliação!")
    except ValueError:
        await update.message.reply_text("⚠️ Digite apenas um número de 0 a 10.")
        return NOTA_AVALIACAO

    return ConversationHandler.END

async def receber_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    motivo = update.message.text.strip()
    context.user_data["motivo_nao_encontrou"] = motivo
    context.user_data["data_resposta"] = datetime.utcnow().isoformat()

    salvar_resposta_followup(context.user_data)
    await update.message.reply_text("✅ Obrigado pelo seu retorno!")
    return ConversationHandler.END

async def agendador():
    bot = Bot(token=BOT_TOKEN)
    while True:
        await verificar_e_enviar_followups(bot)
        await asyncio.sleep(60)  # verifica a cada 1 minuto

async def receber_bairro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    context.job_queue.run_once(enviar_followup, when=60, data={  # Alteração feita aqui
        "chat_id": update.effective_chat.id,
        "interacao_id": context.user_data.get("interacao_id"),
    })

    return ConversationHandler.END

async def enviar_followup(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.context
    chat_id = job_data["chat_id"]

    keyboard = [["Sim", "Não"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Olá! Você encontrou o produto que estava procurando?",
        reply_markup=reply_markup,
    )

if __name__ == '__main__':
    from telegram.ext import ApplicationBuilder

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & (~filters.COMMAND), start_followup)],
        states={
            AGUARDANDO_RESPOSTA: [MessageHandler(filters.TEXT & (~filters.COMMAND), start_followup)],
            NOTA_AVALIACAO: [MessageHandler(filters.TEXT & (~filters.COMMAND), receber_nota)],
            MOTIVO_NAO_ENCONTROU: [MessageHandler(filters.TEXT & (~filters.COMMAND), receber_motivo)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)

    # Rodar o agendador de follow-up em paralelo com o bot
    asyncio.create_task(agendador())

    app.run_polling()