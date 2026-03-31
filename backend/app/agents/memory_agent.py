import google.generativeai as genai
import ulid
from typing import Dict, Any
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent import AgentContext

logger = logging.getLogger(__name__)

async def memorize_edge_case(session_id: str, case_data: Dict[str, Any], db: AsyncSession) -> None:
    """
    Takes a successful onboarding session edge-case, converts it into a text summary,
    generates an embedding, and saves it to the AgentContext pgvector table.
    """
    try:
        # 1. Synthesize the summary
        summary_text = f"Successful resolution for session {session_id}. Context data: {case_data}"
        logger.info(f"Generating embedding for session {session_id}")
        
        # 2. Get embeddings from Gemini 
        # (Standard text-embedding-004 model generates 768 length array)
        embedding_result = genai.embed_content(
            model="models/text-embedding-004",
            content=summary_text,
            task_type="retrieval_document"
        )
        
        vector = embedding_result.get('embedding')
        if not vector:
             logger.error(f"Failed to generate embedding array for session {session_id}")
             return
             
        # 3. Store in the pgvector compliant database
        memory_record = AgentContext(
            id=str(ulid.ULID()),
            session_id=session_id,
            summary=summary_text,
            embedding=vector
        )
        
        db.add(memory_record)
        await db.commit()
        logger.info(f"Successfully stored agent memory for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to map semantic memory for {session_id}: {e}")

async def query_similar_cases(context: str, db: AsyncSession) -> list[str]:
    """
    Searches the pgvector historical database for similar past edge cases
    to ensure the Agentic Orchestrator makes consistent risk decisions.
    """
    try:
        embedding_result = genai.embed_content(
            model="models/text-embedding-004",
            content=context,
            task_type="retrieval_query"
        )
        
        vector = embedding_result.get('embedding')
        if not vector:
             return ["No historical context found (embedding failure)."]
             
        # pgvector cosine distance nearest-neighbor search
        stmt = select(AgentContext).order_by(AgentContext.embedding.cosine_distance(vector)).limit(3)
        result = await db.execute(stmt)
        
        neighbors = result.scalars().all()
        return [n.summary for n in neighbors]
        
    except Exception as e:
        logger.error(f"Failed to query semantic memory: {e}")
        return [f"Memory query failed: {e}"]
