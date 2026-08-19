import json
import logging
from pathlib import Path

from app.schemas.document import DocumentStatus
from app.services.documents import DocumentService
from app.services.retrieval import RetrievedChunk
from app.utils.file_parser import Parser

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EVAL_PDF_PATH = FIXTURES_DIR / "Led_Zeppelin.pdf"
EVAL_QA_PATH = FIXTURES_DIR / "led_zeppelin_qa.json"
EVAL_DOC_FILENAME = "Led_Zeppelin.pdf"


async def get_or_create_eval_doc() -> str:
    """
    Return the document id of the eval fixture, uploading it once (idempotent
    across reruns) if it isn't already present in the database.
    """
    existing = await DocumentService.list_documents()
    for doc in existing:
        if doc.filename == EVAL_DOC_FILENAME and doc.status == DocumentStatus.ready:
            logger.info(f"Reusing existing eval document: {doc.id}")
            return doc.id

    logger.info("Eval document not found, creating it")
    content = EVAL_PDF_PATH.read_bytes()

    doc = await DocumentService.create_document(
        filename=EVAL_DOC_FILENAME,
        content_type="application/pdf",
        size=len(content),
    )

    raw_text = Parser.from_pdf(content)
    await DocumentService.create_chunks(raw_text=raw_text, parent_id=doc.id)
    await DocumentService.update_status(doc.id, DocumentStatus.ready)

    logger.info(f"Created eval document: {doc.id}")
    return doc.id


def load_qa_pairs() -> list[dict]:
    return json.loads(EVAL_QA_PATH.read_text())


def hit_at_k(retrieved: list[RetrievedChunk], relevant_indices: list[int]) -> bool:
    """True if at least one relevant chunk index is present in the retrieved set."""
    retrieved_indices = {c.index for c in retrieved}
    return bool(retrieved_indices & set(relevant_indices))
