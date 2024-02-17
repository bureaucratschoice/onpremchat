#!/usr/bin/env python3
from typing import List, Tuple
from nicegui import app,context, ui, events
from pages.common_tools import assign_uuid_if_missing
from helpers.random_words import get_random_word_string

import os


def chain_editor(cfg,app,jobStat,taskQueue):
    placeholder = 'prompt' 
    action_mapping = {1: 'Map', 2: 'Reduce', 3: 'Expand'}
    timer = ui.timer(1.0, lambda: chain_messages.refresh())
    
    @ui.refreshable
    def chain() -> None:
        assign_uuid_if_missing(app)
        if not 'chain_id' in app.storage.user or not app.storage.user['chain_id']:
            app.storage.user['chain_id'] = get_random_word_string(3)
        if 'filenames' in app.storage.user:
            filenames = app.storage.user['filenames']
        else:
            filenames = []
        i = 0
        while 'chain_prompt'+str(i) in app.storage.user:
            if not app.storage.user['chain_prompt'+str(i)]:
                j = i+1
                while 'chain_prompt'+str(j) in app.storage.user:
                    if app.storage.user['chain_prompt'+str(j)]:
                        app.storage.user['chain_prompt'+str(i)] = app.storage.user['chain_prompt'+str(j)]
                        app.storage.user['chain_prompt'+str(j)] = ""
                        if 'chain_action'+str(j) in app.storage.user and app.storage.user['chain_action'+str(j)]:
                            app.storage.user['chain_action'+str(i)] = app.storage.user['chain_action'+str(j)]
                            app.storage.user['chain_action'+str(j)] = ""
                        if 'chain_files'+str(j) in app.storage.user and app.storage.user['chain_files'+str(j)]:
                            app.storage.user['chain_files'+str(i)] = app.storage.user['chain_files'+str(j)]
                            app.storage.user['chain_files'+str(j)] = []
                        break
                    j = j+1
            i += 1
        i = 0
        while 'chain_prompt'+str(i) in app.storage.user and app.storage.user['chain_prompt'+str(i)] and len(app.storage.user['chain_prompt'+str(i)]) > 0:
            with ui.row().classes('w-full no-wrap items-center'):
                text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
                .classes('w-full self-center').bind_value(app.storage.user, 'chain_prompt'+str(i)).on('keydown.enter', append)
                ui.radio(action_mapping).props('inline').bind_value(app.storage.user, 'chain_action'+str(i))
                ui.select(filenames, multiple=True, value="", label='Aus Dateien').classes('w-64').props('use-chips').bind_value(app.storage.user, 'chain_files'+str(i))
            i += 1
        with ui.row().classes('w-full no-wrap items-center'):
            text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
            .classes('w-full self-center').bind_value(app.storage.user, 'chain_prompt'+str(i)).on('keydown.enter', append)
            ui.radio(action_mapping).props('inline').bind_value(app.storage.user, 'chain_action'+str(i))
            ui.select(filenames, multiple=True, value="", label='Aus Dateien').classes('w-64').props('use-chips').bind_value(app.storage.user, 'chain_files'+str(i))
        with ui.row().classes('w-full no-wrap items-center'):
            compile_btn = ui.button(icon="not_started", on_click=lambda: compile())

    chainmessages: List[Tuple[str, str]] = [] 
    thinking: bool = False
    
    assign_uuid_if_missing(app)
    
    @ui.refreshable
    def chain_messages() -> None:
        assign_uuid_if_missing(app)
        chainmessages: List[Tuple[str, str]] = [] 
        chainmessages.append(("assi",str(jobStat.countQueuedJobs())))
        answers = []
        questions = []
        status = jobStat.getJobStatus(app.storage.browser['id'],app.storage.user['chain_job'])
            
        if 'job_type' in status and status['job_type'] == 'compile_chain':
            if 'answer' in status:
                answers = status['answer']
        i_q = 0
        i_a = 0
        output_fin = False
        while not output_fin:
            if i_q < len(questions):
                if questions[i_q]:
                    chainmessages.append((you,questions[i_q]))
                    i_q += 1
                else:
                    i_q += 1
                    continue
            if i_a < len(answers):
                if answers[i_a]:
                    chainmessages.append(("assi",answers[i_a]))
                    i_a += 1
                else:
                    i_a += 1
                    continue
            if i_q >= len(questions) and i_a >= len(answers):
                output_fin = True
            
        for name, text in chainmessages:
            ui.chat_message(text=text, name=name, sent=name == "assi")
            
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
        #if context.get_client().has_socket_connection:
        #    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

    def compile()-> None:
        i = 0
        chain = []
        while 'chain_prompt'+str(i) in app.storage.user and app.storage.user['chain_prompt'+str(i)]:
            chain_elem = {'prompt':app.storage.user['chain_prompt'+str(i)],'action':app.storage.user['chain_action'+str(i)] if 'chain_action'+str(i) in app.storage.user else 0,'files':app.storage.user['chain_files'+str(i)] if 'chain_files'+str(i) in app.storage.user else []}
            chain.append(chain_elem)
            i += 1
        meta_chain = {'chain_id':app.storage.user['chain_id'],'file_id':app.storage.browser['id'],'chain':chain}
        print(chain)
        jobStat.addJob(app.storage.browser['id'],app.storage.user['chain_job'],'compile_chain',job_type = 'compile_chain' )
        job = {'token':app.storage.browser['id'],'uuid':app.storage.user['chain_job'],'meta_chain':meta_chain}
        try:
            taskQueue.put(job)
                
        except:
            jobStat.updateStatus(app.storage.browser['id'],app.storage.user['chain_job'],"failed") 
        timer.activate()
        
    def append() -> None:
        assign_uuid_if_missing(app)
        chain.refresh()

    def handle_upload(event: events.UploadEventArguments):
        assign_uuid_if_missing(app)
        fileid = app.storage.browser['id']
        if 'filenames' in app.storage.user:
            filenames = app.storage.user['filenames']
        else:
            filenames = []
        with event.content as f:    
            filepath = f'/tmp/{fileid}/{event.name}'
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file = open(filepath, 'wb')
            for line in f.readlines():
                file.write(line)
            file.close()
            filenames.append(event.name)  
        app.storage.user['filenames'] = filenames
        chain.refresh()
    anchor_style = r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}'
    ui.add_head_html(f'<style>{anchor_style}</style>')
    title = os.getenv('APP_TITLE',default=cfg.get_config('frontend','app_title',default="MWICHT"))

    ui.page_title(title)
    # the queries below are used to expand the contend down to the footer (content can then use flex-grow to expand)
    ui.query('.q-page').classes('flex')
    ui.query('.nicegui-content').classes('w-full')
    with ui.column().classes('w-full max-w-3xl mx-auto my-6'):
        #with ui.row().classes('w-full no-wrap items-center'):
        ui.input(label='Chain_ID',validation={'Input too long': lambda value: len(value) < 100}).bind_value(app.storage.user, 'chain_id').classes('w-full')
        ui.upload(on_upload=handle_upload,multiple=True,label='Upload Files',max_total_size=9048576,on_rejected=lambda: ui.notify('Rejected!')).props('accept=".pdf,.docx,.msg"').classes('max-w-full')
        chain()
        chain_messages()
    