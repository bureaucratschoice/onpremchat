from llama_index.core.prompts.base import ChatPromptTemplate

#from llama_index.core import ChatPromptTemplate

class RoleToggle:
    """
    A class to toggle between two roles: 'user' and 'assistant'.
    """
    def __init__(self, user: str, assistant: str):
        self.user = user
        self.assistant = assistant
        self._acting = self.user  # Start with the user role.

    def toggle(self) -> str:
        """Toggles the current role between 'user' and 'assistant'."""
        previous_role = self._acting
        self._acting = self.assistant if self._acting == self.user else self.user
        return previous_role

class FriendlyFormatter:
    def interleave_prompts_answers(self, prompts, answers):
        combined = []
        for i in range(len(prompts)):
            combined.append(prompts[i])
            if i < len(answers):  # Ensure we don't go out of bounds for answers
                combined.append(answers[i])
        return combined

    def format(self, item, sysprompt):
        toggle = RoleToggle("user", "assistant")
        prompts = item.get('prompt', [])
        answers = item.get('answer', [])
        
        messages = [("system", sysprompt)]
        for message in self.interleave_prompts_answers(prompts, answers):
            messages.append((toggle.toggle(), message))
        
        return ChatPromptTemplate.from_messages(messages)
