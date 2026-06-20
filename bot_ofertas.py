import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
TOKEN_TELEGRAM = "7967185957:AAFTl0q2GoQ0WHkZBQqmFWLz_OjlsiqKnFs"
CARPETA_DESCARGAS = "./descargas_mp3"
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de bienvenida."""
    await update.message.reply_text(
        "🔍 ¡Hola! Escríbeme el nombre de la canción o artista que buscas y te daré opciones para descargar en MP3. 🎵"
    )

def buscar_en_youtube(query: str) -> list:
    """Busca en YouTube y devuelve los primeros 8 resultados usando yt-dlp."""
    import yt_dlp
    opciones = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "extract_flat": True,  # Solo extrae la info rápido sin descargar nada todavía
    }
    
    # Buscamos usando el prefijo ytsearch8: para traer 8 resultados
    with yt_dlp.YoutubeDL(opciones) as ydl:
        resultado = ydl.extract_info(f"ytsearch8:{query}", download=False)
        if "entries" in resultado:
            return list(resultado["entries"])
    return []

async def procesar_busqueda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captura el texto del usuario, busca en YT y genera la botonera."""
    query = update.message.text
    
    # Si por error mandan un link directo, avisamos
    if "youtube.com" in query or "youtu.be" in query:
        await update.message.reply_text("❌ Por favor, escribe solo el nombre de la canción, no el enlace directo.")
        return

    mensaje_espera = await update.message.reply_text(f"🔍 Buscando '{query}' en YouTube...")
    
    # Ejecutar la búsqueda en segundo plano
    loop = asyncio.get_event_loop()
    resultados = await loop.run_in_executor(None, buscar_en_youtube, query)
    
    if not resultados:
        await mensaje_espera.edit_text("❌ No encontré resultados para tu búsqueda. Intenta con otro nombre.")
        return
    
    # Guardamos los resultados temporalmente en la memoria del bot para saber qué links corresponden a qué botones
    context.user_data["resultados_busqueda"] = resultados
    
    # Armamos el texto de la lista
    texto_lista = f"🔍 *{query}*\nResultados 1-{len(resultados)} de YouTube:\n\n"
    botones = []
    fila_actual = []
    
    for i, video in enumerate(resultados, start=1):
        titulo = video.get("title", "Sin título")
        duracion = video.get("duration")
        str_duracion = f" [{int(duracion)//60}:{int(duracion)%60:02d}]" if duracion else ""
        
        # Agregamos la línea al texto que verá el usuario
        texto_lista += f"{i}. {titulo}{str_duracion}\n"
        
        # Creamos el botón interactivo para este número
        # El callback_data guarda el índice del video (ej: "descargar_0", "descargar_1")
        boton = InlineKeyboardButton(text=str(i), callback_data=f"descargar_{i-1}")
        fila_actual.append(boton)
        
        # Hacemos filas de 4 botones
        if i % 4 == 0 or i == len(resultados):
            botones.append(fila_actual)
            fila_actual = []
            
    # Agregar botón de cancelar al final (opcional)
    botones.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_busqueda")])
    
    reply_markup = InlineKeyboardMarkup(botones)
    
    # Editamos el mensaje de espera con la lista final y los botones
    await mensaje_espera.edit_text(texto_lista, reply_markup=reply_markup, parse_mode="Markdown")

def descargar_video_a_mp3(url: str, carpeta: str) -> str:
    """Descarga el audio real del video elegido."""
    import yt_dlp
    os.makedirs(carpeta, exist_ok=True)
    opciones = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(carpeta, "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
    }
    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        return f"{base}.mp3"

async def clicks_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las acciones cuando el usuario presiona los botones numéricos."""
    query = update.callback_query
    await query.answer() # Avisa a Telegram que el click fue recibido
    
    data = query.data
    
    if data == "cancelar_busqueda":
        await query.message.edit_text("❌ Búsqueda cancelada.")
        return
        
    if data.startswith("descargar_"):
        indice = int(data.split("_")[1])
        resultados = context.user_data.get("resultados_busqueda", [])
        
        if not resultados or indice >= len(resultados):
            await query.message.reply_text("❌ Error: La sesión expiró. Por favor realiza una nueva búsqueda.")
            return
            
        video_elegido = resultados[indice]
        url_video = f"https://www.youtube.com/watch?v={video_elegid_id}" if (video_elegid_id := video_elegido.get('id')) else video_elegido.get('url')
        titulo_video = video_elegido.get("title", "Audio")
        
        # Notificar que empezó la descarga del botón seleccionado
        mensaje_descarga = await query.message.reply_text(f"⏳ Descargando y convirtiendo: *{titulo_video}*...", parse_mode="Markdown")
        
        try:
            loop = asyncio.get_event_loop()
            archivo_mp3 = await loop.run_in_executor(None, descargar_video_a_mp3, url_video, CARPETA_DESCARGAS)
            
            await mensaje_descarga.edit_text("🚀 Enviando MP3 a Telegram...")
            
            with open(archivo_mp3, 'rb') as audio:
                await query.message.reply_audio(audio=audio, title=os.path.basename(archivo_mp3))
                
            if os.path.exists(archivo_mp3):
                os.remove(archivo_mp3)
                
            await mensaje_descarga.delete()
            
        except Exception as e:
            await mensaje_descarga.edit_text(f"❌ Ocurrió un error al descargar: {e}")

def main():
    """Inicio del bot."""
    if "AQUÍ_PEGA" in TOKEN_TELEGRAM:
        print("❌ ERROR: Olvidaste poner tu Token de Telegram en la línea 10.")
        return

    print("🤖 Bot interactivo de música iniciado...")
    application = Application.builder().token(TOKEN_TELEGRAM).build()

    application.add_handler(CommandHandler("start", start))
    # Escucha el texto para buscar
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_busqueda))
    # Escucha los clicks de los botones en línea
    application.add_handler(CallbackQueryHandler(clicks_botones))

    application.run_polling(connect_timeout=30.0, read_timeout=30.0)

if __name__ == "__main__":
    main()