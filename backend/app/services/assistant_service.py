from openai import OpenAI
from app.config import settings
from app.models import User
from app.services.journal_service import get_monthly_summary, get_important_events
import json

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Assistant creation (run once or on startup in a real deployment)
ASSISTANT_INSTRUCTIONS = """
You are a psychology expert assistant designed to help users with their journaling and personal insights. You have access to a library of psychology texts via file search and can retrieve information to support your advice. You can also access summaries and insights from the user's journal entries through function calls. Be empathetic, supportive, and provide informed responses. Include a disclaimer when appropriate: 'I am not a substitute for professional help; please consult a licensed therapist for serious concerns.'
"""

assistant = client.beta.assistants.create(
    name="PsychologyExpert",
    instructions=ASSISTANT_INSTRUCTIONS,
    model="gpt-4o-mini",
    tools=[
        {"type": "file_search"},
        {
            "type": "function",
            "function": {
                "name": "get_monthly_summary",
                "description": "Get a summary of the user's journal entries for a specific month.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "year": {"type": "integer"},
                        "month": {"type": "integer"}
                    },
                    "required": ["year", "month"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_important_events",
                "description": "Identify significant events from the user's journal entries.",
                "parameters": {"type": "object", "properties": {}}
            }
        }
    ]
)

# Attach psychology texts (run once with prepared files)
def attach_psychology_texts():
    file_ids = []
    for file_path in ["scripts/psychology_texts/Psychology.txt", "scripts/psychology_texts/Dream_interpretation.txt"]:
        with open(file_path, "rb") as f:
            file = client.files.create(file=f, purpose="assistants")
            file_ids.append(file.id)
    client.beta.assistants.update(assistant_id=assistant.id, file_ids=file_ids)

# Uncomment to run once
# attach_psychology_texts()

async def handle_assistant_message(user: User, message: str):
    if not user.thread_id:
        thread = client.beta.threads.create()
        user.thread_id = thread.id
        await user.save()
    thread_id = user.thread_id

    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=message)
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant.id)

    while run.status in ["in_progress", "queued", "requires_action"]:
        run = client.beta.threads.runs.retrieve(run_id=run.id, thread_id=thread_id)
        if run.status == "requires_action":
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                if tool_call.function.name == "get_monthly_summary":
                    args = json.loads(tool_call.function.arguments)
                    summary = await get_monthly_summary(user, args["year"], args["month"])
                    tool_outputs.append({"tool_call_id": tool_call.id, "output": summary})
                elif tool_call.function.name == "get_important_events":
                    events = await get_important_events(user)
                    tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(events)})
            if tool_outputs:
                client.beta.threads.runs.submit_tool_outputs(
                    run_id=run.id, thread_id=thread_id, tool_outputs=tool_outputs
                )

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data[0].content[0].text.value