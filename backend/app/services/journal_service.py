from app.models import JournalEntry
from app.config import settings
from openai import OpenAI
from datetime import datetime

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def get_monthly_summary(user, year: int, month: int):
    entries = await JournalEntry.filter(
        user=user,
        date__year=year,
        date__month=month
    ).order_by("date")
    if not entries:
        return "No journal entries found for this month."
    contents = [entry.content for entry in entries]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize the following journal entries concisely."},
            {"role": "user", "content": "\n".join(contents[:10])}  # Limit to 10 entries for efficiency
        ],
        max_tokens=200
    )
    return response.choices[0].message.content

async def get_important_events(user):
    entries = await JournalEntry.filter(user=user).order_by("-date").limit(50)
    if not entries:
        return []
    contents = [entry.content for entry in entries]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Identify up to 5 significant events from these journal entries, focusing on emotional intensity or recurring themes."},
            {"role": "user", "content": "\n".join(contents)}
        ],
        max_tokens=300
    )
    events = response.choices[0].message.content.split("\n")
    return [event.strip() for event in events if event.strip()]