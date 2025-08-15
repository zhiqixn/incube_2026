import weaviate
import os

# from configs.tools_config import rag_cfg

# Configuration: Update with your actual Weaviate instance details
WEAVIATE_URL = "http://192.168.100.110:8080"  # or your cloud instance URL
COLLECTION_NAME = "SOP"  # Replace with your class name

rag_cfg = {
    "weaviate_client_configs": {
        "http_host": os.environ.get("WEAVIATE_HOST", "weaviate"),
        "http_port": os.environ.get("WEAVIATE_PORT", 8080),
        "http_secure": False,
        "grpc_host": os.environ.get("WEAVIATE_HOST", "weaviate"),
        "grpc_port": os.environ.get("WEAVIATE_GRPC_PORT", 50051),
        "grpc_secure": False,
    }
}


def check_if_collection_has_documents():
    client = weaviate.connect_to_custom(**rag_cfg["weaviate_client_configs"])
    print(client.is_ready())
    return True


if __name__ == "__main__":
    has_docs = check_if_collection_has_documents()
    if has_docs:
        print("Collection contains documents.")
    else:
        print("Collection is empty or does not exist.")
