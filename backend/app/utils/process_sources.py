import weaviate
from openai import OpenAI
import os
from glob import glob

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = weaviate.Client(WEAVIATE_URL)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

schema = {
    "classes": [
        {
            "class": "PsychologyChunk",
            "properties": [
                {"name": "title", "dataType": ["string"]},
                {"name": "text", "dataType": ["text"]},
            ],
            "vectorizer": "none",
        }
    ]
}
client.schema.delete_all()
client.schema.create(schema)

source_dir = "../data/psychology_sources"
for file_path in glob(os.path.join(source_dir, "*.txt")):
    with open(file_path, "r") as f:
        text = f.read()
        chunks = text.split("\n\n")
        for chunk in chunks:
            if chunk.strip():
                embedding = openai_client.embeddings.create(input=chunk, model="text-embedding-ada-002").data[0].embedding
                client.data_object.create(
                    {
                        "title": os.path.basename(file_path),
                        "text": chunk,
                    },
                    "PsychologyChunk",
                    vector=embedding
                )