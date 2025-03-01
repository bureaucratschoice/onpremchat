#!/usr/bin/env python3
from typing import List, Tuple, Optional
from nicegui import app, context, ui, events, Client
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
import time
from uuid import uuid4
import json

# --- Modelldefinitionen ---
class InputText:
    def __init__(self):
        self.text = ""

inputText = InputText()

class PDFReady:
    def __init__(self):
        self.ready = False
        self.answered = False
        self.ready_to_upload = True

def assign_uuid_if_missing():
    if not 'chat_job' in app.storage.user or not app.storage.user['chat_job']:
        app.storage.user['chat_job'] = uuid4()
    if not 'pdf_job' in app.storage.user or not app.storage.user['pdf_job']:
        app.storage.user['pdf_job'] = uuid4()
    if not 'pdf_ready' in app.storage.user or not app.storage.user['pdf_ready']:
        app.storage.user['pdf_ready'] = {'ready': False, 'answered': False, 'ready_to_upload': True}

'''Authentication for management tasks via SUPERTOKEN'''
passwords = {'mngmt': os.getenv('SUPERTOKEN', default="PLEASE_CHANGE_THIS_PLEASE")}
unrestricted_page_routes = {'/login','/','/chat','/pdf'}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path in Client.page_routes.values() and request.url.path not in unrestricted_page_routes:
                app.storage.user['referrer_path'] = request.url.path  # merken, wo der User hinwollte
                return RedirectResponse('/login')
        return await call_next(request)

app.add_middleware(AuthMiddleware)
'''End of Authentication'''

# --- Moderne CSS-Styles einbinden ---
def setup_styles():
    ui.add_head_html('''
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap">
    <style>
        body {
            font-family: 'Roboto', sans-serif;
            background-color: #f5f7fa;
            color: #333;
            margin: 0;
            padding: 0;
        }
        /* Header & Navigation */
        .header {
            background: linear-gradient(90deg, #1e88e5, #1565c0);
            color: #fff;
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header img {
            height: 50px;
        }
        .nav-link {
    margin: 0 1rem;
    text-decoration: none;
    font-weight: 500;
    color: #000; /* Changed from white to black */
    transition: background-color 0.3s, color 0.3s;
    padding: 0.25rem 0.5rem; /* Added padding to better show the grey box */
}

.nav-link:hover {
    background-color: #ccc; /* Adds a grey background on hover */
    color: #000; /* Keeps the text black */
}

        /* Link Drawer */
        .left-drawer {
            background-color: #fff;
            border-right: 1px solid #ddd;
            padding: 1rem;
        }
        /* Container Cards für Chat und PDF */
        .chat-container, .pdf-container, .card {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            padding: 2rem;
            margin: 2rem auto;
            max-width: 800px;
        }
      /* Für gesendete Nachrichten (sent=True) */
  .q-chat-message--sent .q-chat-message__bubble {
    background-color: #4CAF50;  /* Beispiel: grün */
  }

  /* Für empfangene Nachrichten (sent=False) */
  .q-chat-message:not(.q-chat-message--sent) .q-chat-message__bubble {
    background-color: #f1f1f1;  /* Beispiel: hellgrau */
  }
        /* Footer */
        .footer {
            background-color: #fff;
            padding: 1rem 2rem;
            box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 2rem;
        }
        /* Inputs & Buttons */
        input, textarea {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 0.75rem;
            width: 100%;
        }
        button {
            background-color: #1e88e5;
            border: none;
            color: #fff;
            border-radius: 4px;
            padding: 0.75rem 1.5rem;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #1565c0;
        }
        /* Tabs */
        .tabs {
            margin-bottom: 1rem;
        }
        /* Überschriften in den Cards */
        .card h1, .card h2, .card h3 {
            margin-bottom: 1rem;
            text-align: center;
        }
    </style>
    ''')



# --- Hauptinitialisierung ---
def init(fastapi_app: FastAPI, jobStat, taskQueue, cfg, statistic) -> None:
    assi = os.getenv('ASSISTANT', default=cfg.get_config('frontend','assistant', default="Assistent:in"))
    you = os.getenv('YOU', default=cfg.get_config('frontend','you', default="Sie"))
    greeting = os.getenv('GREETING', default=cfg.get_config('frontend','chat-greeting', default="Achtung, prüfen Sie jede Antwort vor Weiterverwendung. Warteschlange: "))
    pdf_greeting = os.getenv('PDFGREETING', default=cfg.get_config('frontend','pdf-greeting', default="Laden Sie ein PDF hoch, um Fragen zu stellen. Warteschlange: "))
    pdf_processed = os.getenv('PDFPROC', default=cfg.get_config('frontend','pdf-preprocessing', default="Ihr PDF wird verarbeitet. Status: "))
    
    # --- Navigation & Header ---
    def navigation():
        setup_styles()  # Einmaliges Einbinden der Styles
        title = os.getenv('APP_TITLE', default="MWICHT")
        ui.page_title(title)
        with ui.header().classes("header") as header:
            with ui.row():
                ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat').classes('text-white')
            with ui.row():
                ui.image('/app/static/logo.jpeg')
        with ui.left_drawer().classes("left-drawer") as left_drawer:
            ui.link("Home", home).classes("nav-link")
            tochat = os.getenv('TOCHAT', default="Zum Chat")
            ui.link(tochat, show).classes("nav-link")
            topdf = os.getenv('TOPDF', default="Zu den PDF-Werkzeugen")
            ui.link(topdf, pdfpage).classes("nav-link")

    # --- Chatseite ---
    @ui.page('/chat')
    def show():
        timer = ui.timer(1.0, lambda: chat_messages.refresh())
        assign_uuid_if_missing()

        @ui.refreshable
        def chat_messages() -> None:
            assign_uuid_if_missing()
            messages: List[Tuple[str, str]] = []
            messages.append((assi, greeting + str(jobStat.count_queued_jobs())))
            answers = []
            questions = []
            status = jobStat.get_job_status(app.storage.browser['id'], app.storage.user['chat_job'])
            if status.get('job_type') == 'chat':
                answers = status.get('answer', [])
                questions = status.get('prompt', [])
            i_q = i_a = 0
            while i_q < len(questions):
                messages.append((you, questions[i_q]))
                if i_a < len(answers):
                    messages.append((assi, answers[i_a]))
                i_q += 1
                i_a += 1

            # Render each message with improved styling
            for name, text in messages:
                if name == you:
                    # User messages: light background, dark text, right-aligned
                    ui.chat_message(
                        text=text,
                        name=name,
                        sent=True
                    )#.classes("bg-gray-200 text-black rounded-lg p-2 m-1 max-w-xs self-end")
                else:
                    # Assistant messages: colored background, white text, left-aligned
                    ui.chat_message(
                        text=text,
                        name=name,
                        sent=False
                    )#.classes("bg-blue-500 text-white rounded-lg p-2 m-1 max-w-xs self-start")

            if status.get('status') == 'processing':
                timer.activate()
                ui.spinner(size='3rem').classes('self-center')
            else:
                timer.activate()
                if status.get('status') == 'finished':
                    timer.deactivate()
            if context.client.has_socket_connection:
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

        def delete_chat() -> None:
            assign_uuid_if_missing()
            jobStat.remove_job(app.storage.browser['id'], app.storage.user['chat_job'])
            app.storage.user['text'] = ""
            app.storage.user['chat_job'] = uuid4()
            chat_messages.refresh()

        def copy_data():
            status = jobStat.get_job_status(app.storage.browser['id'], app.storage.user['chat_job'])
            if 'answer' in status:
                text = status['answer'][-1]
                ui.run_javascript('navigator.clipboard.writeText(`' + text + '`)', timeout=5.0)

        async def send() -> None:
            statistic.addEvent('chat')
            assign_uuid_if_missing()
            message = app.storage.user['text']
            text.value = ''
            jobStat.add_job(
                app.storage.browser['id'],
                app.storage.user['chat_job'],
                message,
                custom_config=False,
                job_type='chat'
            )
            job = {'token': app.storage.browser['id'], 'uuid': app.storage.user['chat_job']}
            try:
                taskQueue.put(job)
            except:
                jobStat.update_status(app.storage.browser['id'], app.storage.user['chat_job'], "failed")
            timer.activate()
            chat_messages.refresh()

        navigation()
        # Adjust container styling
        ui.query('.q-page').classes('flex')
        ui.query('.nicegui-content').classes('w-full')

        # Chat-Container: Enthält sowohl die Chat-Nachrichten als auch die Eingabemaske
        with ui.card().classes("chat-container p-8 shadow-lg rounded-lg bg-white"):
            chat_messages()
            # Eingabemaske direkt am Ende des Chat-Verlaufs
            with ui.row().classes("w-full items-center space-x-2 mt-4"):
                placeholder = 'message'
                text = ui.textarea(
                    placeholder=placeholder
                ).props('rounded outlined clearable') \
                    .classes("w-full flex-1") \
                    .bind_value(app.storage.user, 'text') \
                    .on('keydown.enter', send)
                ui.button(icon="send", on_click=send)
                ui.button(icon="content_copy", on_click=copy_data)
                ui.button(icon="delete_forever", on_click=delete_chat)

    # --- Home-Seite ---
    @ui.page('/')
    def home():
        navigation()
        statistic.addEvent('visit')
        title = os.getenv('APP_TITLE', default=cfg.get_config('frontend','app_title', default="MWICHT"))
        with ui.column().classes('absolute-center'):
            ui.markdown(f"# Willkommen bei {title}").classes('text-center text-3xl font-bold mb-4')
            with ui.row().classes('justify-center gap-4'):
                ui.image('/app/static/home_background1.jpeg').classes('w-40 h-40 rounded-full shadow')
                ui.image('/app/static/home_background2.jpeg').classes('w-40 h-40 rounded-full shadow')
            with ui.row().classes('justify-center gap-4 mt-4'):
                ui.image('/app/static/home_background3.jpeg').classes('w-40 h-40 rounded-full shadow')
                ui.image('/app/static/home_background4.jpeg').classes('w-40 h-40 rounded-full shadow')
    
    # --- Management-Seite ---
    @ui.page('/management')
    def mngmt():
        navigation()
        with ui.column().classes("card"):
            ui.button(on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')), icon='logout').props('outline round')
            ui.markdown("Du kannst hier **.jpeg**-Dateien hochladen, um das Aussehen anzupassen.")
            ui.markdown("Für das **Logo** bitte die Datei `logo.jpeg` hochladen.")
            ui.markdown("Für die **Hintergrundbilder** bitte `home_background[1-4].jpeg` verwenden.")
            ui.upload(on_upload=handle_upload, multiple=False, label='Upload JPEG', max_file_size=9048576).props('accept=.jpeg')
    
    # --- Statistik-Seite ---
    @ui.page('/statistic')
    def statistics():
        navigation()
        categories = ['visit', 'chat', 'pdf_question', 'pdf_summary', 'max_queue']
        with ui.column().classes("card"):
            ui.button(on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')), icon='logout').props('outline round')
            for c in categories:
                ui.label(c).classes("font-medium")
                dates, values = statistic.getEventStat(c)
                columns = [
                    {'name': 'date', 'label': 'Date', 'field': 'date', 'required': True, 'align': 'left'},
                    {'name': 'value', 'label': c, 'field': 'value', 'sortable': True},
                ]
                rows = []
                for d, v in zip(dates, values):
                    rows.append({'date': d, 'value': v})
                ui.table(columns=columns, rows=rows, row_key='name')
    

        

    @ui.page('/pdf')
    def pdfpage():

    #TODO: Add jobtypes. Distiguish pdf_processing from pdf_chat
        pdfmessages: List[Tuple[str, str]] = [] 
        thinking: bool = False
        timer = ui.timer(1.0, lambda: pdf_messages.refresh())
        assign_uuid_if_missing()
        pdf_ready = app.storage.user['pdf_ready']
        @ui.refreshable
        def pdf_messages() -> None:
            assign_uuid_if_missing()
            pdfmessages: List[Tuple[str, str]] = [] 
            pdfmessages.append((assi, pdf_greeting + str(jobStat.count_queued_jobs())))
            answers = []
            questions = []
            status = jobStat.get_job_status(app.storage.browser['id'],app.storage.user['pdf_job'])
            if 'job_type' in status and status['job_type'] == 'pdf_processing' and 'status' in status:
                pdfmessages.append((assi, pdf_processed + str(status['status'])))
                if not status['status'] == 'finished':
                    pdf_ready['ready'] = False
                    
                else:
                    pdf_ready['ready'] = True
                    pdf_ready['answered'] = True
                    

            if 'job_type' in status and status['job_type'] == 'pdf_chat':
                if 'status' in status and status['status'] == 'finished':
                    pdf_ready['answered'] = True
                else:
                    
                    pdf_ready['answered'] = False
                if 'prompt' in status:
                    questions = status['prompt']
                if 'answer' in status:
                    answers = status['answer']

                
            
            if 'job_type' in status and status['job_type'] == 'pdf_summarize':
                if 'status' in status and status['status'] == 'finished':
                    pdf_ready['answered'] = True
                else:
                    pdf_ready['answered'] = False
                if 'answer' in status:
                    answers = status['answer']
            i_q = 0
            i_a = 0
            output_fin = False
            while not output_fin:
                if i_q < len(questions):
                    if questions[i_q]:
                        pdfmessages.append((you,questions[i_q]))
                        i_q += 1
                    else:
                        i_q += 1
                        continue
                if i_a < len(answers):
                    if answers[i_a]:
                        pdfmessages.append((assi,answers[i_a]))
                        i_a += 1
                    else:
                        i_a += 1
                        continue
                if i_q >= len(questions) and i_a >= len(answers):
                    output_fin = True
            
            for name, text in pdfmessages:
                ui.chat_message(text=text, name=name, sent=name == you)
                
            if 'status' in status:
                if status['status'] == 'processing':
                    thinking = True
                    timer.activate()
                    
                else:
                    thinking = False
                    timer.activate()
                if status['status'] == 'finished':
                    timer.deactivate()
            
            else:
                thinking = False
                timer.activate()
            if thinking:
                ui.spinner(size='3rem').classes('self-center')
            if context.client.has_socket_connection:
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
            app.storage.user['pdf_ready'] = pdf_ready

        def delete_chat() -> None:
            assign_uuid_if_missing()
            jobStat.remove_job(app.storage.browser['id'],app.storage.user['pdf_job'])
            app.storage.user['pdf_question'] = ""
            app.storage.user['pdf_job'] = uuid4()
            pdf_ready['ready'] = False
            pdf_ready['answered'] = False
            pdf_ready['ready_to_upload'] = True
            app.storage.user['pdf_ready'] = pdf_ready
            pdf_messages.refresh()

        def copy_data():
            if 'answer' in jobStat.get_job_status(app.storage.browser['id'],app.storage.user['pdf_job']):
                text = jobStat.get_job_status(app.storage.browser['id'],app.storage.user['pdf_job'])['answer'][-1]
                ui.run_javascript('navigator.clipboard.writeText(`' + text + '`)', timeout=5.0)

        async def send() -> None:
            statistic.addEvent('pdf_question')
            assign_uuid_if_missing()
            message = app.storage.user['pdf_question']
            #custom_config = {'temperature':app.storage.user['temperature']/100,'max_tokens':app.storage.user['max_tokens'],'top_k':app.storage.user['top_k'],'top_p':app.storage.user['top_p']/100,'repeat_penalty':app.storage.user['repeat_penalty']/100}
            text.value = ''
            jobStat.add_job(app.storage.browser['id'],app.storage.user['pdf_job'],message,job_type = 'pdf_chat' )
            job = {'token':app.storage.browser['id'],'uuid':app.storage.user['pdf_job']}
            try:
                taskQueue.put(job)
                
            except:
                jobStat.update_status(app.storage.browser['id'],app.storage.user['pdf_job'],"failed") 

            timer.activate()
            pdf_messages.refresh()

        def summarize_pdf() -> None:
            statistic.addEvent('pdf_summary')
            assign_uuid_if_missing()
            jobStat.add_job(app.storage.browser['id'],app.storage.user['pdf_job'],"",job_type = 'pdf_summarize' )
            job = {'token':app.storage.browser['id'],'uuid':app.storage.user['pdf_job']}
            try:
                taskQueue.put(job)
                
            except:
                jobStat.update_status(app.storage.browser['id'],app.storage.user['pdf_job'],"failed") 

            timer.activate()
            pdf_messages.refresh()

        def handle_upload(event: events.UploadEventArguments):
            assign_uuid_if_missing()
            fileid = app.storage.browser['id']
            with event.content as f:
                
                filepath = f'/tmp/{fileid}/{event.name}'
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file = open(filepath, 'wb')
                for line in f.readlines():
                    file.write(line)
                file.close()
            jobStat.add_job(app.storage.browser['id'],app.storage.user['pdf_job'],prompt = '',custom_config = False,job_type = 'pdf_processing' )
            job = {'token':app.storage.browser['id'],'uuid':app.storage.user['pdf_job'],'filepath':filepath}
            try:
                taskQueue.put(job)
                pdf_ready['ready'] = False
                pdf_ready['answered'] = False
            except:
                jobStat.update_status(app.storage.browser['id'],app.storage.user['pdf_job'],"failed") 
            pdf_ready['ready_to_upload'] = False
            timer.activate()
            pdf_messages.refresh()

        navigation()
        
        # the queries below are used to expand the contend down to the footer (content can then use flex-grow to expand)
        ui.query('.q-page').classes('flex')
        ui.query('.nicegui-content').classes('w-full')
        
        with ui.card():
            pdf_messages()

            ui.upload(on_upload=handle_upload,multiple=True,label='Upload Files',max_total_size=90485760000).props('accept=".pdf,.docx,.csv"').classes('max-w-full').bind_visibility_from(pdf_ready,'ready_to_upload')

            with ui.row().classes("w-full items-center mt-4"):
                placeholder = 'message'
                text = ui.textarea(
                    placeholder=placeholder
                ).props('rounded outlined clearable').classes("w-full flex-1") \
                .bind_value(app.storage.user, 'pdf_question') \
                .on('keydown.enter', send) \
                .bind_visibility_from(pdf_ready, 'ready')
                ui.button(icon="send", on_click=send).bind_visibility_from(pdf_ready, 'ready')
                ui.button("summarize pdf", on_click=summarize_pdf).bind_visibility_from(pdf_ready, 'ready')
                ui.button(icon="content_copy", on_click=copy_data)
                ui.button(icon="delete_forever", on_click=delete_chat)




    ui.run_with(
        fastapi_app,
        storage_secret=uuid4(),
    )
