from openai import OpenAI
from app.config import settings
from app.models import User
from app.services.journal_service import get_monthly_summary, get_important_events, get_friend_personality
import json

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Delay assistant creation until startup
assistant = None

async def init_assistant():
    global assistant
    if assistant is None:
        ASSISTANT_INSTRUCTIONS = """You are a psychology expert assistant designed to help users with their journaling and personal insights. You have access to a library of psychology texts via file search and can retrieve information to support your advice. You can also access summaries and insights from the user's journal entries through function calls. Be empathetic, supportive, and provide informed responses. Include a disclaimer when appropriate: 'I am not a substitute for professional help; please consult a licensed therapist for serious concerns.'"""
        assistant = client.beta.assistants.create(
            name="PsychologyExpert",
            instructions=ASSISTANT_INSTRUCTIONS,
            model="gpt-4o-mini",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_monthly_summary",
                        "description": "Get a summary of the user's journal entries for the last 30 days.",
                        "parameters": {"type": "object", "properties": {}}
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_important_events",
                        "description": "Identify significant events from the user's journal entries for the last 30 days.",
                        "parameters": {"type": "object", "properties": {}}
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_friend_personality",
                        "description": "Summarize a friend's personality from the user's journal entries for the last 30 days.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "f_name": {
                                    "type": "string",
                                    "description": "The first name of the friend to analyze."
                                }
                            },
                            "required": ["f_name"]
                        }
                    }
                }
            ]
        )


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
                    summary = await get_monthly_summary(user)
                    tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(summary)})

                elif tool_call.function.name == "get_important_events":
                    events = await get_important_events(user)
                    tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(events)})

                elif tool_call.function.name == "get_friend_personality":
                    args = json.loads(tool_call.function.arguments)
                    personality = await get_friend_personality(user, args["f_name"])
                    tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(personality)})

            if tool_outputs:
                client.beta.threads.runs.submit_tool_outputs(
                    run_id=run.id, thread_id=thread_id, tool_outputs=tool_outputs
                )

    messages = client.beta.threads.messages.list(thread_id=thread_id).data
    assistant_msgs = [obj for obj in messages if obj.role == 'assistant']
    assistant_msgs.sort(key=lambda m: m.created_at, reverse=True)
    
    # Check if there are any assistant messages
    if not assistant_msgs:
        return "I'm sorry, I couldn't process your request. Please try again."
    
    # Get the latest assistant message
    latest = assistant_msgs[0]
    reply = "".join(block.text.value for block in latest.content if hasattr(block, "text") and hasattr(block.text, "value"))

    return reply
