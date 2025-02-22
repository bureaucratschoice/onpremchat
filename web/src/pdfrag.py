import os
import shutil
from typing import Any, List, Optional, Generator, Union

# Updated imports using the new Settings-based configuration.
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.core import QueryBundle
from llama_index.core import Settings  # Instead of ServiceContext
from llama_index.core.vector_stores import SimpleVectorStore, VectorStoreQuery
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.readers.file.pymu_pdf import PyMuPDFReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.query_engine.retriever_query_engine import RetrieverQueryEngine


class CustomRetriever(BaseRetriever):
    """
    A custom retriever that searches the vector store using text embeddings.
    Implements both the abstract _retrieve method and a public retrieve method that
    can accept either a string or a QueryBundle.
    """
    def __init__(
        self,
        vector_store: Any,
        embed_model: Any,
        nodes: List[TextNode],
        query_mode: str = "default",
        similarity_top_k: int = 2,
    ) -> None:
        self.vector_store = vector_store
        self.embed_model = embed_model
        self.nodes = nodes
        self.query_mode = query_mode
        self.similarity_top_k = similarity_top_k

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Required abstract method from BaseRetriever.
        Delegates to the public retrieve method after extracting the query string.
        """
        return self.retrieve(query_bundle)

    def retrieve(self, query: Union[str, QueryBundle]) -> List[NodeWithScore]:
        """
        Retrieve nodes that are most similar to the input query.
        If a QueryBundle is provided, extract its query_str.
        """
        # Ensure we have a string query.
        if isinstance(query, QueryBundle):
            query = query.query_str

        query_embedding = self.embed_model.get_query_embedding(query)
        vector_store_query = VectorStoreQuery(
            query_embedding=query_embedding,
            similarity_top_k=self.similarity_top_k,
            mode=self.query_mode,
        )
        query_result = self.vector_store.query(vector_store_query)

        # If nodes are not populated, resolve them using the IDs.
        if query_result.nodes is None:
            query_result.nodes = [
                node for node_id in query_result.ids
                for node in self.nodes
                if node.node_id == node_id
            ]

        nodes_with_scores: List[NodeWithScore] = []
        for idx, node in enumerate(query_result.nodes):
            score: Optional[float] = (
                query_result.similarities[idx]
                if query_result.similarities and idx < len(query_result.similarities)
                else None
            )
            nodes_with_scores.append(NodeWithScore(node=node, score=score))
        return nodes_with_scores


class DocumentProcessor:
    """
    Processes documents (from PDFs or directories), converts them into text nodes with embeddings,
    and supports query-based retrieval over the processed content.
    """
    def __init__(self, llm: Any, chunk_size: int = 3900):
        # Optionally, you can use global Settings here if you want to override the defaults.
        self.embed_model = HuggingFaceEmbedding()
        self.llm = llm
        self.vector_store = SimpleVectorStore()
        self.text_parser = SentenceSplitter(chunk_size=chunk_size)
        self.nodes: List[TextNode] = []
        self.filepaths: List[str] = []
        self.last_response: Optional[Any] = None

    @staticmethod
    def get_num_tokens(text: str) -> int:
        """
        Approximate token count based on splitting on whitespace.
        """
        return len(text.split())

    @staticmethod
    def _remove_path(path: str) -> bool:
        """
        Remove a file or directory if it resides in a temporary location (e.g., /tmp).
        """
        if not path.startswith('/tmp/'):
            return False
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
            return True
        except Exception:
            return False

    def cleanup_paths(self) -> None:
        """
        Remove all stored temporary file paths.
        """
        for path in self.filepaths:
            self._remove_path(path)
        self.filepaths.clear()

    def process_directory(self, directory: str) -> None:
        """
        Load and process all documents from a given directory.
        """
        loader = SimpleDirectoryReader(input_dir=directory)
        documents = loader.load_data()
        self.filepaths.append(directory)
        self._process_documents(documents)
        self._remove_path(directory)

    def process_pdf(self, filepath: str) -> None:
        """
        Load and process a PDF file.
        """
        loader = PyMuPDFReader()
        documents = loader.load(file_path=filepath)
        self.filepaths.append(filepath)
        self._process_documents(documents)
        self._remove_path(filepath)

    def _process_documents(self, documents: List[Any]) -> None:
        """
        Splits document texts into chunks, creates TextNodes, computes embeddings,
        and adds them to the vector store.
        """
        text_chunks: List[str] = []
        doc_indices: List[int] = []
        for idx, doc in enumerate(documents):
            chunks = self.text_parser.split_text(doc.text)
            text_chunks.extend(chunks)
            doc_indices.extend([idx] * len(chunks))

        new_nodes: List[TextNode] = []
        for chunk, idx in zip(text_chunks, doc_indices):
            node = TextNode(text=chunk)
            node.metadata = documents[idx].metadata
            new_nodes.append(node)

        # Compute embeddings for each node and add them to the vector store.
        for node in new_nodes:
            node.embedding = self.embed_model.get_text_embedding(
                node.get_content(metadata_mode="all")
            )
        self.vector_store.add(new_nodes)
        self.nodes.extend(new_nodes)

    def ask(self, question: str) -> Any:
        """
        Query the processed documents with the given question and return the LLM response.
        """
        retriever = CustomRetriever(
            vector_store=self.vector_store,
            embed_model=self.embed_model,
            nodes=self.nodes,
            query_mode="default",
            similarity_top_k=3
        )
        query_engine = RetrieverQueryEngine.from_args(retriever, llm=self.llm, streaming=True)
        response = query_engine.query(question)
        self.last_response = response
        return response.response_gen

    def get_top_similar(self, question: str, top_k: int = 1) -> List[NodeWithScore]:
        """
        Return the top similar nodes for a given question.
        """
        retriever = CustomRetriever(
            vector_store=self.vector_store,
            embed_model=self.embed_model,
            nodes=self.nodes,
            query_mode="default",
            similarity_top_k=top_k
        )
        return retriever.retrieve(question)

    def get_last_response_metadata(self) -> Optional[List[Any]]:
        """
        Retrieve metadata from the source nodes of the last response.
        """
        if self.last_response and hasattr(self.last_response, "source_nodes"):
            return [node.metadata for node in self.last_response.source_nodes]
        return None

    def get_nodes_contents(self) -> Generator[tuple[str, str, str], None, None]:
        """
        Generator yielding (content, filename, source) for each node.
        """
        for node in self.nodes:
            content = node.get_content()
            filename = str(node.metadata.get('file_path', 'unknown'))
            if '/' in filename:
                filename = filename.split('/')[-1]
            source = str(node.metadata.get('source', node.metadata.get('page_label', '?')))
            yield content, filename, source
