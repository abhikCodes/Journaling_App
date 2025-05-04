#!/usr/bin/env python
"""
Script to generate a sample CSV file for testing the journal import endpoint.
"""
import pandas as pd
import json
from datetime import datetime, timedelta
import random

# Sample journal content templates
TEMPLATES = [
    "Today was a {adjective} day. I spent most of my time {activity}. I felt {emotion} about it and learned that {learning}. Tomorrow I plan to {future_plan}.",
    "I woke up feeling {emotion} this morning. After {activity}, I had a {adjective} conversation with {person}. We discussed {topic} and I realized {learning}.",
    "My day started {adverb}. I {activity} which was quite {adjective}. Later, I met with {person} and we {activity2}. I'm {emotion} about how things are going.",
    "Reflecting on today, I feel {emotion}. The highlight was {activity} which turned out {adverb} {adjective}. I'm grateful for {gratitude} and looking forward to {future_plan}."
]

# Word lists for generating content
ADJECTIVES = ["productive", "challenging", "inspiring", "difficult", "relaxing", "stressful", "peaceful", "exciting", "boring", "pleasant"]
EMOTIONS = ["happy", "content", "anxious", "hopeful", "concerned", "grateful", "proud", "overwhelmed", "motivated", "nostalgic"]
ACTIVITIES = ["working on a project", "reading a book", "meeting with friends", "exercising", "learning something new", "cooking a meal", "organizing my space", "spending time outdoors", "reflecting on my goals", "helping someone in need"]
ACTIVITIES2 = ["had coffee", "went for a walk", "discussed our plans", "watched a movie", "shared ideas", "worked on a project", "had a meaningful conversation", "played a game", "enjoyed a meal together", "reminisced about old times"]
ADVERBS = ["surprisingly", "wonderfully", "disappointingly", "unexpectedly", "predictably", "delightfully", "frustratingly", "peacefully", "energetically", "slowly"]
PEOPLE = ["a friend", "a colleague", "my partner", "a family member", "an old acquaintance", "my mentor", "a neighbor", "a new contact", "my team", "someone unexpected"]
TOPICS = ["future plans", "recent experiences", "shared interests", "current events", "personal growth", "mutual challenges", "creative ideas", "life changes", "philosophical questions", "practical matters"]
LEARNINGS = ["patience is valuable", "taking small steps makes progress", "asking for help is strength", "change is inevitable", "perspective matters", "consistency pays off", "self-care is essential", "relationships need nurturing", "listening is underrated", "adaptability is crucial"]
GRATITUDE = ["supportive people in my life", "moments of peace", "opportunities to learn", "small achievements", "health and well-being", "unexpected kindness", "beautiful surroundings", "technological conveniences", "personal growth", "simple pleasures"]
FUTURE_PLANS = ["focus more on priorities", "try something new", "connect with someone important", "continue what's working well", "adjust my approach", "rest and reflect", "tackle a challenge", "celebrate progress", "plan the next steps", "be more present"]

def generate_journal_entry():
    """Generate a random journal entry"""
    template = random.choice(TEMPLATES)
    return template.format(
        adjective=random.choice(ADJECTIVES),
        emotion=random.choice(EMOTIONS),
        activity=random.choice(ACTIVITIES),
        activity2=random.choice(ACTIVITIES2),
        adverb=random.choice(ADVERBS),
        person=random.choice(PEOPLE),
        topic=random.choice(TOPICS),
        learning=random.choice(LEARNINGS),
        gratitude=random.choice(GRATITUDE),
        future_plan=random.choice(FUTURE_PLANS)
    )

def generate_tags():
    """Generate random tags for an entry"""
    all_tags = ["personal", "work", "health", "relationships", "learning", "productivity", 
                "reflection", "goals", "challenges", "achievements", "gratitude", "growth"]
    
    # Pick 1-3 random tags
    num_tags = random.randint(1, 3)
    return random.sample(all_tags, num_tags)

def generate_title(entry):
    """Generate a simple title based on the content"""
    words = entry.split()
    if len(words) > 10:
        key_start = random.randint(0, min(10, len(words)-5))
        title_words = words[key_start:key_start+random.randint(3, 5)]
        return ' '.join(title_words).capitalize()
    return "Journal Entry"

def main():
    # Number of entries to generate
    num_entries = 30
    
    # Start date (30 days ago)
    start_date = datetime.now() - timedelta(days=num_entries)
    
    # Generate data
    data = []
    for i in range(num_entries):
        entry_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        content = generate_journal_entry()
        tags = generate_tags()
        title = generate_title(content)
        
        data.append({
            'date': entry_date,
            'content': content,
            'tags': json.dumps(tags),
            'title': title
        })
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data)
    csv_path = 'journal_sample.csv'
    df.to_csv(csv_path, index=False)
    print(f"Sample CSV file generated at: {csv_path}")

if __name__ == "__main__":
    main() 