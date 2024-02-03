import yaml

class config:
    def __init__(self):
        self.config = {}
        with open('/config/config.yml', 'r') as file:
            config = yaml.safe_load(file)
    
    def store_config(self):
        with open('/config/config.yml', 'w') as file:
            yaml.dump(self.config,file)
    

    def get_config(self,section,key,default = None):
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return default
        
    def set_config(self,section,key,value):
        if section in self.config:
            self.config[section][key] = value
        else:
            self.config[section] = {key:value}
        
        