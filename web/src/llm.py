from llama_cpp import Llama, LlamaGrammar
from dotenv import find_dotenv, load_dotenv
import box
import yaml
import requests
import os
from pdfrag import PDF_Processor
import pdftools
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
                prompt = item['prompt']
                print(item['prompt'])
                pdf_action_prompt = f"Du bist ein hilfreicher Assistent. Der folgende TEXT enthält in dreifachen Anführungszeichen (''') einen Arbeitsauftrag in Bezug auf ein Dokument. Arbeitsaufträge können sein:\nZusammenfassen\nFrage beantworten\n\n. Bitte geben Sie nur den enthaltenen Arbeitsauftrag aus. Hier einige Beispiele:\nBei 'Bitte fassen Sie das Dokument zusammen.' wäre der Arbeitsauftrag 'Zusammenfassen'.\nBei 'Bitte beantworten Sie die folgende Frage.' wäre der Arbeitsauftrag 'Frage beantworten'.\nWenn ein Fragewort ('Wer','Was','Wie','Wo','Warum',...) enthalten ist, ist der Arbeitsauftrag eher 'Frage beantworten'. Wenn aber eine Frage an das ganze Dokument gestellt wird, dann ist der Arbeitsauftrag eher 'Zusammenfassen'. TEXT:'''{prompt}''' ASSISTANT: Arbeitsauftrag:"
                pdf_action = self.llm(pdf_action_prompt, temperature = 0.7, max_tokens = 128, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text']
                if 'Zusammenfassen' in pdf_action:
                    chain_elem['pdf_action'] = 'Zusammenfassen'
                else:
                    chain_elem['pdf_action'] = 'Frage beantworten'
                print(pdf_action)
                
                chain_elem['pdf_proc'] = proc
            chain_elem['instruction'] = item['prompt']
            chain_elem['action'] = item['action']
            self.chain.append(chain_elem)
        #self.run()

    def seperate_into_list(self,text):
        if '\n\n':
            text = text.split("\n\n")
            text = [i for i in text if i]
        else:
            if '\n' in text:    
                text = text.split("\n")
                text = [i for i in text if i]
            else:
                if ',' in text:
                    text = text.split(",")
                    text = [i for i in text if i]
        return text

    def run(self,create_callback,update_callback,status_callback,last_answer_callback,initialprompt = ""):
        #TODO: Nach jedem Schritt der chain zurück, für ggf. andere Aufträge. Handling von PDF-Zusammenfassung in diesem Zusammenhang gesondert.
        i = 0
        output = []
        last_content = ""
        while i < len(self.chain):
            create_callback(str(output))
            chain_elem = self.chain[i]
            print("CHAINSTEP " + str(i))
            if i == 0:
                if initialprompt:
                    prompt = f"Du bist ein hilfreicher Assistent. AUFTRAG: {chain_elem['instruction']}. EINGABE:{initialprompt}. "
                else:
                    prompt = f"Du bist ein hilfreicher Assistent. AUFTRAG: {chain_elem['instruction']}"

                if 'pdf_action' in chain_elem and 'pdf_proc' in chain_elem:
                    pdf_proc = chain_elem['pdf_proc']
                    if chain_elem['pdf_action'] == 'Zusammenfassen':
                        summarizer = pdftools.SimplePdfSummarizer(llm,pdf_proc,create_callback,update_callback,status_callback,cfg)
                        output = summarizer.run(False)
                    else:
                        output = pdf_proc.askPDF(chain_elem['instruction'])
                else:
                    output = self.llm(prompt, temperature = 0.7, max_tokens = 4096, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text'].strip()

                if chain_elem['action'] == 3:
                    output = self.seperate_into_list(output)
                    
                    
               
                print("PROMPT: " + str(prompt))
                print("OUTPUT: " + str(output))
            else:
                newoutput = []
                if isinstance(output, list):
                    if chain_elem['action'] == 1 or chain_elem['action'] == 3  : #map each elem to prompt, no support for further expasion yet
                        print("Elementwise Mapping")
                        for item in output:
                            if item:
                                item = str(item).strip()
                                prompt = f"Du bist ein hilfreicher Assistent. AUFTRAG: {chain_elem['instruction']}. EINGABE:{item}. "
                                print("PROMPT: " + str(prompt))
                                newresult = self.llm(prompt, temperature = 0.7, max_tokens = 4096, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text'].strip()
                                print("OUTPUT: " + str(newresult))
                                newoutput.append(newresult)
                    if chain_elem['action'] == 2: #reduce list to one
                        
                        fulltext = ""
                        for item in output:
                            fulltext += item + "\n" 
                        fulltext = fulltext.strip()
                        print("Reduce List")
                        prompt = f"Du bist ein hilfreicher Assistent. AUFTRAG: {chain_elem['instruction']}. EINGABE:{output}. "
                        print("PROMPT: " + str(prompt))
                        newoutput = self.llm(prompt, temperature = 0.7, max_tokens = 4096, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text'].strip()
                        print("OUTPUT: " + str(newoutput))

                else:
                    if chain_elem['action'] == 1 or chain_elem['action'] == 2: #reduce is like map without list
                        print("Reduce or map without list ")
                        f"Du bist ein hilfreicher Assistent. AUFTRAG: {chain_elem['instruction']}. EINGABE:{output}. "
                        print("PROMPT: " + str(prompt))
                        newoutput = self.llm(prompt, temperature = 0.7, max_tokens = 4096, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text'].strip()
                        print("OUTPUT: " + str(newoutput))
                    else: #expand
                        print("Expand without list ")
                        prompt = f"Du bist ein hilfreicher Assistent. AUFTRAG: {chain_elem['instruction']}. EINGABE:{output}. "
                        print("PROMPT: " + str(prompt))
                        newoutput = self.llm(prompt, temperature = 0.7, max_tokens = 4096, top_k=20, top_p=0.9,repeat_penalty=1.15)['choices'][0]['text'].strip()    
                        print("OUTPUT: " + str(newoutput))
                        if '\n' in newoutput:   
                            newoutput = newoutput.split("\n")
                            newoutput = [i for i in newoutput if i]    
                  
                output = newoutput
            i += 1
            
            
            update_callback(str(output))
            

        print(output)
        status_callback("finished")
