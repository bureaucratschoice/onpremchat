#!/usr/bin/env python3
from typing import List, Tuple
from nicegui import app,context, ui, events
from pages.common_tools import assign_uuid_if_missing
import os

def chain_editor(cfg,app):
        placeholder = 'prompt' 
        @ui.refreshable
        def chain() -> None:
            assign_uuid_if_missing(app)
            i = 0
                        
            while 'chain'+str(i) in app.storage.user:
                ui.chat_message(text=app.storage.user['chain'+str(i)], name="Sie")
                    
                i += 1
          
            
        def append() -> None:
            assign_uuid_if_missing(app)
            chain.refresh()

        anchor_style = r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}'
        ui.add_head_html(f'<style>{anchor_style}</style>')
        title = os.getenv('APP_TITLE',default=cfg.get_config('frontend','app_title',default="MWICHT"))

        ui.page_title(title)
        # the queries below are used to expand the contend down to the footer (content can then use flex-grow to expand)
        ui.query('.q-page').classes('flex')
        ui.query('.nicegui-content').classes('w-full')

        with ui.footer().classes('bg-white'):
            with ui.column().classes('w-full max-w-3xl mx-auto my-6'):
                with ui.row().classes('w-full no-wrap items-center').bind_visibility_from(pdf_ready,'ready'):
                    text = ui.textarea(placeholder=placeholder).props('rounded outlined input-class=mx-3').props('clearable') \
                    .classes('w-full self-center').bind_value(app.storage.user, 'chain'+str(0)).on('keydown.enter', append)
                send_btn = ui.button(icon="send", on_click=lambda: append())

           