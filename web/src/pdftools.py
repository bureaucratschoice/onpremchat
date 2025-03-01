import os
from rouge_score import rouge_scorer  # noqa: F401
import threading  # Remove if unused
import ast      # Remove if unused


class SimplePdfSummarizer:
    """
    A simple PDF summarizer that processes text content and generates summaries.
    """

    def __init__(self, llm, pdf_proc, create_callback, update_callback, status_callback, cfg):
        """
        Initializes the summarizer.

        Args:
            llm: Language model interface.
            pdf_proc: PDF processor with method `get_nodes_contents()`.
            create_callback: Function to create an initial response.
            update_callback: Function to update the response.
            status_callback: Function to update the summarization status.
            cfg: Configuration object.
        """
        self.llm = llm
        self.create_callback = create_callback
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.content_gen = pdf_proc.get_nodes_contents()
        self.cfg = cfg

        # Information needed to summarize multiple pages until the token limit is reached
        self.total_tokens = 0
        self.total_text = ""
        self.names = []
        self.sources = []

    def summarize_snippet(self, snippet, names, sources):
        """
        Summarizes a given text snippet using the language model.

        Args:
            snippet (str): The text snippet to summarize.
            names (list): List of names associated with the snippet.
            sources (list): List of source information.

        Returns:
            bool: True if the summarization completed successfully, False otherwise.
        """
        response = ""
        self.create_callback(response)

        prompt = (
            "Ihre Aufgabe ist es, eine kurze Inhaltsangabe des folgenden Textes in maximal drei Sätzen zu schreiben. "
            "Schreiben Sie nichts, wenn es sich nur um ein Inhaltsverzeichnis oder bibliografische Informationen handelt. "
            f"Der Text ist in dreifachen Aposthrophen '''TEXT''' eingefasst: '''{snippet}'''. "
            "Schreiben Sie eine kurze Inhaltsangabe in maximal drei Sätzen. ASSISTANT:"
        )

        try:
            answer = self.llm.stream_complete(prompt)  # e.g., top_k=20, top_p=0.9, repeat_penalty=1.15
            for answ in answer:
                res = answ.delta  # Alternatively, use answ['choices'][0]['text'] if applicable.
                response += res
                if not self.update_callback(response):
                    return False
        except Exception as error:
            print(error)
            response = "An Error occurred."

        # Optional: Calculate ROUGE scores if needed.
        # scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
        # scores = scorer.score(snippet, response)
        # rouge1 = scores['rouge1'].fmeasure

        summary_meta = f" (Vgl. {names}:{sources[0]}-{sources[-1]})"
        self.update_callback(response + summary_meta)
        return True

    def run(self):
        """
        Processes content and summarizes snippets based on token limits.

        Returns:
            bool: True if the summarization process finishes, False if stopped early.
        """
        for text, name, source in self.content_gen:
            # Estimate tokens using a word count multiplied by a factor
            snippet_tokens = len(text.split(" ")) * 2

            # Retrieve token limit from environment variable or configuration
            token_limit = int(
                os.getenv(
                    'NUMBER_OF_TOKENS_PDF',
                    default=self.cfg.get_config('model', 'number_of_tokens_pdf', default=3800)
                )
            )

            if snippet_tokens + self.total_tokens > token_limit:
                if not self.summarize_snippet(self.total_text, self.names, self.sources):
                    break
                # Reset accumulators after summarizing a batch of text
                self.total_tokens = snippet_tokens
                self.total_text = text
                self.names = [name]
                self.sources = [source]
                return False
            else:
                self.total_tokens += snippet_tokens
                self.total_text += "\n" + text
                if name not in self.names:
                    self.names.append(name)
                self.sources.append(source)

        self.summarize_snippet(self.total_text, self.names, self.sources)
        self.status_callback("finished")
        return True
