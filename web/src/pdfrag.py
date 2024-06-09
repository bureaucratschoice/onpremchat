from llama_index.embeddings import HuggingFaceEmbedding
from llama_index.llms import LlamaCPP
from llama_index import ServiceContext
from llama_index.vector_stores import SimpleVectorStore
from llama_hub.file.pymu_pdf.base import PyMuPDFReader
from llama_index import SimpleDirectoryReader
from llama_index.node_parser.text import SentenceSplitter
from llama_index.schema import TextNode
from llama_index.vector_stores import VectorStoreQuery
from llama_index.schema import NodeWithScore
from typing import Optional
from llama_index import QueryBundle
from llama_index.retrievers import BaseRetriever
from typing import Any, List
from llama_index.query_engine import RetrieverQueryEngine
import os
import shutil




        

class OwnRetriever(BaseRetriever):
    """Retriever over a simple vector store."""

    def __init__(
        self,
        vector_store: SimpleVectorStore,
        embed_model: Any,
        nodes: List,
        query_mode: str = "default",
        similarity_top_k: int = 2,
        
    ) -> None:
        """Init params."""
        self._vector_store = vector_store
        self._embed_model = embed_model
        self._nodes = nodes
        self._query_mode = query_mode
        self._similarity_top_k = similarity_top_k
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieve."""
        query_embedding = self._embed_model.get_query_embedding(
            query_bundle.query_str
        )
        vector_store_query = VectorStoreQuery(
            query_embedding=query_embedding,
            similarity_top_k=self._similarity_top_k,
            mode=self._query_mode,
        )
        query_result = self._vector_store.query(vector_store_query)
        if query_result.nodes == None:
          query_result.nodes = []
          for id in query_result.ids:
            for node in self._nodes:
              if node.node_id == id :
                query_result.nodes.append(node)
        nodes_with_scores = []
        for index, node in enumerate(query_result.nodes):
            score: Optional[float] = None
            if query_result.similarities is not None:
                score = query_result.similarities[index]
            nodes_with_scores.append(NodeWithScore(node=node, score=score))

        return nodes_with_scores

    def retrieve(self,query_str):
        query_embedding = self._embed_model.get_query_embedding(query_str)
        vector_store_query = VectorStoreQuery(
            query_embedding=query_embedding,
            similarity_top_k=self._similarity_top_k,
            mode=self._query_mode,
        )
        query_result = self._vector_store.query(vector_store_query)
        if query_result.nodes == None:
          query_result.nodes = []
          for id in query_result.ids:
            for node in self._nodes:
              if node.node_id == id :
                query_result.nodes.append(node)
        nodes_with_scores = []
        for index, node in enumerate(query_result.nodes):
            score: Optional[float] = None
            if query_result.similarities is not None:
                score = query_result.similarities[index]
            nodes_with_scores.append(NodeWithScore(node=node, score=score))

        return nodes_with_scores

class PDF_Processor():
    def __init__(self, cfg, llm):

        self.embed_model = HuggingFaceEmbedding()

        
        self.llm = llm

    

        self.service_context = ServiceContext.from_defaults(
        llm=self.llm, embed_model=self.embed_model
        )

        self.vector_store = SimpleVectorStore()
        self.text_parser = SentenceSplitter(
            chunk_size=3900,
            # separator=" ",
        )

        self.nodes = []
        self.filepathes = []
        self.last_response = ""

    def get_num_tokens(self,str):
        #return self.llm.get_num_tokens(str)
        return len(str.split(" "))
    def removeFiles(self):
        for filepath in self.filepathes:
            if os.path.isdir(filepath):
                
                try:
                    if filepath.startswith('/tmp/'):
                        shutil.rmtree(filepath)
                except:
                    pass
            if os.path.isfile(filepath):
                try:
                    if filepath.startswith('/tmp/'):
                        os.remove(filepath)
                except:
                    pass

    def remove(self,filepath):
        
        if os.path.isdir(filepath):
                
            try:
                if filepath.startswith('/tmp/'):
                    shutil.rmtree(filepath)
            except:
                return False
        if os.path.isfile(filepath):
            try:
                if filepath.startswith('/tmp/'):
                    os.remove(filepath)
            except:
                return False
        return True
            

    def processDirectory(self, path):
        loader = SimpleDirectoryReader(input_dir=path)
        documents = loader.load_data()
        self.filepathes.append(path)
        self.processDocs(documents)
        self.remove(path)

    def processDocs(self,documents):
        text_chunks = []
        # maintain relationship with source doc index, to help inject doc metadata in (3)
        doc_idxs = []
        for doc_idx, doc in enumerate(documents):
            cur_text_chunks = self.text_parser.split_text(doc.text)
            text_chunks.extend(cur_text_chunks)
            doc_idxs.extend([doc_idx] * len(cur_text_chunks))

        nodes = []
        for idx, text_chunk in enumerate(text_chunks):
            node = TextNode(
                text=text_chunk,
            )
            src_doc = documents[doc_idxs[idx]]
            node.metadata = src_doc.metadata
            nodes.append(node)

        for node in nodes:
            node_embedding = self.embed_model.get_text_embedding(
                node.get_content(metadata_mode="all")
            )
            node.embedding = node_embedding
        
        self.vector_store.add(nodes)
        
        self.nodes.extend(nodes)

    def processPDF(self,filepath):
        loader = PyMuPDFReader()
        documents = loader.load(file_path=filepath)
        self.filepathes.append(filepath)
        self.processDocs(documents)
        self.remove(filepath)

    def askPDF(self,question):
        retriever = OwnRetriever(
            self.vector_store, self.embed_model, self.nodes, query_mode="default", similarity_top_k=3
        )
        query_engine = RetrieverQueryEngine.from_args(
            retriever, service_context=self.service_context, streaming = True
        )
        response = query_engine.query(question,)
        self.last_response = response
        return response.response_gen

    def getTopSimilar(self,question,top_k=1):
        retriever = OwnRetriever(
            self.vector_store, self.embed_model, self.nodes, query_mode="default", similarity_top_k=top_k
        )
        nodes_with_scores = retriever.retrieve(question)
        return nodes_with_scores

    def getLastResponseMetaData(self):
        if self.last_response:
            metadatas = []
            for node in self.last_response.source_nodes:
                metadatas.append(node.metadata)
            return metadatas
        return False
            
    def getNodesContents(self):
        for node in self.nodes:
            content = node.get_content()
            
            name = str(node.metadata['file_path']) if 'file_path' in node.metadata else 'unknown'
            if '/' in name:
                name = name.split('/')[-1]
            if 'source' in node.metadata:
                source = str(node.metadata['source'])
            else:
                if 'page_label' in node.metadata:
                    source = str(node.metadata['page_label']) 
                else: 
                    source = '?'
            yield content, name, source


