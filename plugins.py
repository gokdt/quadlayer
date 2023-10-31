import os
import uuid

import requests
import structlog
from litellm import embedding

logger = structlog.get_logger()


class Plugins:
    """
    Plugins for quadlayer

    We provide several plugins by default, but you can add your own plugins
    by adding them to the plugins list.
    """

    def __init__(self):
        search_plugin = {
            "name": "search",
            "description": "Search using search engine, useful when requires recent knowledge",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query to search",
                    },
                },
                "required": ["query"],
            },
        }

        notes_plugin = [
            {
                "name": "create_note",
                "description": "Create a note, returns note ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Note title",
                        },
                        "content": {
                            "type": "string",
                            "description": "Note content",
                        },
                    },
                    "required": ["title", "content"],
                },
            },
            {
                "name": "retrieve_note",
                "description": "Retrieve a note, returns note contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Query to search (e.g. note title or topic)",
                        },
                    },
                    "required": ["query"],
                },
            },
        ]

        self.plugins = []
        self.plugins_map = {}

        self.bing_api_key = os.environ.get("BING_API_KEY")
        self.use_chroma = os.environ.get("USE_CHROMA", "false").lower() == "true"

        if self.bing_api_key:
            logger.debug("Bing API key found, enabling search plugin")
            self.plugins.append(search_plugin)
            self.plugins_map["search"] = self.search

        if self.use_chroma:
            logger.debug("ChromaDB enabled, enabling notes plugin")
            self.plugins.extend(notes_plugin)
            self.plugins_map["create_note"] = self.create_note
            self.plugins_map["retrieve_note"] = self.retrieve_note

            import chromadb

            self.chroma_client = chromadb.PersistentClient(path=".chroma")

    def search(self, query: str) -> str:
        """
        Search using Bing

        :param query: Query
        :return: Search result
        """
        if not self.bing_api_key:
            raise Exception("Bing API key not found")

        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
        params = {"q": query}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        search_results = response.json()

        if not search_results["webPages"]["value"]:
            return "No results found"

        snippets = [
            f"{result['name']}: {result['snippet']}"
            for result in search_results["webPages"]["value"]
        ]
        return "\n\n".join(snippets)

    def wit(self, query: str, api_key: str | None = None) -> str:
        """
        Get intent using wit.ai

        :param query: Query
        :param api_key: Wit API key
        :return: Intent
        """
        if not api_key:
            raise Exception("Wit API key not found")

        response = requests.get(
            "https://api.wit.ai/message",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            params={"q": query},
        )
        response.raise_for_status()

        wit_response = response.json()

        return wit_response["intents"][0]["name"]

    def create_note(self, title: str, content: str, **kwargs) -> str:
        """
        Create a note

        :param title: Note title
        :param content: Note content
        :return: Note ID
        """
        collection = self.chroma_client.get_or_create_collection(kwargs["user_id"])

        # Let's generate embeddings for the title + content
        embeddings_response = embedding(
            os.environ.get("EMBEDDINGS_MODEL"),
            input=[f"{title}\n\n{content}"],
        )

        # Let's generate note ID
        note_id = str(uuid.uuid4())

        # And store the note
        collection.add(
            embeddings=[embeddings_response["data"][0]["embedding"]],
            documents=[f"{title}\n\n{content}"],
            ids=[note_id],
        )

        return note_id

    def retrieve_note(self, query: str, **kwargs) -> str:
        """
        Retrieve a note

        :param query: Query to search (e.g. note title or topic)
        :return: Note content
        """
        collection = self.chroma_client.get_or_create_collection(kwargs["user_id"])

        # Let's generate embeddings for the query
        embeddings_response = embedding(
            os.environ.get("EMBEDDINGS_MODEL"),
            input=[query],
        )

        # And search for the note
        search_response = collection.query(
            query_embeddings=[embeddings_response["data"][0]["embedding"]],
            n_results=3,
        )

        search_response = [
            f"--BEGIN NOTE--\n{document}\n--END NOTE--"
            for document in search_response["documents"]
        ]

        return "\n\n".join(search_response)

    def call_function(self, name: str, arguments: dict, user_id: str) -> str:
        """
        Call a function

        :param name: Function name
        :param arguments: Function arguments
        :return: Function result
        """
        logger.debug("Calling function", name=name, arguments=arguments)
        if name not in self.plugins_map:
            raise Exception(f"Function {name} not found")

        arguments["user_id"] = user_id

        return str(self.plugins_map[name](**arguments))
