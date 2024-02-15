from llama_cpp import Llama, LlamaGrammar
from dotenv import find_dotenv, load_dotenv
import box
import yaml
import requests
import os
from pdfrag import PDF_Processor
from llama_index.llms import LlamaCPP # FOR PDF

grammar = LlamaGrammar.from_file("list.gbnf")

def download_file(url, filename):
    local_filename = filename
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):  
                f.write(chunk)
    return local_filename

def build_llm(cfg):
    url= os.getenv('MODEL_DOWNLOAD_URL',default=cfg.get_config('model','model_download_url',default="https://huggingface.co/TheBloke/em_german_leo_mistral-GGUF/resolve/main/em_german_leo_mistral.Q5_K_S.gguf"))
    filename = os.getenv('MODEL_BIN_PATH',default=cfg.get_config('model','model_bin_path',default="/models/em_german_leo_mistral.Q5_K_S.gguf"))
    ntokens = os.getenv('NUMBER_OF_TOKENS',default=cfg.get_config('model','number_of_tokens',default=4096))
    verbose = os.getenv('VERBOSE',default=cfg.get_config('model','verbose',default=True))
    layers = os.getenv('GPU_LAYERS',default=cfg.get_config('model','gpu_layers',default=0))
    if not os.path.exists(filename):
        print("Specified Model not found. Downloading Model...")
        download_file(url,filename)
        print("Download complete.")
    llm = Llama(model_path=filename,n_ctx=ntokens, n_batch=128,verbose=verbose,n_gpu_layers=int(layers)) #verbose = False leads to error
    return llm


class chainProzessor():
    def __init__(self,llm,create_callback,update_callback,status_callback,cfg,meta_chain):
        self.llm = llm
        self.create_callback = create_callback
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.cfg = cfg
        #Info needed to summarize multiple pages until token limit
        self.total_tokens = 0
        self.total_text = ""
        self.names = []
        self.sources = []
        self.chain_id = meta_chain['chain_id']
        self.file_id = meta_chain['file_id']
        self.rawchain = meta_chain['chain']
        self.chain = []
        self.pdf_llm = LlamaCPP(
            # You can pass in the URL to a GGML model to download it automatically
            # optionally, you can set the path to a pre-downloaded model instead of model_url
            model_path=os.getenv('MODEL_BIN_PATH',default=cfg.get_config('model','model_bin_path',default="/models/em_german_leo_mistral.Q5_K_S.gguf")),
            temperature=0.1,
            max_new_tokens=512,
            # llama2 has a context window of 4096 tokens, but we set it lower to allow for some wiggle room
            context_window=3900,
            # kwargs to pass to __call__()
            generate_kwargs={},
            # kwargs to pass to __init__()
            # set to at least 1 to use GPU
            model_kwargs={"n_gpu_layers": int(os.getenv('GPU_LAYERS',default=cfg.get_config('model','gpu_layers',default=0)))},
            verbose=True,
            )
        self.__compile__()

    def __compile__(self):
        self.chain = []
        for item in self.rawchain:
            chain_elem = {}
            print(item)
            if item['files'] and not item['files'] == ['']:
                print(len(item['files']))
                proc = PDF_Processor(self.cfg,self.pdf_llm)
                for file in item['files']:
                    filepath = f'/tmp/{self.file_id}/{file}'
                    proc.processPDF(filepath,remove_orig=False)
                #prompt = item['prompt']
                #pdf_action_prompt = f"Sie kategoriesieren Texte nach dem jeweils enthaltenen Arbeitsauftrag. Bitte bestimmen Sie auf Basis des folgenden Arbeitsauftrags, welche der Aktionen 'Zusammenfassen','Frage Beantworten','Sonstige' gewünscht ist. '''{prompt}''' Geben Sie genau eine Aktion als Liste also entweder ['Zusammenfassen'], ['Frage Beantworten'] oder ['Sonstiges'] aus. ASSISTANT: Aktion:"
                #pdf_action = self.llm(prompt, temperature = 0.7, max_tokens = 128, top_k=20, top_p=0.9,repeat_penalty=1.15, grammar= grammar)['choices'][0]['text']
                #print(pdf_action)
                
                chain_elem['pdf_proc'] = proc
            chain_elem['instruction'] = item['prompt']
            chain_elem['action'] = item['action']
            self.chain.append(chain_elem)
        self.run()
    def run(self,initialprompt = ""):
        i = 0
        output = []
        while i < len(self.chain):
            chain_elem = self.chain[i]
            print("CHAINSTEP " + str(i))
            if i == 0:
                if initialprompt:
                    prompt = f"Eingabe:{initialprompt}. Auftrag: {chain_elem['instruction']}."
                else:
                    prompt = chain_elem['instruction']
                if chain_elem['action'] == 3:
                    output = self.llm(prompt, temperature = 0.7, max_tokens = 1024, top_k=20, top_p=0.9,repeat_penalty=1.15, grammar= grammar)['choices'][0]['text']    
                    output = output.split("- ")
                else:
                    output = self.llm(prompt, temperature = 0.7, max_tokens = 1024, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text']    
                print(output)
            else:
                newoutput = []
                if isinstance(output, list):
                    if chain_elem['action'] == 1 or chain_elem['action'] == 3  : #map each elem to prompt, no support for further expasion yet
                        for item in output[:10]:
                            print("Elementwise Mapping with " + str(item))
                            prompt = f"Eingabe:{item}. Auftrag: {chain_elem['instruction']}."
                            newoutput.append(self.llm(prompt, temperature = 0.7, max_tokens = 4096, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text'])
                    if chain_elem['action'] == 2: #reduce list to one
                        
                        fulltext = ""
                        for item in output:
                            fulltext += item + "\n" 
                        print("Reduce List with " + str(fulltext))
                        prompt = f"Eingabe:{fulltext}. Auftrag: {chain_elem['instruction']}."
                        newoutput = self.llm(prompt, temperature = 0.7, max_tokens = 4096, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text']

                else:
                    if chain_elem['action'] == 1 or chain_elem['action'] == 2: #reduce is like map without list
                        print("Reduce or map without list " +str(output))
                        prompt = f"Eingabe:{output}. Auftrag: {chain_elem['instruction']}."
                        newoutput = self.llm(prompt, temperature = 0.7, max_tokens = 4096, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text']
                    else: #expand
                        print("Expand without list " +str(expand))
                        prompt = f"Eingabe:{output}. Auftrag: {chain_elem['instruction']}."
                        newoutput = self.llm(prompt, temperature = 0.7, max_tokens = 4096, top_k=20, top_p=0.9,repeat_penalty=1.15, grammar= grammar)['choices'][0]['text']    
                        newoutput = newoutput.split("- ")
                output = newoutput

            i += 1
        print(output)