from llama_cpp import Llama
from dotenv import find_dotenv, load_dotenv
import box
import yaml
import requests
import os

def download_file(url, filename):
    local_filename = filename
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):  
                f.write(chunk)
    return local_filename


url= os.getenv('MODEL_DOWNLOAD_URL',default="https://huggingface.co/TheBloke/em_german_leo_mistral-GGUF/resolve/main/em_german_leo_mistral.Q5_K_S.gguf")
filename = os.getenv('MODEL_BIN_PATH',default="/models/em_german_leo_mistral.Q5_K_S.gguf")
ntokens = os.getenv('NUMBER_OF_TOKENS',default=4096)
verbose = os.getenv('VERBOSE',default=True)
layers = os.getenv('GPU_LAYERS',default=0)

def build_llm():
    if not os.path.exists(filename):
        print("Specified Model not found. Downloading Model...")
        download_file(url,filename)
        print("Download complete.")
    llm = Llama(model_path=filename,n_ctx=ntokens, n_batch=128,verbose=verbose,n_gpu_layers=int(layers)) #verbose = False leads to error
    return llm

