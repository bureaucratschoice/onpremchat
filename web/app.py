from src.llm import build_llm
import requests
import json
print("start")
llm = build_llm()


from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any
import pickle
import os
from uuid import uuid4

from nicegui import app, ui
import frontend

import threading
import queue

class jobStatus():

    def __init__(self):
        self.jobsByToken = {}

    def addJob(self,token,uuid,prompt):
        try: 
            if token in self.jobsByToken:
                if uuid in self.jobsByToken[token]:
                    self.jobsByToken[token][uuid] = {'status':'queued','prompt':self.jobsByToken[token][uuid]['prompt'] + [prompt],'answer':self.jobsByToken[token][uuid]['answer']} 
                else:
                    self.jobsByToken[token][uuid] = {'status':'queued','prompt':[prompt],'answer':[]} 
            else:
                self.jobsByToken[token] = {uuid:{'status':'queued','prompt':[prompt],'answer':[]}} 
        except:
            return False
    def countQueuedJobs(self):
        try:
            counter = 0
            for token in self.jobsByToken:
                for uuid in self.jobsByToken[token]:
                    if 'status' in self.jobsByToken[token][uuid]:
                        if self.jobsByToken[token][uuid]['status'] == 'queued':
                            counter +=1
            return counter
        except:
            return 0

    def removeJob(self,token,uuid):
        try:
            if token in self.jobsByToken:
                if uuid in self.jobsByToken[token]:
                    del self.jobsByToken[token][uuid]
                    return True
            return False
        except:
            return False

    def superRemoveJob(self,uuid):
        try:
            if uuid == 'All':
                self.jobsByToken = {}
                return True
            else:
                for token in self.jobsByToken:
                    if uuid in self.jobsByToken[token]:
                        del self.jobsByToken[token][uuid]
                        return True
                return False
        except:
            return False
    
    def addAnswer(self,token,uuid,answer):
        try:
            if token in self.jobsByToken:
                if uuid in self.jobsByToken[token]:
                    if 'answer' in self.jobsByToken[token][uuid]:
                        self.jobsByToken[token][uuid]['answer'].append(answer)
                    else:
                        self.jobsByToken[token][uuid]['answer'] = [answer]
                    return True
            return False
        except:
            return False

    def updateAnswer(self,token,uuid,answer):
        try:
            if token in self.jobsByToken:
                if uuid in self.jobsByToken[token]:
                    if 'answer' in self.jobsByToken[token][uuid]:
                        self.jobsByToken[token][uuid]['answer'][-1] = answer
                    else:
                        self.jobsByToken[token][uuid]['answer'] = [answer]
                    return True
            return False
        except:
            return False
    
    
    def updateStatus(self,token,uuid,status):
        try:
            if token in self.jobsByToken:
                if uuid in self.jobsByToken[token]:
                    self.jobsByToken[token][uuid]['status'] = status
                    return True
            return False
        except:
            return False
    
    def getJobStatus(self,token,uuid):
        try:
            if token in self.jobsByToken:
                if uuid in self.jobsByToken[token]:
                    status = self.jobsByToken[token][uuid]
                    status['uuid'] = uuid
                    return self.jobsByToken[token][uuid]
            return {'uuid':'','status':'','prompt':[''],'answer':['']} 
        except:
            return False
    
    def getAllJobsForToken(self,token):
        try:
            if token in self.jobsByToken:
                return self.jobsByToken[token]
            return {'':{'status':'','prompt':[''],'answer':['']}} 
        except:
            return False

    def getAllStatus(self):
        try:
            result = {}
            for token in self.jobsByToken:
                result[token] = {}
                for uuid in self.jobsByToken[token]:
                    result[token][uuid] = {}
                    if 'status' in self.jobsByToken[token][uuid]:
                        result[token][uuid]['status'] = self.jobsByToken[token][uuid]['status']
            return result
        except:
            return False
            
  
class MainProcessor (threading.Thread):
    def __init__(self,taskLock,taskQueue):
        super().__init__(target="MainProcessor")
       
        self.taskLock = taskLock
        self.taskQueue = taskQueue
        
    def run(self):
        while True:
            job = self.taskQueue.get(block=True)
            jobStat.updateStatus(job['token'],job['uuid'],"processing")
            item = jobStat.getJobStatus(job['token'],job['uuid'])
            
            prompts = item['prompt']
            answers = []
            if 'answer' in item:
                answers = item['answer']
            
            i_p = 0
            i_a = 0
            instruction = ""
            while i_p < len(prompts):
                instruction += "USER:  " + prompts[i_p]
                if i_a < len(answers):
                    instruction += "ASSISTANT:  " + answers[i_a]
                i_p += 1
                i_a += 1
            
            if len(instruction) >= 2000:
                instruction = instruction[-2000:]
            prompt = f"Du bist ein hilfreicher Assistent. {instruction} ASSISTANT:"

            response = ""
            jobStat.addAnswer(job['token'],job['uuid'],response)
            try:
                answer = llm(prompt, stream=True, temperature = 0.7, max_tokens = 1024, top_k=20, top_p=0.9,repeat_penalty=1.15)
                
                for answ in answer:
                    res = answ['choices'][0]['text'] 
                    response += res
                    if not jobStat.updateAnswer(job['token'],job['uuid'],response):
                        break
            except:
                response = "An Error occured."
            jobStat.updateAnswer(job['token'],job['uuid'],response)            
            jobStat.updateStatus(job['token'],job['uuid'],"finished")





def dumpTokens(tokens):
    pickle.dump(tokens, open("/config/tokens.pickle", "wb"))

try:
    tokens = pickle.load(open("/config/tokens.pickle", "rb"))
except (OSError, IOError) as e:
    tokens = {}
    dumpTokens(tokens)

def generate_token(quota,description = ""):
    token = uuid4().hex
    tokens[token]={'quota':quota,'description':description}
    dumpTokens(tokens)
    return token

def revoke_token(token):
    if token in tokens:
        del(tokens[token])
        dumpTokens(tokens)
        return "OK"
    else:
        return "Token tot found"

def check_token(token):
    if token in tokens:
        if tokens[token]['quota'] == -1:
            return True
        if tokens[token]['quota'] > 0:
            tokens[token]['quota'] -= 1
            return True    
    return False

def token_details(token):
    if token in tokens:
        return tokens[token]
    return {'quota':0,'description':'Not existent'}

supertoken = os.getenv('SUPERTOKEN',default="PLEASE_CHANGE_THIS_PLEASE")




jobStat = jobStatus()

taskLock = threading.Lock()
taskQueue = queue.Queue(1000)

thread = MainProcessor(taskLock,taskQueue)
thread.start()






app = FastAPI()



class Item(BaseModel):
    prompt: str
    token: str

class TokenCreation(BaseModel):
    supertoken: str
    quota: int | None = 100
    description: str | None = "unknown" 

class TokenRevoke(BaseModel):
    supertoken: str
    token: str

class Status(BaseModel):
    token: str
    uuid: str | None = "All"



@app.post("/getStatus/")
async def get_status(status: Status) -> Any:
    if status.uuid == "All":
        stat = jobStat.getAllJobsForToken(status.token)
    else:
        stat = jobStat.getJobStatus(status.token,status.uuid)
    return stat

@app.post("/getAllStatus/")
async def get_status(status: Status) -> Any:
    if status.token == supertoken:
        return jobStat.getAllStatus()
    else:
        return {"result": "Acces denied."}

@app.post("/deleteJob/")
async def get_status(status: Status) -> Any:
    if status.token == supertoken:
        stat = jobStat.superRemoveJob(status.uuid)
        
        return stat
    else:
        return {"result": "Acces denied."}
    

@app.post("/createToken/")
async def create_token(token: TokenCreation) -> Any:
    if token.supertoken == supertoken:
        token = generate_token(token.quota,token.description)
        return {"token":token}
    else:
        return {"result": "Acces denied."}
    
@app.post("/revokeToken/")
async def create_token(token: TokenRevoke) -> Any:
    if token.supertoken == supertoken:
        result = revoke_token(token.token)
        return {"result": result}
    else:
        return {"result": "Acces denied."}

@app.post("/generate/")
async def generate_text(item: Item) -> Any:
    if(check_token(item.token)):
        uuid = uuid4().hex
        jobStat.addJob(item.token,uuid,item.prompt) 
        job = {'token':item.token,'uuid':uuid}
        try:
            taskQueue.put(job)
        except:
            jobStat.updateStatus(item.token,uuid,"failed")
        result = jobStat.getJobStatus(item.token,uuid)
    else:
        result = "Access denied."
    return result

frontend.init(app,jobStat,taskQueue)