import weaviate
from openai import OpenAI
import os

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = weaviate.Client(WEAVIATE_URL)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

async def get_relevant_chunks(query, k=5):
    query_embedding = openai_client.embeddings.create(input=query, model="text-embedding-ada-002").data[0].embedding
    result = client.query.get("PsychologyChunk", ["title", "text"]).with_near_vector({"vector": query_embedding}).with_limit(k).do()
    return result["data"]["Get"]["PsychologyChunk"]

async def generate_response(query, context):
    prompt = f"You are a psychology expert. Based on the following context and the user's journal entries, provide advice or answer the query.\n\nContext:\n{context}\n\nQuery: {query}"
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content