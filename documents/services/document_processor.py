"""
Extract text from uploaded documents and split it into chunks suitable for
embedding and vector storage.

Supported formats
-----------------
* PDF  — via ``pypdf``
* DOCX / DOC — via ``docx2txt``
* TXT  — built-in file I/O

All extraction errors are raised as-is so the caller (the indexing service)
can handle them uniformly and record a meaningful error message on the
Document model.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

import docx2txt
from pypdf import PdfReader

from documents.services.chunking_service import ChunkingService

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Lightweight document processor: extract text → chunk → return structured
    chunk dicts.

    No LangChain dependency; uses ``pypdf`` and ``docx2txt`` directly.

    A module-level singleton (``document_processor``) is provided at the
    bottom of this file for convenience.
    """

    SUPPORTED_TYPES = frozenset({"pdf", "docx", "doc", "txt"})

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def extract_text(self, file_path: str, file_type: str) -> str:
        """
        Extract the full text content from a document file.

        Args:
            file_path: Absolute path to the local file.
            file_type: Extension *without* the leading dot, case-insensitive
                       (e.g. ``"pdf"``, ``"docx"``).

        Returns:
            The extracted text as a single string.  Pages / sections are
            separated by double newlines where applicable.

        Raises:
            ValueError:    If ``file_type`` is not in ``SUPPORTED_TYPES``.
            FileNotFoundError: If ``file_path`` does not exist.
            Exception:     Propagated from the underlying extraction library
                           on parse errors (e.g. corrupted file).
        """
        file_type = file_type.lower().lstrip(".")

        if file_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported file type: {file_type!r}. "
                f"Supported: {sorted(self.SUPPORTED_TYPES)}"
            )

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.debug(
            "Extracting text from document.",
            extra={"file_path": file_path, "file_type": file_type},
        )

        if file_type == "pdf":
            return self._extract_pdf(file_path)
        if file_type in ("docx", "doc"):
            return self._extract_docx(file_path)
        if file_type == "txt":
            return self._extract_txt(file_path)

        # Should be unreachable given the guard above, but keeps mypy happy.
        raise ValueError(f"Unhandled file type: {file_type!r}")

    def process_document(self, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """
        Full pipeline: extract text → chunk → return structured chunk list.

        Each item in the returned list is a dict with the following keys:

        * ``content``     (str)  — The chunk text.
        * ``chunk_index`` (int)  — Zero-based position of this chunk in the
                                    document.
        * ``token_count`` (int)  — Approximate word count (whitespace-split),
                                    used as a lightweight proxy for token count.
        * ``metadata``    (dict) — Extra information; currently contains
                                    ``source`` (the bare filename).

        Args:
            file_path: Absolute path to the local file.
            file_type: Extension without leading dot (e.g. ``"pdf"``).

        Returns:
            A list of chunk dicts.  Returns an empty list only when the
            extracted text is blank — callers should treat this as an error.

        Raises:
            ValueError:        On unsupported ``file_type`` or empty text.
            FileNotFoundError: If the file does not exist.
            Exception:         Propagated from text extraction on parse failure.
        """
        logger.info(
            "Starting document processing pipeline.",
            extra={"file_path": file_path, "file_type": file_type},
        )

        text = self.extract_text(file_path, file_type)

        if not text or not text.strip():
            logger.warning(
                "Text extraction returned empty content.",
                extra={"file_path": file_path, "file_type": file_type},
            )
            return []

        logger.debug(
            "Text extracted successfully.",
            extra={"file_path": file_path, "char_count": len(text)},
        )

        chunking_service = ChunkingService()
        raw_chunks = chunking_service.chunk_text(text)

        source_name = Path(file_path).name
        chunks = [
            {
                "content": chunk,
                "chunk_index": i,
                "token_count": len(chunk.split()),
                "metadata": {"source": source_name},
            }
            for i, chunk in enumerate(raw_chunks)
        ]

        logger.info(
            "Document processing complete.",
            extra={
                "file_path": file_path,
                "file_type": file_type,
                "num_chunks": len(chunks),
                "total_chars": len(text),
            },
        )
        return chunks

    # ──────────────────────────────────────────────────────────────────────────
    # Private extraction helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF using ``pypdf``.

        Each page's text is joined with double newlines.  Pages that yield no
        text (e.g. scanned images without OCR) contribute an empty string,
        which is later collapsed by the chunker's whitespace normalisation.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Extracted text string.

        Raises:
            pypdf.errors.PdfReadError: On corrupted or password-protected files.
        """
        reader = PdfReader(file_path)
        num_pages = len(reader.pages)
        logger.debug("PDF has %d page(s).", num_pages, extra={"file_path": file_path})

        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if not page_text.strip():
                logger.debug(
                    "PDF page %d yielded no text (possibly scanned image).",
                    page_number,
                    extra={"file_path": file_path, "page_number": page_number},
                )
            pages.append(page_text)

        return "\n\n".join(pages)

    def _extract_docx(self, file_path: str) -> str:
        """
        Extract text from a DOCX (or legacy DOC) file using ``docx2txt``.

        Args:
            file_path: Path to the DOCX/DOC file.

        Returns:
            Extracted text string.

        Raises:
            Exception: Propagated from ``docx2txt`` on parse failure.
        """
        return docx2txt.process(file_path)

    def _extract_txt(self, file_path: str) -> str:
        """
        Read a plain-text file.

        Files are assumed to be UTF-8 encoded.  A ``UnicodeDecodeError`` is
        raised (and propagated to the caller) if the encoding assumption fails.

        Args:
            file_path: Path to the TXT file.

        Returns:
            File contents as a string.

        Raises:
            UnicodeDecodeError: If the file is not valid UTF-8.
            OSError:            On I/O errors (permissions, etc.).
        """
        with open(file_path, "r", encoding="utf-8") as fh:
            return fh.read()


# Module-level singleton — import and use directly in other modules.
document_processor = DocumentProcessor()