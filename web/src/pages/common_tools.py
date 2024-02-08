from uuid import uuid4

def assign_uuid_if_missing(app):
    if not 'chat_job' in app.storage.user or not app.storage.user['chat_job']:
        app.storage.user['chat_job'] = uuid4()
    if not 'pdf_job' in app.storage.user or not app.storage.user['pdf_job']:
        app.storage.user['pdf_job'] = uuid4()
    if not 'chain_job' in app.storage.user or not app.storage.user['chain_job']:
        app.storage.user['chain_job'] = uuid4()