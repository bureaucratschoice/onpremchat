"""
Main module for initializing the language model, processing PDF/chat jobs,
and serving endpoints via FastAPI.
"""

import os
import json
import pickle
import queue
import threading
from uuid import uuid4
from typing import Any, Dict, List, Union

import requests
from fastapi import FastAPI
from pydantic import BaseModel
from nicegui import app, ui

# Third-party language model
from llama_index.llms.llama_cpp import LlamaCPP

# Local modules
from llm import build_llm, download_file
from config import config
import frontend
import pdftools
from pdfrag import DocumentProcessor
from statistics import Statistic
from promptutils import FriendlyFormatter


# -----------------------------
# Environment & LLM Initialization
# -----------------------------


cfg = config()

# Retrieve context tokens and model parameters from environment or config
n_ctx: int = int(os.getenv('NUMBER_OF_TOKENS', default=cfg.get_config('model', 'number_of_tokens', default=4096)))
model_url: str = os.getenv(
    'MODEL_DOWNLOAD_URL',
    default=cfg.get_config('model', 'model_download_url', default="https://huggingface.co/TheBloke/em_german_leo_mistral-GGUF/resolve/main/em_german_leo_mistral.Q5_K_S.gguf")
)
model_bin_path: str = os.getenv(
    'MODEL_BIN_PATH',
    default=cfg.get_config('model', 'model_bin_path', default="/models/em_german_leo_mistral.Q5_K_S.gguf")
)

# Download model if not present
if not os.path.exists(model_bin_path):
    print("Specified Model not found. Downloading Model...")
    download_file(model_url, model_bin_path)
    print("Download complete.")

# Instantiate the language model
llm2 = LlamaCPP(
    model_path=os.getenv(
        'MODEL_BIN_PATH',
        default=cfg.get_config('model', 'model_bin_path', default="/models/em_german_leo_mistral.Q5_K_S.gguf")
    ),
    max_new_tokens=int(n_ctx/2)-1,
    context_window=int(n_ctx/2),
    generate_kwargs={},
    model_kwargs={
        "n_gpu_layers": int(os.getenv('GPU_LAYERS', default=cfg.get_config('model', 'gpu_layers', default=0))),
        "n_ctx": n_ctx
    },
    verbose=True,
)
llm = llm2


# -----------------------------
# Job Status Management
# -----------------------------

class JobStatus:
    """
    Class to manage job statuses and associated PDF processors.
    """

    def __init__(self) -> None:
        self.jobs_by_token: Dict[str, Dict[str, Dict]] = {}
        self.pdf_proc_by_token: Dict[str, Dict[str, Any]] = {}

    def add_pdf_proc(self, token: str, uuid: str, pdf_proc: Any) -> None:
        """Add a PDF processor for the given token and job uuid."""
        if token in self.pdf_proc_by_token:
            self.pdf_proc_by_token[token][uuid] = pdf_proc
        else:
            self.pdf_proc_by_token[token] = {uuid: pdf_proc}

    def get_pdf_proc(self, token: str, uuid: str) -> Union[Any, bool]:
        """Retrieve the PDF processor for the given token and job uuid."""
        if token in self.pdf_proc_by_token and uuid in self.pdf_proc_by_token[token]:
            return self.pdf_proc_by_token[token][uuid]
        return False

    def add_job(
        self,
        token: str,
        uuid: str,
        prompt: str,
        custom_config: bool = False,
        job_type: str = 'chat'
    ) -> bool:
        """
        Add a job with the given parameters.
        The job is stored with an initial status of 'queued'.
        """
        try:
            if token in self.jobs_by_token:
                if uuid in self.jobs_by_token[token]:
                    self.jobs_by_token[token][uuid] = {
                        'status': 'queued',
                        'prompt': self.jobs_by_token[token][uuid]['prompt'] + [prompt],
                        'answer': self.jobs_by_token[token][uuid]['answer'],
                        'custom_config': custom_config,
                        'job_type': job_type
                    }
                else:
                    self.jobs_by_token[token][uuid] = {
                        'status': 'queued',
                        'prompt': [prompt],
                        'answer': [],
                        'custom_config': custom_config,
                        'job_type': job_type
                    }
            else:
                self.jobs_by_token[token] = {
                    uuid: {
                        'status': 'queued',
                        'prompt': [prompt],
                        'answer': [],
                        'custom_config': custom_config,
                        'job_type': job_type
                    }
                }
            return True
        except Exception:
            return False

    def count_queued_jobs(self) -> int:
        """Count and return the number of jobs with status 'queued'."""
        counter = 0
        try:
            for token in self.jobs_by_token:
                for uuid in self.jobs_by_token[token]:
                    if self.jobs_by_token[token][uuid].get('status') == 'queued':
                        counter += 1
            return counter
        except Exception:
            return 0

    def remove_job(self, token: str, uuid: str) -> bool:
        """Remove a specific job (and its PDF processor if present)."""
        try:
            if token in self.jobs_by_token and uuid in self.jobs_by_token[token]:
                del self.jobs_by_token[token][uuid]
                if token in self.pdf_proc_by_token and uuid in self.pdf_proc_by_token[token]:
                    del self.pdf_proc_by_token[token][uuid]
                return True
            return False
        except Exception:
            return False

    def super_remove_job(self, uuid: str) -> bool:
        """
        Remove all jobs if uuid equals 'All'; otherwise, remove the job matching uuid.
        """
        try:
            if uuid == 'All':
                self.jobs_by_token = {}
                self.pdf_proc_by_token = {}
                return True
            else:
                for token in self.jobs_by_token:
                    if uuid in self.jobs_by_token[token]:
                        del self.jobs_by_token[token][uuid]
                        return True
                return False
        except Exception:
            return False

    def add_answer(self, token: str, uuid: str, answer: str) -> bool:
        """Append an answer to the job identified by token and uuid."""
        #print(f'called add_answer for token: {token} with uuid: {uuid} and answer: {answer}')
        try:
            if token in self.jobs_by_token and uuid in self.jobs_by_token[token]:
                self.jobs_by_token[token][uuid].setdefault('answer', []).append(answer)
                return True
            return False
        except Exception:
            return False

    def update_answer(self, token: str, uuid: str, answer: str) -> bool:
        """Update the last answer of the job identified by token and uuid."""
        #print(f'called update_answer for token: {token} with uuid: {uuid} and answer: {answer}')
        try:
            if token in self.jobs_by_token and uuid in self.jobs_by_token[token]:
                if self.jobs_by_token[token][uuid].get('answer'):
                    self.jobs_by_token[token][uuid]['answer'][-1] = answer
                else:
                    self.jobs_by_token[token][uuid]['answer'] = [answer]
                return True
            return False
        except Exception as error:
            print(error)
            return False

    def update_status(self, token: str, uuid: str, status: str) -> bool:
        """Update the status of the job identified by token and uuid."""
        #print(f'called update_status for token: {token} with uuid: {uuid} and status: {status}')
        try:
            if token in self.jobs_by_token and uuid in self.jobs_by_token[token]:
                self.jobs_by_token[token][uuid]['status'] = status
                return True
            return False
        except Exception:
            return False

    def get_job_status(self, token: str, uuid: str) -> Dict:
        """
        Retrieve the job status. If not found, return a default empty job.
        """
        try:
            if token in self.jobs_by_token and uuid in self.jobs_by_token[token]:
                job = self.jobs_by_token[token][uuid]
                job['uuid'] = uuid
                return job
            return {'uuid': '', 'status': '', 'prompt': [''], 'answer': ['']}
        except Exception:
            return {}

    def get_all_jobs_for_token(self, token: str) -> Dict:
        """Return all jobs for a given token."""
        try:
            if token in self.jobs_by_token:
                return self.jobs_by_token[token]
            return {'': {'status': '', 'prompt': [''], 'answer': ['']}}
        except Exception:
            return {}

    def get_all_status(self) -> Dict:
        """Return the status of all jobs across tokens."""
        try:
            result = {}
            for token in self.jobs_by_token:
                result[token] = {}
                for uuid in self.jobs_by_token[token]:
                    job = self.jobs_by_token[token][uuid]
                    result[token][uuid] = {'status': job.get('status', '')}
            return result
        except Exception:
            return {}


# -----------------------------
# Main Processing Thread
# -----------------------------

class MainProcessor(threading.Thread):
    """
    Thread that continuously processes jobs from the task queue.
    """

    def __init__(self, task_lock: threading.Lock, task_queue: queue.Queue, job_stat: JobStatus, statistic: Statistic) -> None:
        super().__init__()
        self.task_lock = task_lock
        self.task_queue = task_queue
        self.job_stat = job_stat
        self.statistic = statistic
        self.daemon = True  # Ensure thread exits when main program exits

    def run(self) -> None:
        """Continuously process jobs from the queue."""
        while True:
            job = self.task_queue.get(block=True)
            token = job['token']
            uuid = job['uuid']

            self.job_stat.update_status(token, uuid, "processing")
            item = self.job_stat.get_job_status(token, uuid)
            self.statistic.updateQueueSize(self.job_stat.count_queued_jobs())


            job_type = item.get('job_type', '')
            if job_type == 'pdf_processing':
                filepath = job.get('filepath')
                if filepath:
                    pdf_proc = self.job_stat.get_pdf_proc(token, uuid)
                    if not pdf_proc:
                        pdf_proc = DocumentProcessor(llm2, 3900)
                        self.job_stat.add_pdf_proc(token, uuid, pdf_proc)
                    # Process PDF from its directory
                    pdf_proc.process_directory(os.path.dirname(filepath))
                    self.job_stat.update_status(token, uuid, "finished")

            elif job_type == 'pdf_chat':
                response = ""
                self.job_stat.add_answer(token, uuid, response)
                pdf_proc = self.job_stat.get_pdf_proc(token, uuid)
                if not pdf_proc:
                    self.job_stat.update_status(token, uuid, "failed")
                else:
                    answer = pdf_proc.ask(item['prompt'][-1])
                    for answ in answer:
                        response += answ
                        if not self.job_stat.update_answer(token, uuid, response):
                            break

                    metadatas = pdf_proc.get_last_response_metadata()
                    response += "(vgl. "
                    for metadata in metadatas:
                        source = metadata.get('source', '?')
                        if source == '?':
                            source = metadata.get('page_label', '?')
                        name = metadata.get('file_path', '?')
                        if '/' in name:
                            name = name.split('/')[-1]
                        response += f"{name}:{source}"
                    response += ")"
                    self.job_stat.update_answer(token, uuid, response)
                    self.job_stat.update_status(token, uuid, "finished")
                    pdf_proc.get_last_response_metadata()

            elif job_type == 'pdf_summarize':
                pdf_proc = self.job_stat.get_pdf_proc(token, uuid)
                #self.job_stat.add_answer(token, uuid, "")
                create_callback = lambda x: self.job_stat.add_answer(token, uuid, x)
                update_callback = lambda x: self.job_stat.update_answer(token, uuid, x)
                status_callback = lambda x: self.job_stat.update_status(token, uuid, x)

                # Determine summarizer type
                summarizer = job.get('summarizer')
                if not summarizer:
                    summarizer_type = os.getenv(
                        'SUMMARIZER',
                        default=cfg.get_config('model', 'summarizer', default="simple")
                    )
                    if summarizer_type == "advanced":
                        summarizer = pdftools.AdvancedPdfSummarizer(
                            llm, pdf_proc, create_callback, update_callback, status_callback, cfg
                        )
                    else:
                        summarizer = pdftools.SimplePdfSummarizer(
                            llm, pdf_proc, create_callback, update_callback, status_callback, cfg
                        )

                if not summarizer.run():
                    self.task_queue.put({
                        'token': token,
                        'uuid': uuid,
                        'summarizer': summarizer
                    })

            else:
                # Default: process chat job
                sysprompt = os.getenv(
                    'CHATPROMPT',
                    default=cfg.get_config('model', 'chatprompt', default="Sei hilfreich!")
                )
                prompt_format = os.getenv(
                    'PROMPTFORMAT',
                    default=cfg.get_config('model', 'promptformat', default="leo-mistral")
                )
                
                formatter = FriendlyFormatter()
                
                prompt = formatter.format(item, sysprompt)
                response = ""
                
                self.job_stat.add_answer(token, uuid, response)
                completion_kwargs={
                    "stop": ["ASSISTANT:"],  # Verhindert das automatische Einfügen
                    "format": "markdown"
                }
                try:
                    if item.get('custom_config'):
                        answer = llm.stream(prompt,kwargs=completion_kwargs)
                        #answer = llm.create_chat_completion(prompt,stream=True)
                    else:
                        answer = llm.stream(prompt,kwargs=completion_kwargs)
                        #answer = llm.create_chat_completion(prompt,stream=True)
                    for answ in answer:
                        response += answ
                        if not self.job_stat.update_answer(token, uuid, response):
                            break
                except Exception as e:
                    print(e)
                    response = os.getenv(
                        'CHATERROR',
                        default=cfg.get_config('model', 'chaterror', default="Sie haben die maximale Chatlänge erreicht.")
                    )
                self.job_stat.update_answer(token, uuid, response)
                self.job_stat.update_status(token, uuid, "finished")


# -----------------------------
# Token Management Functions
# -----------------------------

TOKENS_FILE = "/config/tokens.pickle"
try:
    tokens: Dict[str, Dict] = pickle.load(open(TOKENS_FILE, "rb"))
except (OSError, IOError):
    tokens = {}
    pickle.dump(tokens, open(TOKENS_FILE, "wb"))


def dump_tokens(tokens_dict: Dict[str, Dict]) -> None:
    """Persist tokens to disk."""
    pickle.dump(tokens_dict, open(TOKENS_FILE, "wb"))


def generate_token(quota: int, description: str = "") -> str:
    """
    Generate a new token with the given quota and description.
    Returns the generated token.
    """
    token = uuid4().hex
    tokens[token] = {'quota': quota, 'description': description}
    dump_tokens(tokens)
    return token


def revoke_token(token: str) -> str:
    """
    Revoke the given token.
    Returns "OK" if successful, otherwise an error message.
    """
    if token in tokens:
        del tokens[token]
        dump_tokens(tokens)
        return "OK"
    return "Token not found"


def check_token(token: str) -> bool:
    """
    Check if a token is valid.
    If quota is positive, decrement it (unless it is -1, which means unlimited).
    """
    if token in tokens:
        if tokens[token]['quota'] == -1:
            return True
        if tokens[token]['quota'] > 0:
            tokens[token]['quota'] -= 1
            dump_tokens(tokens)
            return True
    return False


def token_details(token: str) -> Dict[str, Union[int, str]]:
    """
    Return details of the given token.
    If token is not found, return default details.
    """
    return tokens.get(token, {'quota': 0, 'description': 'Not existent'})


# Super token for administrative endpoints
supertoken: str = os.getenv('SUPERTOKEN', default="PLEASE_CHANGE_THIS_PLEASE")


# -----------------------------
# Global Objects and Thread Startup
# -----------------------------

job_stat = JobStatus()
task_lock = threading.Lock()
task_queue = queue.Queue(1000)
statistic = Statistic()

processor_thread = MainProcessor(task_lock, task_queue, job_stat, statistic)
processor_thread.start()


# -----------------------------
# FastAPI Endpoints
# -----------------------------

app = FastAPI()


class Item(BaseModel):
    prompt: str
    token: str


class TokenCreation(BaseModel):
    supertoken: str
    quota: Union[int, None] = 100
    description: Union[str, None] = "unknown"


class TokenRevoke(BaseModel):
    supertoken: str
    token: str


class Status(BaseModel):
    token: str
    uuid: Union[str, None] = "All"


@app.post("/getStatus/")
async def get_status(status: Status) -> Any:
    """
    Return the job status for a given token and uuid.
    If uuid is 'All', return all jobs for the token.
    """
    if status.uuid == "All":
        return job_stat.get_all_jobs_for_token(status.token)
    return job_stat.get_job_status(status.token, status.uuid)


@app.post("/getAllStatus/")
async def get_all_status(status: Status) -> Any:
    """
    Return the status of all jobs if the provided token matches the supertoken.
    """
    if status.token == supertoken:
        return job_stat.get_all_status()
    return {"result": "Access denied."}


@app.post("/deleteJob/")
async def delete_job(status: Status) -> Any:
    """
    Delete a job (or all jobs if uuid is 'All') if the provided token matches the supertoken.
    """
    if status.token == supertoken:
        result = job_stat.super_remove_job(status.uuid)
        return result
    return {"result": "Access denied."}


@app.post("/createToken/")
async def create_token(token_data: TokenCreation) -> Any:
    """
    Create a new token if the provided supertoken is valid.
    """
    if token_data.supertoken == supertoken:
        token_str = generate_token(token_data.quota, token_data.description)
        return {"token": token_str}
    return {"result": "Access denied."}


@app.post("/revokeToken/")
async def revoke_token_endpoint(token_data: TokenRevoke) -> Any:
    """
    Revoke an existing token if the provided supertoken is valid.
    """
    if token_data.supertoken == supertoken:
        result = revoke_token(token_data.token)
        return {"result": result}
    return {"result": "Access denied."}


@app.post("/generate/")
async def generate_text(item: Item) -> Any:
    """
    Enqueue a new job for text generation if the token is valid.
    """
    if check_token(item.token):
        job_uuid = uuid4().hex
        job_stat.add_job(item.token, job_uuid, item.prompt)
        job = {'token': item.token, 'uuid': job_uuid}
        try:
            task_queue.put(job)
        except Exception:
            job_stat.update_status(item.token, job_uuid, "failed")
        return job_stat.get_job_status(item.token, job_uuid)
    return "Access denied."


# Initialize frontend with app, job status, task queue, configuration, and statistics
frontend.init(app, job_stat, task_queue, cfg, statistic)
