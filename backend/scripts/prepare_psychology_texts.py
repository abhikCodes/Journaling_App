import wikipedia
import os

topics = ["Psychology", "Dream interpretation", "Anxiety", "Depression", "Personality psychology"]
output_dir = "scripts/psychology_texts"

os.makedirs(output_dir, exist_ok=True)

for topic in topics:
    try:
        page = wikipedia.page(topic)
        with open(f"{output_dir}/{topic.replace(' ', '_')}.txt", "w", encoding="utf-8") as f:
            f.write(page.content)
        print(f"Saved {topic}")
    except Exception as e:
        print(f"Error fetching {topic}: {e}")

print("Psychology texts prepared.")