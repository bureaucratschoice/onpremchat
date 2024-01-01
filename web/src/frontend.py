#!/usr/bin/env python3
from typing import List, Tuple

from nicegui import app,context, ui
from datetime import datetime
from fastapi import FastAPI
import os
import time
from uuid import uuid4

class InputText:
    def __init__(self):
        self.text = ""

inputText = InputText()

def init(fastapi_app: FastAPI,jobStat,taskQueue) -> None:
    assi = os.getenv('ASSISTANT',default="Assistent")
    you = os.getenv('YOU',default="Sie")
    greeting = os.getenv('GREETING',default="Achtung, prüfen Sie jede Antwort bevor Sie diese in irgendeiner Form weiterverwenden. Je länger Ihre Frage ist bzw. je länger der bisherige Chatverlauf, desto länger brauche ich zum lesen. Es kann daher dauern, bis ich anfange Ihre Antwort zu schreiben. Die Länge der Warteschlange ist aktuell: ")
        



    @ui.page('/chat')
    
    def show():
        
        messages: List[Tuple[str, str]] = [] 
        thinking: bool = False
        timer = ui.timer(1.0, lambda: chat_messages.refresh())
        @ui.refreshable
        def chat_messages() -> None:
            messages: List[Tuple[str, str]] = [] 
            messages.append((assi, greeting + str(jobStat.countQueuedJobs())))
            answers = []
            questions = []
            if 'answer' in jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id']):
                answers = jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id'])['answer']
            if 'prompt' in jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id']):
                questions = jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id'])['prompt']
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
                
                #ui.chat_message(text=text, name=name, sent=name == you)
            if 'status' in jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id']):
                if jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id'])['status'] == 'processing':
                    thinking = True
                    timer.activate()
                    
                else:
                    thinking = False
                    timer.activate()
                if jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id'])['status'] == 'finished':
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
            if 'answer' in jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id']):
                answers = jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id'])['answer']
            if 'prompt' in jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id']):
                questions = jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id'])['prompt']
            

            i_q = 0
            i_a = 0
            
            while i_q < len(questions):
                messages.append((you,questions[i_q]))
                if i_a < len(answers):
                    messages.append((assi,answers[i_q]))
                i_q += 1
                i_a += 1

        def delete_chat() -> None:
            jobStat.removeJob(app.storage.browser['id'],app.storage.browser['id'])
           
            chat_messages.refresh()
        
        def copy_data():
            if 'answer' in jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id']):
                text = jobStat.getJobStatus(app.storage.browser['id'],app.storage.browser['id'])['answer'][-1]
                ui.run_javascript('navigator.clipboard.writeText(`' + text + '`)', timeout=5.0)
        async def send() -> None:
            #nonlocal thinking
            message = app.storage.user['text']
            


            #thinking = True
            text.value = ''

            jobStat.addJob(app.storage.browser['id'],app.storage.browser['id'],message)
            job = {'token':app.storage.browser['id'],'uuid':app.storage.browser['id']}
            try:
                taskQueue.put(job)
            except:
                jobStat.updateStatus(frontend,app.storage.browser['id'],"failed") 
            #thinking = False
            timer.activate()
            chat_messages.refresh()
            

        anchor_style = r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}'
        ui.add_head_html(f'<style>{anchor_style}</style>')
        title = os.getenv('APP_TITLE',default="MWICHT")

        ui.page_title(title)
        # the queries below are used to expand the contend down to the footer (content can then use flex-grow to expand)
        ui.query('.q-page').classes('flex')
        ui.query('.nicegui-content').classes('w-full')

        with ui.tabs().classes('w-full') as tabs:
            chat_tab = ui.tab('Chat')
        with ui.tab_panels(tabs, value=chat_tab).classes('w-full max-w-2xl mx-auto flex-grow items-stretch'):
            with ui.tab_panel(chat_tab).classes('items-stretch'):
                chat_messages()


        with ui.footer().classes('bg-white'), ui.column().classes('w-full max-w-3xl mx-auto my-6'):
            with ui.row().classes('w-full no-wrap items-center'):
                placeholder = 'message' 
                text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
                    .classes('w-full self-center').bind_value(app.storage.user, 'text').on('keydown.enter', send)
                send_btn = ui.button(icon="send", on_click=lambda: send())
                copy_btn = ui.button(icon="content_copy", on_click=lambda: copy_data())
                delete_btn = ui.button(icon="delete_forever", on_click=lambda: delete_chat())
                #update_btn = ui.button('Aktualisieren', on_click=lambda: chat_messages.refresh())
                
                
            #ui.markdown('simple chat app built with [NiceGUI](https://nicegui.io)') \
            #    .classes('text-xs self-end mr-8 m-[-1em] text-primary')

    @ui.page('/')
    def home():
        tochat = os.getenv('TOCHAT',default="Zum Chat")
        ui.button(tochat, on_click=lambda: ui.open(show, new_tab=False))
    

    ui.run_with(
        fastapi_app,
        storage_secret = uuid4(),
    )

