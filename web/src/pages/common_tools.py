from uuid import uuid4

class PDFReady:
    def __init__(self):
        self.ready = False
        self.answered = False
        self.ready_to_upload = True

class ChainReady:
    def __init__(self):
        self.ready = False
        self.answered = False
        self.ready_to_upload = True

def assign_uuid_if_missing(app):
    if not 'chat_job' in app.storage.user or not app.storage.user['chat_job']:
        app.storage.user['chat_job'] = uuid4()
    if not 'pdf_job' in app.storage.user or not app.storage.user['pdf_job']:
        app.storage.user['pdf_job'] = uuid4()
    if not 'chain_job' in app.storage.user or not app.storage.user['chain_job']:
        app.storage.user['chain_job'] = uuid4()
    if not 'pdf_ready' in app.storage.user or not app.storage.user['pdf_ready']:
        app.storage.user['pdf_ready']= {'ready':False,'answered':False,'ready_to_upload':True}
    if not 'chain_ready' in app.storage.user or not app.storage.user['chain_ready']:
        app.storage.user['chain_ready']={'ready':False,'answered':False,'ready_to_upload':True}