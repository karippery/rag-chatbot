import logging
from typing import List, Dict
from pathlib import Path

from pypdf import PdfReader
import docx2txt

from documents.services.chunking_service import ChunkingService



logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Lightweight document processor without LangChain.
    Supports PDF, DOCX, TXT.
    """

    SUPPORTED_TYPES = {"pdf", "docx", "doc", "txt"}

    def extract_text(self, file_path: str, file_type: str) -> str:

        file_type = file_type.lower()

        if file_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported file type: {file_type}")

        if file_type == "pdf":
            return self._extract_pdf(file_path)

        if file_type in ("docx", "doc"):
            return self._extract_docx(file_path)

        if file_type == "txt":
            return self._extract_txt(file_path)

        raise ValueError("Unsupported type")


    def _extract_pdf(self, file_path: str) -> str:

        reader = PdfReader(file_path)

        pages = []

        for page_number, page in enumerate(reader.pages):

            text = page.extract_text() or ""

            pages.append(text)

        return "\n\n".join(pages)


    def _extract_docx(self, file_path: str) -> str:

        return docx2txt.process(file_path)


    def _extract_txt(self, file_path: str) -> str:

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


    def process_document(
        self,
        file_path: str,
        file_type: str
    ) -> List[Dict]:

        """
        Full pipeline:
        extract text → chunk → return structured chunks
        """

        text = self.extract_text(file_path, file_type)

        chunking_service = ChunkingService()

        chunks = chunking_service.chunk_text(text)

        formatted = []

        for i, chunk in enumerate(chunks):

            formatted.append({

                "content": chunk,

                "chunk_index": i,

                "token_count": len(chunk.split()),

                "metadata": {
                    "source": Path(file_path).name,
                }
            })

        logger.info(f"Created {len(formatted)} chunks")

        return formatted


document_processor = DocumentProcessor()
