"""Data models for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional


class PipelineRunRequest(BaseModel):
    """Request model for the pipeline/run endpoint."""
    offset: int = Field(0, description="Listing offset (default: 0)")
    limit: int = Field(25, description="Listing page size (default: 25)")
    timeout: int = Field(45, description="HTTP timeout in seconds")
    status: str = Field("", description="Optional listing status filter")
    event_id: str = Field(..., description="REQUIRED: CollectorInvestor Event ID (e.g., '4053663')")


class PipelineRunResponse(BaseModel):
    """Response model for the pipeline/run endpoint."""
    success: bool = Field(..., description="Whether the pipeline succeeded")
    fetched: int = Field(..., description="Number of products fetched")
    products_tagged: int = Field(..., description="Number of products tagged")
    total_tags: int = Field(..., description="Total tags generated")
    tags_posted: int = Field(0, description="Number of products with tags posted to API")
    tags_posted_failed: int = Field(0, description="Number of products that failed to post tags")


class ProductSearchResult(BaseModel):
    """Individual search result for a product."""
    id: int
    title: str
    subtitle: Optional[str] = ""
    category: Optional[str] = ""
    description: Optional[str] = ""
    image_url: Optional[str] = ""
    tags: list[str] = Field(default_factory=list)
    matched_tags: list[str] = Field(default_factory=list)
    score: int


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    query: str
    total: int
    results: list[ProductSearchResult] = Field(default_factory=list)


class ProductTagResponse(BaseModel):
    """Response model for /products/{id}/tags endpoint."""
    id: int
    title: str
    tags: list[str] = Field(default_factory=list)


class PostTagResult(BaseModel):
    """Result for a single product tag posting."""
    listing_id: str
    title: str
    status_code: Optional[int]
    success: bool
    response: str


class PostTagsResponse(BaseModel):
    """Response model for posting tags to Collector Investor."""
    success: bool
    total: int
    successful: int
    failed: int
    results: list[PostTagResult] = Field(default_factory=list)

class FullEventPipelineRequest(BaseModel):
    """Request model for processing entire event."""
    event_id: str = Field(..., description="REQUIRED: CollectorInvestor Event ID")

class FullEventPipelineResponse(BaseModel):
    """Response for processing entire event."""
    success: bool
    event_id: str
    total_fetched: int
    products_tagged: int
    products_skipped: int
    total_tags: int
    tags_posted: int
    tags_posted_failed: int
    pages_processed: int
    total_pages: int

class TagSingleListingRequest(BaseModel):
    """Request model for tagging a single listing."""
    event_id: str = Field(..., description="REQUIRED: CollectorInvestor Event ID (e.g., '4053663')")

class TagSingleListingResponse(BaseModel):
    """Response for tagging a single listing."""
    success: bool
    listing_id: int
    title: str
    tags_generated: int
    tags_posted: bool
    message: str