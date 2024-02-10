#!/usr/bin/env python3
from typing import List, Tuple
from nicegui import app,context, ui, events
from pages.common_tools import assign_uuid_if_missing
from helpers.random_words import get_random_word_string

import os

def chain_editor(cfg,app):
    placeholder = 'prompt' 


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
                            app.storage.user['chain_files'+str(j)] = ""
                        break
                    j = j+1
            i += 1
        i = 0
        while 'chain_prompt'+str(i) in app.storage.user and app.storage.user['chain_prompt'+str(i)] and len(app.storage.user['chain_prompt'+str(i)]) > 0:
            with ui.row().classes('w-full no-wrap items-center'):
                text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
                .classes('w-full self-center').bind_value(app.storage.user, 'chain_prompt'+str(i)).on('keydown.enter', append)
                ui.radio({1: 'Map', 2: 'Reduce', 3: 'Expand'}).props('inline').bind_value(app.storage.user, 'chain_action'+str(i))
                ui.select(filenames, multiple=True, value="", label='Aus Dateien').classes('w-64').props('use-chips').bind_value(app.storage.user, 'chain_files'+str(i))
            i += 1
        with ui.row().classes('w-full no-wrap items-center'):
            text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
            .classes('w-full self-center').bind_value(app.storage.user, 'chain_prompt'+str(i)).on('keydown.enter', append)
            ui.radio({1: 'Map', 2: 'Reduce', 3: 'Expand'}).props('inline').bind_value(app.storage.user, 'chain_action'+str(i))
            ui.select(filenames, multiple=True, value="", label='Aus Dateien').classes('w-64').props('use-chips').bind_value(app.storage.user, 'chain_files'+str(i))
        with ui.row().classes('w-full no-wrap items-center'):
            compile_btn = ui.button(icon="not_started", on_click=lambda: compile())

    def compile()-> None:
        i = 0
        chain = []
        while 'chain_prompt'+str(i) in app.storage.user and app.storage.user['chain_prompt'+str(i)]:
            chain_elem = {'prompt':app.storage.user['chain_prompt'+str(i)],'action':app.storage.user['chain_action'+str(i)] if 'chain_action'+str(i) in app.storage.user else None,'files':app.storage.user['chain_files'+str(i)] if 'chain_files'+str(i) in app.storage.user else None}
            chain.append(chain_elem)
            i += 1
        print(chain)
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
        ui.input(label='Chain_ID',validation={'Input too long': lambda value: len(value) < 40}).bind_value(app.storage.user, 'chain_id')
        ui.upload(on_upload=handle_upload,multiple=True,label='Upload Files',max_total_size=9048576,on_rejected=lambda: ui.notify('Rejected!')).props('accept=".pdf,.docx,.msg"').classes('max-w-full')
        chain()
    
