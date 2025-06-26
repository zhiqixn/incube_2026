"""
Tool used for RAG retrieval
"""

from autogen_core.tools import FunctionTool

from config.tools_config import rag_cfg
from typing import List

import requests
import weaviate


def get_weaviate_client():
    assert (
        "weaviate_client_configs" in rag_cfg
    ), "Missing weaviate_client_configs in rag_cfg"

    client = weaviate.connect_to_custom(**rag_cfg["weaviate_client_configs"])

    return client


def retrieve_documents(
    client: weaviate.WeaviateClient, query: str, weaviate_collection: str = None
) -> List[str]:
    """
    Perform a hybrid RAG search using the query and the specified collection.

    Parameters:
    client (weaviate.WeaviateClient): The Weaviate client
    query (str): The query to be searched
    weaviate_collection (str): The Weaviate collection to search in. If None, the
        collection specified in rag_cfg is used.

    Returns:
    List[str]: A list of strings containing the results of the search.
    """
    # embed query
    query_emb_response = requests.post(
        rag_cfg["embedding_api_endpoint"],
        json={
            "input": query,
            "model": rag_cfg["embedding_model"],
        },
        timeout=5,
    )

    query_emb = query_emb_response.json().get("embedding")

    # perform hybrid RAG search
    if not weaviate_collection:
        weaviate_collection = rag_cfg["weaviate_collection"]

    collection = client.collections.get(weaviate_collection)
    query_kwargs = (
        rag_cfg["weaviate_query_kwargs"] if "weaviate_query_kwargs" in rag_cfg else {}
    )
    response = collection.query.hybrid(
        query=query,
        vector=query_emb,
        **query_kwargs,
    )

    rag_results = []

    for response_object in response.objects:
        object_properties = response_object.properties
        rag_results.append(object_properties[rag_cfg["weaviate_content_field"]])

    return rag_results


def rag(query: str, name: str) -> List[str]:
    """
    Retrieves documents from a given collection using a hybrid RAG search.

    Parameters:
    query (str): The query to be searched
    name (str): The name of the collection to search in

    Returns:
    List[str]: A list of strings containing the results of the search
    """
    try:
        client = get_weaviate_client()
    except Exception as e:
        return f"Error occurred when getting weaviate client -> {e}"

    try:
        collection = name
        retrieved_documents = retrieve_documents(client, query, collection)
    except Exception as e:
        return f"Error occurred when retrieving documents -> {e}"
    finally:
        client.close()

    return retrieved_documents


rag = FunctionTool(rag, description=rag_cfg["description"])
