from app.models import JournalEntry
from app.config import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def get_monthly_summary(user):
    entries = await JournalEntry.filter(user=user).order_by("-date").limit(30)
    if not entries:
        return []
    contents = [entry.content for entry in entries]
    prompt = "\n".join(contents)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize the following journal entries concisely."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )
    summaries = response.choices[0].message.content.split("\n")
    return [summary.strip() for summary in summaries if summary.strip()]


async def get_important_events(user):
    entries = await JournalEntry.filter(user=user).order_by("-date").limit(30)
    if not entries:
        return []
    contents = [entry.content for entry in entries]
    prompt = "\n".join(contents)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Identify up to 5 significant events from these journal entries, focusing on emotional intensity or recurring themes."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )
    events = response.choices[0].message.content.split("\n")
    return [event.strip() for event in events if event.strip()]


async def get_friend_personality(user, f_name):
    entries = await JournalEntry.filter(user=user).order_by("-date").limit(30)
    if not entries:
        return []
    contents = [entry.content for entry in entries]
    prompt = "\n".join(contents)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"Summarize the personality of the following person: {f_name}, based on the journal entries provided. If the person's name is not there in the entries, return 'Friend not present'"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )
    summaries = response.choices[0].message.content.split("\n")
    return [summary.strip() for summary in summaries if summary.strip()]
