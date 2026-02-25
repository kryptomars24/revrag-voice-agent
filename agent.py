"""
Revrag Voice Agent
==================
A real-time voice agent that:
  - Joins a LiveKit room
  - Listens to user speech via Deepgram STT (Nova-2)
  - Responds with "You said: <text>" via Deepgram TTS
  - Never speaks over the user (Silero VAD + interrupt handling)
  - Plays a reminder if user is silent for 20+ seconds

HOW NO-OVERLAP WORKS:
  1. Silero VAD runs continuously on the incoming audio track.
  2. When VAD detects speech START:
     -> AgentSession immediately cancels any in-progress TTS playback
     -> Agent enters LISTENING state, publishes zero audio
  3. When VAD detects speech END:
     -> Audio is sent to Deepgram STT -> transcript produced
     -> on_user_turn_completed fires -> echo response generated
     -> Deepgram TTS converts response to audio -> published to room
  4. If user speaks mid-playback -> step 2 fires again (interrupt)
     -> Current TTS stops within one audio frame (~20ms)
  This guarantees the agent NEVER speaks while the user is speaking.
"""

import asyncio
import logging
import time

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    RoomInputOptions,
)
from livekit.plugins import deepgram, silero

load_dotenv()

logger = logging.getLogger("revrag-agent")
logging.basicConfig(level=logging.INFO)

SILENCE_TIMEOUT_SECONDS = 20
REMINDER_TEXT = "I'm still here. Feel free to say something whenever you're ready."


class EchoAgent(Agent):
    """
    Voice agent that echoes back what the user says.
    Uses Deepgram for STT and TTS, Silero for VAD.
    """

    def __init__(self):
        super().__init__(
            instructions="You are a helpful voice assistant that echoes back what the user says."
        )
        self._last_speech_time = time.time()

    async def on_enter(self):
        """Called when agent joins the session. Greet the user."""
        logger.info("EchoAgent entered session")
        await self.session.say(
            "Hello! I'm your voice assistant. Say something and I'll echo it back to you.",
            allow_interruptions=True,
        )
        asyncio.ensure_future(self._silence_watcher())

    async def on_user_turn_completed(self, turn_ctx, new_message):
        """
        Called after STT produces a transcript from the user's speech.
        We override this to generate our echo response instead of using an LLM.
        """
        user_text = new_message.text_content.strip() if new_message.text_content else ""
        self._last_speech_time = time.time()

        logger.info(f"User said: '{user_text}'")

        if user_text:
            response = f"You said: {user_text}"
        else:
            response = "Sorry, I didn't catch that. Could you say that again?"

        logger.info(f"Agent responding: '{response}'")
        await self.session.say(response, allow_interruptions=True)

    async def _silence_watcher(self):
        """
        Background task that monitors silence.
        Plays a reminder once after 20s of silence.
        Resets when the user speaks again.
        Does NOT loop or continuously publish audio.
        """
        reminder_played = False
        while True:
            await asyncio.sleep(5)
            elapsed = time.time() - self._last_speech_time

            if elapsed >= SILENCE_TIMEOUT_SECONDS and not reminder_played:
                logger.info(f"{SILENCE_TIMEOUT_SECONDS}s of silence - playing reminder")
                await self.session.say(REMINDER_TEXT, allow_interruptions=True)
                reminder_played = True
            elif elapsed < SILENCE_TIMEOUT_SECONDS and reminder_played:
                reminder_played = False


def prewarm(proc: JobProcess):
    """Preload Silero VAD model into memory before the job starts."""
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    logger.info(f"Agent joining room: {ctx.room.name}")

    await ctx.connect()

    logger.info("Waiting for participant...")
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant connected: {participant.identity}")

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model="nova-2"),
        tts=deepgram.TTS(model="aura-asteria-en"),
    )

    await session.start(
    agent=EchoAgent(),
    room=ctx.room,
    room_input_options=RoomInputOptions(),
)

    logger.info("Agent session started.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )


    