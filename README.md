# Revrag Voice Agent 🎙️

A real-time voice agent built with LiveKit Agents SDK that joins a LiveKit room, listens to user speech, and responds with **"You said: \<text\>"** — demonstrating a full STT → Response → TTS pipeline with no-overlap and silence handling.

---

## Demo

The agent:
1. Joins a LiveKit room and greets the user
2. Listens to speech via Deepgram STT
3. Responds with `"You said: <transcribed text>"`
4. Never speaks while the user is speaking (VAD-based interrupt handling)
5. Plays a reminder after 20 seconds of silence

---

## Tech Stack

| Component | Tool |
|-----------|------|
| Agent framework | [LiveKit Agents SDK](https://docs.livekit.io/agents/) v1.4.3 (Python) |
| Transport | [LiveKit Cloud](https://cloud.livekit.io) (free tier) |
| STT | [Deepgram Nova-2](https://deepgram.com) (streaming, ~150ms TTFT) |
| TTS | [Deepgram Aura](https://deepgram.com) (aura-asteria-en) |
| VAD | [Silero VAD](https://github.com/snakers4/silero-vad) (bundled with livekit-agents) |

---

## How No-Overlap Works

The `AgentSession` uses **Silero VAD** running continuously on the incoming audio track:

1. **VAD detects speech START** → any in-progress TTS playback is immediately cancelled, agent enters `LISTENING` state (no audio published)
2. **VAD detects speech END** → audio is sent to Deepgram STT, transcript is produced, echo response is generated, Deepgram TTS converts it to audio, audio is published to the room
3. **User speaks mid-playback** → step 1 fires again instantly, stopping the agent within ~20ms (one audio frame)

This guarantees the agent **never speaks while the user is speaking**.

---

## Requirements

- Python 3.11+
- [LiveKit Cloud](https://cloud.livekit.io) account (free)
- [Deepgram](https://console.deepgram.com) account (free — $200 credit)

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/revrag-voice-agent.git
cd revrag-voice-agent
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
DEEPGRAM_API_KEY=your_deepgram_api_key
```

**Getting LiveKit credentials:**
1. Go to [cloud.livekit.io](https://cloud.livekit.io)
2. Open your project → Settings → API Keys
3. Copy `Websocket URL`, `API Key`, and `API Secret`

**Getting Deepgram API key:**
1. Go to [console.deepgram.com](https://console.deepgram.com)
2. Click "Free API Key" → Create Key → Copy it

---

## How to Run

### Step 1 — Generate a token

```bash
python generate_token.py
```

Copy the token printed in the terminal.

### Step 2 — Start the agent

```bash
python agent.py dev
```

You should see:
```
INFO  livekit.agents  starting worker {"version": "1.4.3"}
INFO  livekit.agents  registered worker
INFO  revrag-agent    Waiting for participant...
```

### Step 3 — Connect and speak

1. Go to [meet.livekit.io](https://meet.livekit.io) → click **Custom**
2. Enter your `LIVEKIT_URL`
3. Paste the token from Step 1
4. Click **Connect** → allow microphone
5. Say something — the agent will respond!

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LIVEKIT_URL` | LiveKit Cloud WebSocket URL (`wss://...`) |
| `LIVEKIT_API_KEY` | LiveKit project API key |
| `LIVEKIT_API_SECRET` | LiveKit project API secret |
| `DEEPGRAM_API_KEY` | Deepgram API key for STT + TTS |

---

## Project Structure

```
revrag-voice-agent/
├── agent.py              # Main agent logic
├── generate_token.py     # Generates LiveKit access token for testing
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── .gitignore            # Excludes .env from git
└── README.md
```

---

## Known Limitations

- **Echo only** — responds with "You said: \<text\>", no LLM used
- **English only** — Deepgram Nova-2 configured for English
- **Single participant** — connects to the first participant who joins
- **No UI** — backend agent only; use LiveKit Meet or custom frontend to interact
- **Silence reminder fires once per silence period** — resets when user speaks again, does not loop
- **Token expiry** — generated tokens expire after 6 hours; regenerate if needed
