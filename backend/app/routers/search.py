from fastapi import APIRouter, HTTPException, status
from app.schemas.search import SearchRequest, SearchResponse
from app.services.web_search_service import get_search_service
from app.core.config import settings

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("", response_model=SearchResponse)
async def perform_search(req: SearchRequest):
    """
    Direct web search endpoint returning verified URLs, titles, and snippets.
    """
    service = get_search_service()
    try:
        results = await service.search(query=req.query, max_results=req.max_results)
        return SearchResponse(
            query=req.query,
            results=results,
            provider=settings.SEARCH_PROVIDER
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Web search provider error: {str(e)}"
        )
