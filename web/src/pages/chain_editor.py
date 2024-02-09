#!/usr/bin/env python3
from typing import List, Tuple
from nicegui import app,context, ui, events
from pages.common_tools import assign_uuid_if_missing
import os

def chain_editor(cfg,app):
    placeholder = 'prompt' 

    @ui.refreshable
    def chainold() -> None:
        assign_uuid_if_missing(app)
        print('in Chain')
        if 'chain' in app.storage.user:
          
            for chain_elem in app.storage.user['chain']:
                print(chain_elem)
                ui.chat_message(text=chain_elem, name="Sie",sent = True)
        if context.get_client().has_socket_connection:
            ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

    @ui.refreshable
    def chain() -> None:
        assign_uuid_if_missing(app)
        
        i = 0
        while 'chain_elem'+str(i) in app.storage.user:
            if not app.storage.user['chain_elem'+str(i)]:
                j = i+1
                while 'chain_elem'+str(j) in app.storage.user:
                    if app.storage.user['chain_elem'+str(j)]:
                        app.storage.user['chain_elem'+str(i)] = app.storage.user['chain_elem'+str(j)]
                        app.storage.user['chain_elem'+str(j)] = ""
                        if 'chain_action'+str(j) in app.storage.user and app.storage.user['chain_action'+str(j)]:
                            app.storage.user['chain_action'+str(i)] = app.storage.user['chain_action'+str(j)]
                            app.storage.user['chain_action'+str(j)] = ""
                        break
                    j = j+1
            i += 1
        i = 0
        while 'chain_elem'+str(i) in app.storage.user and app.storage.user['chain_elem'+str(i)] and len(app.storage.user['chain_elem'+str(i)]) > 0:
            with ui.row().classes('w-full no-wrap items-center'):
                text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
                .classes('w-full self-center').bind_value(app.storage.user, 'chain_elem'+str(i)).on('keydown.enter', append)
                ui.radio({1: 'Map', 2: 'Reduce', 3: 'Expand'}).props('inline').bind_value(app.storage.user, 'chain_action'+str(i))
            i += 1
        with ui.row().classes('w-full no-wrap items-center'):
            text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
            .classes('w-full self-center').bind_value(app.storage.user, 'chain_elem'+str(i)).on('keydown.enter', append)
            ui.radio({1: 'Map', 2: 'Reduce', 3: 'Expand'}).props('inline').bind_value(app.storage.user, 'chain_action'+str(i))

    def append() -> None:
        assign_uuid_if_missing(app)
        #print('in Append')
        '''
        chain_elem = app.storage.user['chain_elem']
        if 'chain' in app.storage.user:
            app.storage.user['chain'].append(chain_elem)
        else:
            app.storage.user['chain'] = [chain_elem]
        
        '''
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
        chain()
    
    '''
    with ui.footer().classes('bg-white'):
        with ui.column().classes('w-full max-w-3xl mx-auto my-6'):
            with ui.row().classes('w-full no-wrap items-center'):
                text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
                .classes('w-full self-center').bind_value(app.storage.user, 'chain_elem').on('keydown.enter', append)
                send_btn = ui.button(icon="send", on_click=lambda: append())
    '''