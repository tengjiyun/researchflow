from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from app.schemas.collections import Collection, CollectionList, CollectionWrite
from app.schemas.errors import ErrorResponse
from app.services.collections import CollectionStore, get_collection_store


router = APIRouter(tags=['collections'], responses={
    status: {'model': ErrorResponse} for status in (404, 409, 422, 503)
})
Store = Annotated[CollectionStore, Depends(get_collection_store)]
Identifier = Annotated[int, Path(ge=1, le=9223372036854775807)]


@router.post('/collections', status_code=201, response_model=Collection)
def create_collection(body: CollectionWrite, store: Store) -> Collection:
    return store.create(body.name)


@router.get('/collections', response_model=CollectionList)
def list_collections(store: Store) -> CollectionList:
    return CollectionList(collections=store.list_collections())


@router.patch('/collections/{collection_id}', response_model=Collection)
def rename_collection(collection_id: Identifier, body: CollectionWrite, store: Store) -> Collection:
    return store.rename(collection_id, body.name)


@router.delete('/collections/{collection_id}', status_code=204)
def delete_collection(collection_id: Identifier, store: Store) -> Response:
    store.delete(collection_id)
    return Response(status_code=204)


@router.put('/collections/{collection_id}/papers/{paper_id}', status_code=204)
def add_collection_paper(collection_id: Identifier, paper_id: Identifier, store: Store) -> Response:
    store.add_paper(collection_id, paper_id)
    return Response(status_code=204)


@router.delete('/collections/{collection_id}/papers/{paper_id}', status_code=204)
def remove_collection_paper(collection_id: Identifier, paper_id: Identifier, store: Store) -> Response:
    store.remove_paper(collection_id, paper_id)
    return Response(status_code=204)


@router.get('/papers/{paper_id}/collections', response_model=CollectionList)
def list_paper_collections(paper_id: Identifier, store: Store) -> CollectionList:
    return CollectionList(collections=store.list_collections(paper_id))
