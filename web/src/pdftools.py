class SimplePdfSummarizer(threading.Thread):
    def __init__(self,uuid,token,llm,pdf_proc,update_callback,finished_callback):
        super().__init__(target="SimplePDFSummarizer"+uuid)
        self.uuid = uuid
        self.token = token
        self.llm = llm
        self.pdf_proc = pdf_proc
        self.update_callback = update_callback
        self.finished_callback = finished_callback

    def run(self):
        for text, name, source in pdfProc.getNodesContents():
            response = ""
            self.update_callback(self.token,self.uuid,response)                    
            prompt = f"Ihre Aufgabe ist es, eine kurze Inhaltsangabe des folgenden Textes in maximal drei Sätzen zu schreiben. Schreiben Sie nichts, wenn es sich nur um ein Inhaltsverzeichnis oder bibliografische Informationen handelt. Der Text ist in dreifachen Aposthrophen '''TEXT''' eingefasst: '''{text}'''. Schreiben Sie eine kurze Inhaltsangabe in maximal drei Sätzen. ASSISTANT:"
            try:
                answer = self.llm(prompt, stream=True, temperature = 0.1, max_tokens = 512) #top_k=20, top_p=0.9,repeat_penalty=1.15)
                
                for answ in answer:
                    res = answ['choices'][0]['text'] 
                    response += res
                    if not self.update_callback(self.token,self.uuid,response):
                        break
            except Exception as error:
                print(error)
                response = "An Error occured."
            self.update_callback(self.token,self.uuid,response+"(Vgl. "+name+":"+source+")")
                                            
        self.finished_callback(self.token,self.uuid)

class SimplePdfTopicModeller(threading.Thread):
    def __init__(self,uuid,token,llm,pdf_proc,update_callback,finished_callback):
        super().__init__(target="SimplePdfTopicModeller"+uuid)
        self.uuid = uuid
        self.token = token
        self.llm = llm
        self.pdf_proc = pdf_proc
        self.update_callback = update_callback
        self.finished_callback = finished_callback

    def run(self):
        for text, name, source in pdfProc.getNodesContents():
            response = ""
            self.update_callback(self.token,self.uuid,response)                    
            prompt = f"Ihre Aufgabe ist es, die Themen aufzulisten, die wesentlich für den folgenden Text sind. Schreiben Sie maximal drei Themen auf. Schreiben Sie nichts, wenn es sich um ein Inhaltsverzeichnis oder bibliografische Informationen handelt. Der Text ist in dreifachen Aposthrophen '''TEXT''' eingefasst. Ihre Antwort soll als Python-Liste ausgegeben werden, etwa ['Demographie','Fussball','Altenpflege']: '''{text}'''. Schreiben Sie maximal drei wesentliche Themen des Textes als Python-Liste []. ASSISTANT:"
            try:
                answer = self.llm(prompt, stream=False, temperature = 0.1, max_tokens = 512) #top_k=20, top_p=0.9,repeat_penalty=1.15)
                
                print(answer['choices'][0]['text'])

                if not self.update_callback(self.token,self.uuid,response):
                    break
            except Exception as error:
                print(error)
                response = "An Error occured."
            self.update_callback(self.token,self.uuid,response+"(Vgl. "+name+":"+source+")")
                                            
        self.finished_callback(self.token,self.uuid)

