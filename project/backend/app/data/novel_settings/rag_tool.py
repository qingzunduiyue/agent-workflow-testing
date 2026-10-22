from functools import lru_cache
from pathlib import Path
from langchain_core.tools import tool
from app.core.config import settings

DOCS_DIR = Path(__file__).resolve().parent

@lru_cache(maxsize=1)
def get_retriever():
    # Heavy optional dependencies and the embedding model are loaded only on use.
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    persist = Path(settings.CHROMA_PERSIST_DIR)
    if persist.exists() and any(persist.iterdir()):
        vectorstore = Chroma(persist_directory=str(persist), embedding_function=embeddings)
    else:
        documents = []
        for path in sorted(DOCS_DIR.iterdir()):
            if path.suffix.lower() in {'.txt', '.md'}:
                documents.append(Document(page_content=path.read_text(encoding='utf-8'), metadata={'source': path.name}))
            elif path.suffix.lower() == '.docx':
                import docx2txt
                documents.append(Document(page_content=docx2txt.process(str(path)), metadata={'source': path.name}))
        if not documents:
            raise RuntimeError('知识库目录为空，请添加 txt、md 或 docx 文档')
        chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(documents)
        vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory=str(persist))
    return vectorstore.as_retriever(search_kwargs={'k': 3})

@tool
def retrieve_novel_settings(query: str) -> str:
    """检索小说背景资料，返回带有来源文件名的原文片段。"""
    results = get_retriever().invoke(query)
    if not results:
        return '未检索到相关设定，请明确告知用户没有检索依据。'
    return '\n\n'.join(f"【来源文件：{Path(doc.metadata.get('source', '未知')).name}】\n{doc.page_content}" for doc in results)
