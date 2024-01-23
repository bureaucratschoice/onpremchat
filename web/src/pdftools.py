import threading
#import evaluate
from rouge_score import rouge_scorer
import os
class SimplePdfSummarizer():#threading.Thread):
    def __init__(self,llm,pdf_proc,create_callback,update_callback,status_callback):
        #super().__init__(target="SimplePDFSummarizer")
        self.llm = llm
        self.create_callback = create_callback
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.content_gen = pdf_proc.getNodesContents()
    
    def summarizeSnippet(self,snippet,names,sources):
        response = ""
        self.create_callback(response)                    
        prompt = f"Ihre Aufgabe ist es, eine kurze Inhaltsangabe des folgenden Textes in maximal drei Sätzen zu schreiben. Schreiben Sie nichts, wenn es sich nur um ein Inhaltsverzeichnis oder bibliografische Informationen handelt. Der Text ist in dreifachen Aposthrophen '''TEXT''' eingefasst: '''{snippet}'''. Schreiben Sie eine kurze Inhaltsangabe in maximal drei Sätzen. ASSISTANT:"
        try:
            answer = self.llm(prompt, stream=True, temperature = 0.1, max_tokens = 512) #top_k=20, top_p=0.9,repeat_penalty=1.15)
                
            for answ in answer:
                res = answ['choices'][0]['text'] 
                response += res
                if not self.update_callback(response):
                    return False
        except Exception as error:
            print(error)
            response = "An Error occured."

        scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
        scores = scorer.score(snippet,response)
        rouge1 = scores['rouge1'].fmeasure

        self.update_callback(response+" (Vgl. "+str(names)+":"+str(sources[0]+"-"+sources[-1])+") (Score: "+str(round(rouge1,2))+")")
        return True


    def run(self):
        set_break = False
        total_tokens = 0
        total_text = ""
        names = []
        sources = []
        for text, name, source in self.content_gen():
            snippet_tokens = len(self.llm.tokenize(text.encode(encoding = 'UTF-8', errors = 'strict')))
            if snippet_tokens + total_tokens > int(os.getenv('NUMBER_OF_TOKENS_PDF',default=3800)):
                ##TODO Store current text for next round. Best at and of branch
                if not self.summarizeSnippet(total_text,names,sources):
                    break
                total_tokens = snippet_tokens
                total_text = text
                names = [name]
                sources = [source]
                return False                                
            else:
                total_tokens += snippet_tokens
                total_text += "\n" + text
                if not name in names:
                    names.append(name)
                sources.append(source)           
        
        self.summarizeSnippet(total_text,names,sources)
        self.status_callback("finished")
        return True

class SimplePdfTopicModeller(threading.Thread):
    def __init__(self,llm,pdf_proc,create_callback,update_callback,status_callback):
        super().__init__(target="SimplePdfTopicModeller")
        self.llm = llm
        self.pdf_proc = pdf_proc
        self.create_callback = create_callback
        self.update_callback = update_callback
        self.status_callback = status_callback

    def run(self):
        for text, name, source in self.pdf_proc.getNodesContents():
            response = ""
            self.create_callback(response)                    
            prompt = f"Ihre Aufgabe ist es, die Themen aufzulisten, die wesentlich für den folgenden Text sind. Schreiben Sie maximal drei Themen auf. Schreiben Sie nichts, wenn es sich um ein Inhaltsverzeichnis oder bibliografische Informationen handelt. Der Text ist in dreifachen Aposthrophen '''TEXT''' eingefasst. Ihre Antwort soll als Python-Liste ausgegeben werden, etwa ['Demographie','Fussball','Altenpflege']: '''{text}'''. Schreiben Sie maximal drei wesentliche Themen des Textes als Python-Liste []. ASSISTANT:"
            try:
                answer = self.llm(prompt, stream=False, temperature = 0.1, max_tokens = 512, top_k=20) #top_k=20, top_p=0.9,repeat_penalty=1.15)
                
                print(answer['choices'][0]['text'])

                if not self.update_callback(response):
                    break
            except Exception as error:
                print(error)
                response = "An Error occured."
            self.update_callback(response+"(Vgl. "+name+":"+source+")")
                                            
        self.status_callback("finished")

