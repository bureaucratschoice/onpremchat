import pickle
import os
from datetime import date

class Statistic():
    def __init__(self):
        self.stat = {}
        self.load()

    def load(self):
        try:
            self.stat = pickle.load(open("/config/statistic.pickle", "rb"))
        except (OSError, IOError) as e:
            self.stat = {
                'visit':{'dates':[],'values':[]},
                'chat':{'dates':[],'values':[]},
                'pdf_question':{'dates':[],'values':[]},
                'pdf_summary':{'dates':[],'values':[]},
                'max_queue':{'dates':[],'values':[]}
            }
            self.dumpStat()
    
    def dumpStat(self):
        try:
            pickle.dump(self.stat, open("/config/statistic.pickle", "wb"))
        except (OSError, IOError) as e:
            print("Error on dumping statistic")

    def updateQueueSize(self,size,event='max_queue'):
        if event in self.stat and 'dates' in self.stat[event] and 'values' in self.stat[event] and self.stat[event]['dates'] and self.stat[event]['values']:
            if self.stat[event]['dates'][-1] == date.today() and self.stat[event]['values'][-1] < size :
                self.stat[event]['values'][-1] = size
            else:
                self.stat[event]['dates'].append(date.today())
                self.stat[event]['values'].append(size)
        else:
            self.stat[event] = {'dates':[date.today()],event:[size]}
        self.dumpStat()
    def addEvent(self,event):
        if event in self.stat and 'dates' in self.stat[event] and 'values' in self.stat[event] and self.stat[event]['dates'] and self.stat[event]['values']:
            if self.stat[event]['dates'][-1] == date.today():
                self.stat[event]['values'][-1] += 1
            else:
                self.stat[event]['dates'].append(date.today())
                self.stat[event]['values'].append(1)
        else:
            self.stat[event] = {'dates':[date.today()],'values':[1]}
        self.dumpStat()

    def getEventStat(self,event):
        if event in self.stat and 'dates' in self.stat[event] and 'values' in self.stat[event] and self.stat[event]['dates'] and self.stat[event]['values']:
            return self.stat[event]['dates'],self.stat[event]['values']
        return [date.today()], [0]
    