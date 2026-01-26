import os
from openai import AsyncOpenAI
from signalbot import Context, regex_triggered

from commands.help import CommandWithHelpMessage


client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ChatGPTCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "ask: 🤖 Mention @arisu <question> to ask"

    @regex_triggered(r".*")
    async def handle(self, context: Context) -> None:
        if not self._is_triggered(context):
            return

        prompt = context.message.text
        if context.message.quote:
            prompt = f"{context.message.quote.text}\n{prompt}"

        await context.start_typing()

        try:
            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant deployed on a chatroom. Keep messages brief and to the point.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
            )

            answer = response.choices[0].message.content.strip()  # type: ignore

            if len(answer) > 1800:
                answer = answer[:1800] + "..."

            await context.reply(answer)

        except Exception:
            await context.reply("arisu is busy 😔")

        finally:
            await context.stop_typing()

    def _is_triggered(self, context: Context) -> bool:
        mentions = context.message.mentions
        bot_uuid = context.message.source_uuid

        for m in mentions:
            if m.get("uuid") == bot_uuid:  # type: ignore
                return True

        return False
