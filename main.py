import telebot
import configparser
import os
import json
import datetime

from openai import OpenAI
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def calender_bot():
    class ExHandler(telebot.ExceptionHandler):
        def handle(self, error):
            print('Error: ', error)
            return True
    
    dir_path = (os.path.dirname(__file__))
    print("Started at: ", dir_path)

    config = configparser.ConfigParser()
    config.read(f'{dir_path}/settings.ini')

    MODEL_NAME = config['General']['model_name']
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    allowed_users = list(map(int, config['General']['allowed_users'].split(',')))
    bot = telebot.TeleBot(config['General']['token'], exception_handler=ExHandler())
    
    openai_client = OpenAI(
    api_key=config['General']['gemini_key'],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    def get_calendar_service():
        """Авторизация в Google и получение сервиса Календаря."""
        creds = None
        if os.path.exists(f'{dir_path}/token.json'):
            creds = Credentials.from_authorized_user_file(f'{dir_path}/token.json', SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(f'{dir_path}/credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open(f'{dir_path}/token.json', 'w') as token:
                token.write(creds.to_json())
                
        return build('calendar', 'v3', credentials=creds)
    
    def add_calendar_event(summary, start_time, end_time, description=""):
        """Создает событие в календаре."""
        try:
            service = get_calendar_service()
            event = {
                'summary': summary,
                'description': description,
                'start': {'dateTime': start_time, 'timeZone': 'UTC+3'},
                'end': {'dateTime': end_time, 'timeZone': 'UTC+3'},
            }
            event_result = service.events().insert(calendarId='primary', body=event).execute()
            return f"Событие создано успешно. Ссылка: {event_result.get('htmlLink')}"
        except Exception as e:
            return f"Не удалось добавить событие. Ошибка: {str(e)}"

    def get_calendar_events(start_time, end_time):
        """Считывает события за интервал времени."""
        try:
            service = get_calendar_service()
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            if not events:
                return "Событий на указанный период не обнаружено."
            
            events_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                events_list.append(f"- {start}: {event.get('summary')} (Описание: {event.get('description', 'нет')})")
            return "\n".join(events_list)
        except Exception as e:
            return f"Не удалось получить события. Ошибка: {str(e)}"
        
    tools = [
        {
            "type": "function",
            "function": {
                "name": "add_calendar_event",
                "description": "Добавляет новое событие в Google Календарь.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Название встречи (например, 'Прием у стоматолога')"},
                        "start_time": {"type": "string", "description": "Время начала в формате ISO 8601 (например, '2026-06-03T14:00:00+03:00')"},
                        "end_time": {"type": "string", "description": "Время окончания в формате ISO 8601 (например, '2026-06-03T15:00:00+03:00')"},
                        "description": {"type": "string", "description": "Дополнительное описание события (необязательно)"}
                    },
                    "required": ["summary", "start_time", "end_time"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_calendar_events",
                "description": "Получает список запланированных дел из Google Календаря на указанный период.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_time": {"type": "string", "description": "Начало периода поиска в формате ISO 8601"},
                        "end_time": {"type": "string", "description": "Конец периода поиска в формате ISO 8601"}
                    },
                    "required": ["start_time", "end_time"]
                }
            }
        }
]

    @bot.message_handler(commands=['start'])
    def start(message):
        if message.from_user.id in allowed_users:
            bot.send_message(message.chat.id, "Привет! Я твой бесплатный ИИ-помощник (на базе Gemini) для работы с Google Календарем.\nНапиши мне, что ты хочешь запланировать или спроси о делах.")
    
    @bot.message_handler(func=lambda message: True)
    def handle_all_messages(message):
        if message.from_user.id not in allowed_users:
            bot.reply_to(message, "Доступ к боту ограничен владельцем.")
            return

        user_text = message.text
        now_str = datetime.datetime.now().astimezone().isoformat()
        
        system_prompt = (
            f"Вы — умный ассистент, управляющий Google Календарем. "
            f"Текущие дата и время: {now_str}. "
            f"Используйте предоставленные инструменты (functions) для работы с расписанием пользователя. "
            f"Если длительность события не указана, планируйте встречу на 1 час. "
            f"Если не указано отдельно, работай в часовом поясе UTC+3"
            f"Отвечайте на русском языке, пол женский, стиль дружелюбный"
        )

        try:
            # 1. Отправляем запрос модели
            response = openai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                tools=tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                # Подготовка истории диалога с вызовом функций
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                    {
                        "role": "assistant",
                        "content": response_message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in tool_calls
                        ]
                    }
                ]
                
                # Выполнение локальных функций
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if function_name == "add_calendar_event":
                        function_response = add_calendar_event(
                            summary=function_args.get("summary"),
                            start_time=function_args.get("start_time"),
                            end_time=function_args.get("end_time"),
                            description=function_args.get("description", "")
                        )
                    elif function_name == "get_calendar_events":
                        function_response = get_calendar_events(
                            start_time=function_args.get("start_time"),
                            end_time=function_args.get("end_time")
                        )
                    else:
                        function_response = "Ошибка: Функция не найдена."

                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
                
                # 2. Получение итогового ответа ИИ с учетом результатов работы функций
                final_response = openai_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages
                )
                bot.reply_to(message, final_response.choices[0].message.content)
            else:
                # Обычный ответ, если вызывать функции не потребовалось
                bot.reply_to(message, response_message.content)
                
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка обработки: {str(e)}")

    bot.polling(none_stop=True)


if __name__ == '__main__':
    calender_bot()