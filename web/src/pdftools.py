import threading
#import evaluate
from rouge_score import rouge_scorer
import os
import ast
class SimplePdfSummarizer():
    def __init__(self,llm,pdf_proc,create_callback,update_callback,status_callback,cfg):
        self.llm = llm
        self.create_callback = create_callback
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.content_gen = pdf_proc.getNodesContents()
        self.cfg = cfg
        #Info needed to summarize multiple pages until token limit
        self.total_tokens = 0
        self.total_text = ""
        self.names = []
        self.sources = []
    
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
        #set_break = False

        for text, name, source in self.content_gen:
            snippet_tokens = len(self.llm.tokenize(text.encode(encoding = 'UTF-8', errors = 'strict')))
            if snippet_tokens + self.total_tokens > int(os.getenv('NUMBER_OF_TOKENS_PDF',default=self.cfg.get_config('model','number_of_tokens_pdf',default=3800))):
                if not self.summarizeSnippet(self.total_text,self.names,self.sources):
                    break
                self.total_tokens = snippet_tokens
                self.total_text = text
                self.names = [name]
                self.sources = [source]
                return False                                
            else:
                self.total_tokens += snippet_tokens
                self.total_text += "\n" + text
                if not name in self.names:
                    self.names.append(name)
                self.sources.append(source)           
        
        self.summarizeSnippet(self.total_text,self.names,self.sources)
        self.status_callback("finished")
        return True

class AdvancedPdfSummarizer():
    def __init__(self,llm,pdf_proc,create_callback,update_callback,status_callback,cfg):
        self.llm = llm
        self.create_callback = create_callback
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.content_gen = pdf_proc.getNodesContents()
        self.cfg = cfg
        self.pdf_proc = pdf_proc
        #Info needed to summarize multiple pages until token limit
        self.total_tokens = 0
        self.total_text = ""
        self.names = []
        self.sources = []
        #Info for advanced summary quality
        
    
    def identifyGenre(self,snippet):
        prompt = f"Bitte bestimmen Sie, um welche Art von Text es sich bei dem folgenden Ausschnitt handelt:'''{snippet}'''. Um welche Art von Text handelt es sich? ASSISTANT:"
        genre = ""
        try:
            answer = self.llm(prompt, stream=True, temperature = 0.7, max_tokens = 512) #top_k=20, top_p=0.9,repeat_penalty=1.15)
                
            for answ in answer:
                res = answ['choices'][0]['text'] 
                genre += res
            print(genre)

        except Exception as error:
            print(error)
            genre = ""
        return genre

    def findHeading(self,snippet):
        heading = ""
        prompt = f"Bitte geben Sie dem folgenden Text eine treffende Überschrift:'''{snippet}'''. Wie sollte die Überschrift lauten? ASSISTANT:"
        try:
            answer = self.llm(prompt, stream=True, temperature = 0.7, max_tokens = 512) #top_k=20, top_p=0.9,repeat_penalty=1.15)
                
            for answ in answer:
                res = answ['choices'][0]['text'] 
                heading += res
            print(heading)

        except Exception as error:
            print(error)
            heading = ""
        return heading

    def summarizeSnippet(self,snippet,names,sources):
        
        heading = self.findHeading(snippet)
        genre = self.identifyGenre(snippet)
        response = ""
                         
        prompt = f"Ihre Aufgabe ist es, eine kurze Zusammenfassung des folgenden Textes der Gattung {genre} mit der Überschrift '''{heading}''' in maximal drei Sätzen zu schreiben. Schreiben Sie nichts, wenn es sich nur um ein Inhaltsverzeichnis oder bibliografische Informationen handelt. Der Text ist in dreifachen Aposthrophen '''TEXT''' eingefasst: '''{snippet}'''. Schreiben Sie eine Zusammenfassung in drei Sätzen in Markdown. ASSISTANT:"
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
        #set_break = False
        self.create_callback("")
        for text, name, source in self.content_gen:
            snippet_tokens = len(self.llm.tokenize(text.encode(encoding = 'UTF-8', errors = 'strict')))
            if snippet_tokens + self.total_tokens > int(os.getenv('NUMBER_OF_TOKENS_PDF',default=self.cfg.get_config('model','number_of_tokens_pdf',default=3800))):
                heading = self.findHeading(self.total_text)
                if not self.update_callback(heading +'\n'):
                    break
                self.total_text = text
                return False
            else:
                self.total_tokens += snippet_tokens
                self.total_text += "\n" + text               
        self.content_gen = self.pdf_proc.getNodesContents()
        self.total_tokens = 0
        self.total_text = ""
        for text, name, source in self.content_gen:
            snippet_tokens = len(self.llm.tokenize(text.encode(encoding = 'UTF-8', errors = 'strict')))
            if snippet_tokens + self.total_tokens > int(os.getenv('NUMBER_OF_TOKENS_PDF',default=self.cfg.get_config('model','number_of_tokens_pdf',default=3800))):
                if not self.summarizeSnippet(self.total_text,self.names,self.sources):
                    break
                self.total_tokens = snippet_tokens
                self.total_text = text
                self.names = [name]
                self.sources = [source]
                return False                                
            else:
                self.total_tokens += snippet_tokens
                self.total_text += "\n" + text
                if not name in self.names:
                    self.names.append(name)
                self.sources.append(source)           
        
        self.summarizeSnippet(self.total_text,self.names,self.sources)
        self.status_callback("finished")
        return True


class SimpleGraphExtractor():
    def __init__(self,llm,pdf_proc,create_callback,update_callback,status_callback,cfg):
        self.llm = llm
        self.create_callback = create_callback
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.content_gen = pdf_proc.getNodesContents()
        self.cfg = cfg
        #Info needed to summarize multiple pages until token limit
        self.total_tokens = 0
        self.total_text = ""
        self.names = []
        self.sources = []

    def extractGraph(self,snippet,names,sources):
        response = []
        self.create_callback(response)                    
        prompt = f"Sie sind ein Netzwerkgraphenersteller, der Begriffe aus einem gegebenen Kontext extrahiert. Sie erhalten ein Kontextstück (abgegrenzt durch '''). Ihre Aufgabe ist es, die Ontologie von Begriffen zu extrahieren, die in dem gegebenen Kontext erwähnt werden. Diese Begriffe sollten die Schlüsselkonzepte aus dem Kontext repräsentieren. \n "\
            "Gedanke 1: Denken Sie beim Durchgehen jedes Satzes an die darin erwähnten Schlüsselbegriffe. \n " \
            "\tDie Begriffe können Objekt, Einheit, Ort, Organisation, Person, \n " \
            "\tBedingung, Akronym, Dokumente, Dienstleistung, Konzept, usw.\n " \
            "\tBegriffe sollten so atomistisch wie möglich sein\n\n " \
            "Formatieren Sie Ihre Ausgabe als Liste []. Jedes Element der Liste enthält einen Begriff , wie folgt: \n" \
            "['Konzept 1', 'Konzept 2', …] \n "\
            "Kontext: '''{snippet}''' " 
        try:
            answer = self.llm(prompt, temperature = 0.1, max_tokens = 512) #top_k=20, top_p=0.9,repeat_penalty=1.15)
            
            try: 
                l = ast.literal_eval(answer['choices'][0]['text'])
                response.extend(l)
            except Exception as error:
                print(error)
                response = "An Error occured."
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
        #set_break = False

        for text, name, source in self.content_gen:
            snippet_tokens = len(self.llm.tokenize(text.encode(encoding = 'UTF-8', errors = 'strict')))
            if snippet_tokens + self.total_tokens > int(os.getenv('NUMBER_OF_TOKENS_PDF',default=self.cfg.get_config('model','number_of_tokens_pdf',default=3800))):
                if not self.extractGraph(self.total_text,self.names,self.sources):
                    break
                self.total_tokens = snippet_tokens
                self.total_text = text
                self.names = [name]
                self.sources = [source]
                return False                                
            else:
                self.total_tokens += snippet_tokens
                self.total_text += "\n" + text
                if not name in self.names:
                    self.names.append(name)
                self.sources.append(source)           
        
        self.extractGraph(self.total_text,self.names,self.sources)
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
                if not self.update_callback(response):
                    break
            except Exception as error:
                print(error)
                response = "An Error occured."
            self.update_callback(response+"(Vgl. "+name+":"+source+")")
                                            
        self.status_callback("finished")

