from llama_index.prompts import PromptTemplate

class PromptFomater():
    
    def llama_prompt(self,sysprompt,prompts,answers):
        i_p = 0
        i_a = 0
        prompt = ""
        prompt += f"<|system|>\n{sysprompt}</s>\n"
        while i_p < len(prompts):
            prompt += f"<|user|>\n{prompts[i_p]}</s>\n"

            if i_a < len(answers):
                prompt += f"<|assistant|>\n{answers[i_a]}</s>\n"
            i_p += 1
            i_a += 1
        prompt = prompt + "<|assistant|>\n"
        return prompt

    def llama3_prompt(self,sysprompt,prompts,answers):
        i_p = 0
        i_a = 0
        prompt = "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        prompt += f"{sysprompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
        while i_p < len(prompts):
            prompt += f"{prompts[i_p]}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

            if i_a < len(answers):
                prompt += f"{answers[i_a]}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
            i_p += 1
            i_a += 1
        print(prompt)
        return prompt

    def leo_mistral_prompt(self,sysprompt,prompts,answers):
        i_p = 0
        i_a = 0    
        prompt = ""
        while i_p < len(prompts):
            prompt += "USER:  " + prompts[i_p]
            if i_a < len(answers):
                prompt += "ASSISTANT:  " + answers[i_a]
            i_p += 1
            i_a += 1
                            
        prompt = f"{sysprompt} {prompt} ASSISTANT:"    
        return prompt

    def format(self,item,sysprompt,pformat):
        prompts = item['prompt']
        answers = []
        if 'answer' in item:
            answers = item['answer']

        if pformat == 'llama3':
            prompt = self.llama3_prompt(sysprompt,prompts,answers)
        else:
            prompt = self.leo_mistral_prompt(sysprompt,prompts,answers)

        prompt = PromptTemplate(prompt)        
        return prompt