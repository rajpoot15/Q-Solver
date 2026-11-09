import io
import os
import time
from google import genai
from google.genai.errors import APIError
from PIL import Image
import telebot

# Use your actual tokens here
API_KEY = "AQ.Ab8RN6JbC6QStwtuAlgGeymZERLYWO271rcYrH-W5enyQnfAwA"
BOT_TOKEN = "8974738687:AAEtHG9I6dDvIqTJpO1TF276ImtmXhFiMqI"

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)


def log_message(message):
  # Safely check and log locally if path exists
  log_path = "/sdcard/Documents/chat_logs.txt"
  try:
    user_name = message.from_user.first_name
    user_handle = (
        message.from_user.username if message.from_user.username else "NoUsername"
    )
    user_id = message.from_user.id

    if message.text:
      content = message.text
    elif message.caption:
      content = f"[Photo/Media with caption: {message.caption}]"
    elif message.content_type == "photo":
      content = "[Photo without caption]"
    elif message.content_type == "sticker":
      content = "[Sticker]"
    else:
      content = f"[{message.content_type}]"

    log_entry = (
        f"User: {user_name} (@{user_handle}) | ID: {user_id} | Msg: {content}\n"
    )

    with open(log_path, "a", encoding="utf-8") as f:
      f.write(log_entry)
  except Exception:
    pass


def generate_with_retry(contents, max_retries=3):
  """Helper function to retry requests if the API returns a 503/Unavailable error."""
  delay = 2
  for attempt in range(max_retries):
    try:
      return client.models.generate_content(
          model="gemini-2.5-flash", contents=contents
      )
    except APIError as e:
      if e.code == 503 or "UNAVAILABLE" in str(e):
        if attempt < max_retries - 1:
          time.sleep(delay)
          delay *= 2  # Exponential backoff (2s, 4s, 8s)
          continue
      raise e


@bot.message_handler(content_types=["text", "photo", "sticker"])
def handle_message(message):
  log_message(message)

  try:
    if message.text:
      bot.send_chat_action(message.chat.id, "typing")
      response = generate_with_retry(message.text)
      bot.reply_to(message, response.text)

    elif message.photo:
      bot.send_chat_action(message.chat.id, "upload_photo")
      file_id = message.photo[-1].file_id
      file_info = bot.get_file(file_id)
      downloaded_file = bot.download_file(file_info.file_path)
      img = Image.open(io.BytesIO(downloaded_file))

      prompt = (
          message.caption
          if message.caption
          else "Solve this problem step-by-step:"
      )
      response = generate_with_retry([prompt, img])
      bot.reply_to(message, response.text)

  except APIError as e:
    if e.code == 503 or "UNAVAILABLE" in str(e):
      bot.reply_to(
          message,
          "⚠️ The AI model is currently experiencing high demand. Please try"
          " again in a few seconds.",
      )
    else:
      bot.reply_to(message, f"API Error: {e.message}")
  except Exception as e:
    bot.reply_to(message, f"Error: {str(e)}")


print("Bot is running...")
bot.polling(none_stop=True)
                 
