#!/usr/bin/env python3
from typing import List, Tuple, Optional

from nicegui import app,context, ui, events, Client
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
import time
from uuid import uuid4
import json


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
        app.storage.user['pdf_ready']= {'ready':False,'answered':False,'ready_to_upload':True}


'''Authentication for management tasks via SUPERTOKEN'''
passwords = {'mngmt': os.getenv('SUPERTOKEN',default="PLEASE_CHANGE_THIS_PLEASE")}

unrestricted_page_routes = {'/login','/','/chat','/pdf'}


class AuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path in Client.page_routes.values() and request.url.path not in unrestricted_page_routes:
                app.storage.user['referrer_path'] = request.url.path  # remember where the user wanted to go
                return RedirectResponse('/login')
        return await call_next(request)


app.add_middleware(AuthMiddleware)
'''End of Authentication'''

def init(fastapi_app: FastAPI,jobStat,taskQueue,cfg,statistic) -> None:
    assi = os.getenv('ASSISTANT',default=cfg.get_config('frontend','assistant',default="Assistent:in"))
    you = os.getenv('YOU',default=cfg.get_config('frontend','you',default="Sie"))
    greeting = os.getenv('GREETING',default=cfg.get_config('frontend','chat-greeting',default="Achtung, prüfen Sie jede Antwort bevor Sie diese in irgendeiner Form weiterverwenden. Je länger Ihre Frage ist bzw. je länger der bisherige Chatverlauf, desto länger brauche ich zum lesen. Es kann daher dauern, bis ich anfange Ihre Antwort zu schreiben. Die Länge der Warteschlange ist aktuell: "))
    pdf_greeting = os.getenv('PDFGREETING',default=cfg.get_config('frontend','pdf-greeting',default="Laden Sie ein PDF hoch, damit ich Ihnen Fragen hierzu beantworten kann. Achtung, prüfen Sie jede Antwort bevor Sie diese in irgendeiner Form weiterverwenden. Die Länge der Warteschlange ist aktuell: "))
    pdf_processed = os.getenv('PDFPROC',default=cfg.get_config('frontend','pdf-preprocessing',default="Ihr PDF wird gerade verarbeitet. Der aktuelle Status ist: "))
    
    def navigation():
        anchor_style = r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}'
        ui.add_head_html(f'<style>{anchor_style}</style>')
        title = os.getenv('APP_TITLE',default=cfg.get_config('frontend','app_title',default="MWICHT"))
        ui.page_title(title)
        with ui.header().classes(replace='row items-center') as header:
            
            
            with ui.row():

                ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
            with ui.row():
                ui.image('/app/static/logo.jpeg').classes('w-64 h-32 absolute-right')


                    
                    
                    
        with ui.left_drawer().classes('bg-blue-100') as left_drawer:
            ui.link("Home",home)
            tochat = os.getenv('TOCHAT',default=cfg.get_config('frontend','to_chat',default="Zum Chat"))
            ui.link(tochat, show)
            topdf = os.getenv('TOPDF',default=cfg.get_config('frontend','to_pdf',default="Zu den PDF-Werkzeugen"))
            ui.link(topdf, pdfpage)
        
    @ui.page('/chat')
    
    def show():
        
        messages: List[Tuple[str, str]] = [] 
        thinking: bool = False
        timer = ui.timer(1.0, lambda: chat_messages.refresh())
        assign_uuid_if_missing()
        @ui.refreshable
        def chat_messages() -> None:
            assign_uuid_if_missing()
            messages: List[Tuple[str, str]] = [] 
            messages.append((assi, greeting + str(jobStat.countQueuedJobs())))
            answers = []
            questions = []
            status = jobStat.getJobStatus(app.storage.browser['id'],app.storage.user['chat_job'])
            if 'job_type' in status and status['job_type'] == 'chat' :

                if 'answer' in status:
                    answers = status['answer']
                if 'prompt' in status:
                    questions = status['prompt']
            i_q = 0
            i_a = 0
           
            while i_q < len(questions) and questions[i_q]:

                messages.append((you,questions[i_q]))
                if i_a < len(answers) and answers[i_q]:
                    messages.append((assi,answers[i_q]))
                i_q += 1
                i_a += 1
            for name, text in messages:
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
            if context.get_client().has_socket_connection:
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

        
        def update_response() -> None:
            
            answers = []
            questions = []
            if 'answer' in status:
                answers = status['answer']
            if 'prompt' in status:
                questions = status['prompt']
            

            i_q = 0
            i_a = 0
            
            while i_q < len(questions):
                messages.append((you,questions[i_q]))
                if i_a < len(answers):
                    messages.append((assi,answers[i_q]))
                i_q += 1
                i_a += 1

        def delete_chat() -> None:
            assign_uuid_if_missing()
            jobStat.removeJob(app.storage.browser['id'],app.storage.user['chat_job'])
            app.storage.user['text'] = ""
            app.storage.user['chat_job'] = uuid4()
            chat_messages.refresh()
        
        def copy_data():
            if 'answer' in jobStat.getJobStatus(app.storage.browser['id'],app.storage.user['chat_job']):
                text = jobStat.getJobStatus(app.storage.browser['id'],app.storage.user['chat_job'])['answer'][-1]
                ui.run_javascript('navigator.clipboard.writeText(`' + text + '`)', timeout=5.0)

        def reset_config():
            app.storage.user['temperature'] = os.getenv('TEMPERATURE',default=cfg.get_config('model','temperature',default=0.7))*100
            app.storage.user['max_tokens'] = os.getenv('MAX_TOKENS',default=cfg.get_config('model','max_tokens',default=1024))
            app.storage.user['top_k'] = os.getenv('TOP_K',default=cfg.get_config('model','top_k',default=40))
            app.storage.user['top_p'] = os.getenv('TOP_P',default=cfg.get_config('model','top_p',default=0.8))*100
            app.storage.user['repeat_penalty'] = os.getenv('REPEAT_PENALTY',default=cfg.get_config('model','repeat_penalty',default=1.15))*100

        async def send() -> None:
            statistic.addEvent('chat')
            assign_uuid_if_missing()
            message = app.storage.user['text']
            custom_config = {'temperature':app.storage.user['temperature']/100,'max_tokens':app.storage.user['max_tokens'],'top_k':app.storage.user['top_k'],'top_p':app.storage.user['top_p']/100,'repeat_penalty':app.storage.user['repeat_penalty']/100}
            text.value = ''
            jobStat.addJob(app.storage.browser['id'],app.storage.user['chat_job'],message,custom_config,'chat')
            job = {'token':app.storage.browser['id'],'uuid':app.storage.user['chat_job']}
            try:
                taskQueue.put(job)
            except:
                jobStat.updateStatus(app.storage.browser['id'],app.storage.user['chat_job'],"failed") 

            timer.activate()
            chat_messages.refresh()
            
        navigation()
        # the queries below are used to expand the contend down to the footer (content can then use flex-grow to expand)
        ui.query('.q-page').classes('flex')
        ui.query('.nicegui-content').classes('w-full')
        
        with ui.tabs().classes('w-full') as tabs:
            chat_tab = ui.tab('Chat')

        with ui.tab_panels(tabs, value=chat_tab).classes('w-full max-w-2xl mx-auto flex-grow items-stretch'):
            with ui.tab_panel(chat_tab).classes('items-stretch'):
                
                chat_messages()


        with ui.footer().classes('bg-white'):
            with ui.column().classes('w-full max-w-3xl mx-auto my-6'):
                with ui.row().classes('w-full no-wrap items-center'):
                    placeholder = 'message' 
                    text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
                    .classes('w-full self-center').bind_value(app.storage.user, 'text').on('keydown.enter', send)
                    send_btn = ui.button(icon="send", on_click=lambda: send())
                    copy_btn = ui.button(icon="content_copy", on_click=lambda: copy_data())
                    delete_btn = ui.button(icon="delete_forever", on_click=lambda: delete_chat())
            
                with ui.row().classes('w-full no-wrap items-center'):
                    config_lbl = ui.label('CSS').style('color: #000') 
                    config_lbl.set_text('custom config: ')  
                    v = ui.checkbox('custom config', value=False)
                with ui.row().classes('w-full no-wrap items-center').bind_visibility_from(v, 'value'):
                    temp_lbl = ui.label('CSS').style('color: #000')
                    temp_lbl.set_text('Temperature: ')
                    temp_sld = ui.slider(min=0, max=100, value=os.getenv('TEMPERATURE',default=cfg.get_config('model','temperature',default=0.7))*100).bind_value(app.storage.user, 'temperature')
                    temp_val_lbl = ui.label('CSS').style('color: #000')
                    temp_val_lbl.bind_text_from(app.storage.user, 'temperature', lambda x: x/100)

                with ui.row().classes('w-full no-wrap items-center').bind_visibility_from(v, 'value'):
                    max_tokens_lbl = ui.label('CSS').style('color: #000')
                    max_tokens_lbl.set_text('Max Tokens: ')
                    max_tokens_sld = ui.slider(min=0, max=4096, value=os.getenv('MAX_TOKENS',default=cfg.get_config('model','max_tokens',default=1024))).bind_value(app.storage.user, 'max_tokens')
                    max_tokens_val_lbl = ui.label('CSS').style('color: #000')
                    max_tokens_val_lbl.bind_text_from(app.storage.user, 'max_tokens')

                with ui.row().classes('w-full no-wrap items-center').bind_visibility_from(v, 'value'):
                    top_k_lbl = ui.label('CSS').style('color: #000') 
                    top_k_lbl.set_text('Top k: ')
                    top_k_sld = ui.slider(min=0, max=100, value=os.getenv('TOP_K',default=cfg.get_config('model','top_k',default=40))).bind_value(app.storage.user, 'top_k')
                    top_k_val_lbl = ui.label('CSS').style('color: #000') 
                    top_k_val_lbl.bind_text_from(app.storage.user, 'top_k')

                with ui.row().classes('w-full no-wrap items-center').bind_visibility_from(v, 'value'):
                    top_p_lbl = ui.label('CSS').style('color: #000') 
                    top_p_lbl.set_text('Top p: ')
                    top_p_sld = ui.slider(min=0, max=100, value=os.getenv('TOP_P',default=cfg.get_config('model','top_p',default=0.8))*100).bind_value(app.storage.user, 'top_p')
                    top_p_val_lbl = ui.label('CSS').style('color: #000') 
                    top_p_val_lbl.bind_text_from(app.storage.user, 'top_p',lambda x: x/100)

                with ui.row().classes('w-full no-wrap items-center').bind_visibility_from(v, 'value'):
                    repeat_penalty_lbl = ui.label('CSS').style('color: #000')
                    repeat_penalty_lbl.set_text('Repeat penalty: ')
                    repeat_penalty_sld = ui.slider(min=0, max=200, value=os.getenv('REPEAT_PENALTY',default=cfg.get_config('model','repeat_penalty',default=1.15))*100).bind_value(app.storage.user, 'repeat_penalty')
                    repeat_penalty_val_lbl = ui.label('CSS').style('color: #000') 
                    repeat_penalty_val_lbl.bind_text_from(app.storage.user, 'repeat_penalty',lambda x: x/100)
                
                with ui.row().classes('w-full no-wrap items-center').bind_visibility_from(v, 'value'):                   
                    reset_btn = ui.button(text="reset", on_click=lambda: reset_config())
                
                    
                    

    @ui.page('/')
    def home():
        navigation()
        statistic.addEvent('visit')
        title = os.getenv('APP_TITLE',default=cfg.get_config('frontend','app_title',default="MWICHT"))
        
        with ui.column().classes('absolute-center'):
            with ui.row():
                ui.image('/app/static/home_background1.jpeg').classes('w-60 h-60')
                ui.image('/app/static/home_background2.jpeg').classes('w-60 h-60')
            with ui.row():
                ui.image('/app/static/home_background3.jpeg').classes('w-60 h-60')
                ui.image('/app/static/home_background4.jpeg').classes('w-60 h-60')
            

    @ui.page('/management')
    def mngmt():
        navigation()
        title = os.getenv('APP_TITLE',default=cfg.get_config('frontend','app_title',default="MWICHT"))
        
        
        def handle_upload(event: events.UploadEventArguments):
            assign_uuid_if_missing()
            fileid = app.storage.browser['id']
            with event.content as f:
                
                filepath = f'/app/static/{event.name}'
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file = open(filepath, 'wb')
                for line in f.readlines():
                    file.write(line)
                file.close()
        ui.button(on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')), icon='logout').props('outline round')
        ui.markdown('You can upload **.jpeg** files here to customize the appearance of the application.')
        ui.markdown('For the **logo** rename your upload logo.jpeg.')
        ui.markdown('For the **background** images rename your upload home_background[1-4].jpeg')
        ui.upload(on_upload=handle_upload,multiple=False,label='Upload JPEG',max_file_size=9048576).props('accept=.jpeg').classes('max-w-full')
        

    @ui.page('/login')
    def login() -> Optional[RedirectResponse]:
        def try_login() -> None:  # local function to avoid passing username and password as arguments
            if passwords.get(username.value) == password.value:
                app.storage.user.update({'username': username.value, 'authenticated': True})
                ui.navigate.to(app.storage.user.get('referrer_path', '/'))  # go back to where the user wanted to go
            else:
                ui.notify('Wrong username or password', color='negative')

        if app.storage.user.get('authenticated', False):
            return RedirectResponse('/')
        with ui.card().classes('absolute-center'):
            username = ui.input('Username').on('keydown.enter', try_login)
            password = ui.input('Password', password=True, password_toggle_button=True).on('keydown.enter', try_login)
            ui.button('Log in', on_click=try_login)
        return None

    @ui.page('/statistic')
    def statistics():
        navigation()
        title = os.getenv('APP_TITLE',default=cfg.get_config('frontend','app_title',default="MWICHT"))
        categories = ['visit','chat','pdf_question','pdf_summary','max_queue']
        ui.button(on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')), icon='logout').props('outline round')
        for c in categories:
            
                ui.label('CSS').style('color: #000').set_text(c)
                dates, values = statistic.getEventStat(c)
                columns = [
                    {'name': 'date', 'label': 'Date', 'field': 'date', 'required': True, 'align': 'left'},
                    {'name': 'value', 'label': c, 'field': 'value', 'sortable': True},
                ]
                rows = []
                for d,v in zip(dates,values):
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
            pdfmessages.append((assi, pdf_greeting + str(jobStat.countQueuedJobs())))
            answers = []
            questions = []
            status = jobStat.getJobStatus(app.storage.browser['id'],app.storage.user['pdf_job'])
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
            if context.get_client().has_socket_connection:
                ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')
            app.storage.user['pdf_ready'] = pdf_ready

        def delete_chat() -> None:
            assign_uuid_if_missing()
            jobStat.removeJob(app.storage.browser['id'],app.storage.user['pdf_job'])
            app.storage.user['pdf_question'] = ""
            app.storage.user['pdf_job'] = uuid4()
            pdf_ready['ready'] = False
            pdf_ready['answered'] = False
            pdf_ready['ready_to_upload'] = True
            app.storage.user['pdf_ready'] = pdf_ready
            pdf_messages.refresh()

        def copy_data():
            if 'answer' in jobStat.getJobStatus(app.storage.browser['id'],app.storage.user['pdf_job']):
                text = jobStat.getJobStatus(app.storage.browser['id'],app.storage.user['pdf_job'])['answer'][-1]
                ui.run_javascript('navigator.clipboard.writeText(`' + text + '`)', timeout=5.0)

        async def send() -> None:
            statistic.addEvent('pdf_question')
            assign_uuid_if_missing()
            message = app.storage.user['pdf_question']
            #custom_config = {'temperature':app.storage.user['temperature']/100,'max_tokens':app.storage.user['max_tokens'],'top_k':app.storage.user['top_k'],'top_p':app.storage.user['top_p']/100,'repeat_penalty':app.storage.user['repeat_penalty']/100}
            text.value = ''
            jobStat.addJob(app.storage.browser['id'],app.storage.user['pdf_job'],message,job_type = 'pdf_chat' )
            job = {'token':app.storage.browser['id'],'uuid':app.storage.user['pdf_job']}
            try:
                taskQueue.put(job)
                
            except:
                jobStat.updateStatus(app.storage.browser['id'],app.storage.user['pdf_job'],"failed") 

            timer.activate()
            pdf_messages.refresh()

        def summarize_pdf() -> None:
            statistic.addEvent('pdf_summary')
            assign_uuid_if_missing()
            jobStat.addJob(app.storage.browser['id'],app.storage.user['pdf_job'],"",job_type = 'pdf_summarize' )
            job = {'token':app.storage.browser['id'],'uuid':app.storage.user['pdf_job']}
            try:
                taskQueue.put(job)
                
            except:
                jobStat.updateStatus(app.storage.browser['id'],app.storage.user['pdf_job'],"failed") 

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
            jobStat.addJob(app.storage.browser['id'],app.storage.user['pdf_job'],prompt = '',custom_config = False,job_type = 'pdf_processing' )
            job = {'token':app.storage.browser['id'],'uuid':app.storage.user['pdf_job'],'filepath':filepath}
            try:
                taskQueue.put(job)
                pdf_ready['ready'] = False
                pdf_ready['answered'] = False
            except:
                jobStat.updateStatus(app.storage.browser['id'],app.storage.user['pdf_job'],"failed") 
            pdf_ready['ready_to_upload'] = False
            timer.activate()
            pdf_messages.refresh()

        navigation()
        
        # the queries below are used to expand the contend down to the footer (content can then use flex-grow to expand)
        ui.query('.q-page').classes('flex')
        ui.query('.nicegui-content').classes('w-full')
        
        

        with ui.tabs().classes('w-full') as tabs:
                pdf_tab = ui.tab('PDF')

        with ui.tab_panels(tabs, value=pdf_tab).classes('w-full max-w-2xl mx-auto flex-grow items-stretch'):
            with ui.tab_panel(pdf_tab).classes('items-stretch'):
                pdf_messages()

                ui.upload(on_upload=handle_upload,multiple=True,label='Upload Files',max_total_size=9048576).props('accept=".pdf,.docx,.csv"').classes('max-w-full').bind_visibility_from(pdf_ready,'ready_to_upload')


        with ui.footer().classes('bg-white'):
            with ui.column().classes('w-full max-w-3xl mx-auto my-6'):
                

                
                
                with ui.row().classes('w-full no-wrap items-center').bind_visibility_from(pdf_ready,'ready'):
                    placeholder = 'message' 
                    text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
                    .classes('w-full self-center').bind_value(app.storage.user, 'pdf_question').on('keydown.enter', send).bind_visibility_from(pdf_ready,'answered')
                    send_btn = ui.button(icon="send", on_click=lambda: send()).bind_visibility_from(pdf_ready,'answered')
                    summarize_btn = ui.button("summarize pdf", on_click=lambda: summarize_pdf()).bind_visibility_from(pdf_ready,'answered')
                    copy_btn = ui.button(icon="content_copy", on_click=lambda: copy_data())
                    delete_btn = ui.button(icon="delete_forever", on_click=lambda: delete_chat())
             

    ui.run_with(
        fastapi_app,
        storage_secret = uuid4(),
    )

