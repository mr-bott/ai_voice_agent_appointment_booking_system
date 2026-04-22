from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.graphics import renderPDF


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "voice-agent-project-documentation.pdf"


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCustom",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0B3B60"),
            spaceBefore=10,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subsection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1D4ED8"),
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            leftIndent=14,
            firstLineIndent=-8,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#4B5563"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeBlock",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=8.5,
            leading=10.5,
            backColor=colors.HexColor("#F3F4F6"),
            borderColor=colors.HexColor("#D1D5DB"),
            borderWidth=0.5,
            borderPadding=6,
            spaceBefore=4,
            spaceAfter=8,
        )
    )
    return styles


STYLES = build_styles()


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.line(doc.leftMargin, height - 0.9 * cm, width - doc.rightMargin, height - 0.9 * cm)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(colors.HexColor("#0B3B60"))
    canvas.drawString(doc.leftMargin, height - 0.65 * cm, "Voice Agent Project Documentation")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawRightString(width - doc.rightMargin, 0.6 * cm, f"Page {doc.page}")
    canvas.restoreState()


def p(text, style="Body"):
    return Paragraph(text, STYLES[style])


def bullet(text):
    return Paragraph(f"• {text}", STYLES["BulletCustom"])


def code_block(text):
    return Preformatted(text.strip("\n"), STYLES["CodeBlock"])


def section(title):
    return Paragraph(title, STYLES["Section"])


def subsection(title):
    return Paragraph(title, STYLES["Subsection"])


def flow_table():
    rows = [
        ["Step", "What happens", "Main component"],
        ["1", "User speaks in the browser UI.", "Next.js frontend + Web Audio API"],
        ["2", "Frontend downsamples mic audio to 16 kHz PCM and streams it over WebSocket.", "VoiceInterface.tsx"],
        ["3", "FastAPI receives audio on /ws/audio and forwards chunks to Deepgram.", "api/websocket.py + services/stt.py"],
        ["4", "Deepgram returns interim/final transcript text.", "Deepgram STT"],
        ["5", "VoiceOrchestrator stores context in session memory and calls the LLM.", "agent/orchestrator.py"],
        ["6", "Groq model decides whether to reply directly or invoke tools.", "services/llm.py"],
        ["7", "ToolRouter executes doctor lookup, availability, booking, cancellation, or patient search.", "agent/tool_router.py + agent/tools.py"],
        ["8", "Assistant response is saved to memory and converted to speech.", "memory/session.py + services/tts.py"],
        ["9", "Generated MP3 bytes are sent back to the browser and played immediately.", "FastAPI WebSocket + frontend audio playback"],
        ["10", "Dashboard refreshes appointment history from REST APIs.", "Dashboard.tsx + /api endpoints"],
    ]
    table = Table(rows, colWidths=[1.2 * cm, 10.2 * cm, 5.0 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3B60")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def routes_table():
    rows = [
        ["Type", "Route / Channel", "Purpose"],
        ["GET", "/health", "Lightweight health check for backend readiness."],
        ["GET", "/metrics", "Returns in-memory STT, LLM, TTS, and total latency metrics."],
        ["POST", "/api/patients/", "Create a patient profile."],
        ["GET", "/api/patients/", "List patients."],
        ["GET", "/api/patients/{patient_id}", "Fetch a specific patient."],
        ["POST", "/api/doctors/", "Create a doctor record."],
        ["GET", "/api/doctors/", "List active doctors."],
        ["GET", "/api/doctors/{doctor_id}", "Fetch a specific doctor."],
        ["POST", "/api/appointments/", "Create an appointment record directly through REST."],
        ["GET", "/api/appointments/", "List appointments for dashboard history."],
        ["PUT", "/api/appointments/{appointment_id}/status", "Update appointment status."],
        ["POST", "/api/availability/", "Create an availability slot."],
        ["GET", "/api/availability/", "List slot inventory."],
        ["WS", "/ws/audio", "Real-time voice session for audio in, transcripts, tool events, and audio out."],
    ]
    table = Table(rows, colWidths=[1.3 * cm, 6.4 * cm, 9.4 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3B60")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def stack_table():
    rows = [
        ["Layer", "Current implementation"],
        ["LLM", "Groq via OpenAI-compatible AsyncOpenAI client, default model: llama-3.1-8b-instant"],
        ["Speech-to-Text", "Deepgram live transcription using nova-2"],
        ["Text-to-Speech", "Google TTS through gTTS in backend/services/tts.py"],
        ["Backend", "FastAPI + async SQLAlchemy + WebSocket session orchestration"],
        ["Frontend", "Next.js 16 + React 19 + Tailwind CSS + Web Audio APIs"],
        ["Database", "PostgreSQL for doctors, patients, appointments, slots, memory logs, campaign jobs"],
        ["Cache / Session Memory", "Redis with in-memory fallback when Redis is unavailable"],
        ["Background Jobs", "Celery with Redis broker/backend for outbound campaign processing"],
        ["Deployment split", "Docker Compose currently provisions only Postgres and Redis; app servers run separately"],
    ]
    table = Table(rows, colWidths=[4.2 * cm, 12.9 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3B60")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def architecture_diagram(width=520, height=420):
    d = Drawing(width, height)

    def box(x, y, w, h, title, lines, fill, stroke="#1E3A8A"):
        d.add(Rect(x, y, w, h, rx=10, ry=10, fillColor=colors.HexColor(fill), strokeColor=colors.HexColor(stroke), strokeWidth=1.2))
        d.add(String(x + 10, y + h - 18, title, fontName="Helvetica-Bold", fontSize=11, fillColor=colors.white))
        text_y = y + h - 34
        for line in lines:
            d.add(String(x + 10, text_y, line, fontName="Helvetica", fontSize=8, fillColor=colors.white))
            text_y -= 12

    def arrow(x1, y1, x2, y2, label=None):
        d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#334155"), strokeWidth=1.3))
        if x2 >= x1:
            d.add(Line(x2 - 8, y2 + 4, x2, y2, strokeColor=colors.HexColor("#334155"), strokeWidth=1.3))
            d.add(Line(x2 - 8, y2 - 4, x2, y2, strokeColor=colors.HexColor("#334155"), strokeWidth=1.3))
        else:
            d.add(Line(x2 + 8, y2 + 4, x2, y2, strokeColor=colors.HexColor("#334155"), strokeWidth=1.3))
            d.add(Line(x2 + 8, y2 - 4, x2, y2, strokeColor=colors.HexColor("#334155"), strokeWidth=1.3))
        if label:
            tw = stringWidth(label, "Helvetica", 8)
            d.add(Rect((x1 + x2 - tw - 10) / 2, (y1 + y2) / 2 - 8, tw + 10, 14, rx=4, ry=4, fillColor=colors.white, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.6))
            d.add(String((x1 + x2 - tw) / 2, (y1 + y2) / 2 - 3, label, fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#334155")))

    box(20, 280, 120, 85, "Frontend", ["Next.js dashboard", "Mic capture", "Waveform + chat", "WebSocket client"], "#2563EB")
    box(190, 280, 140, 85, "FastAPI Gateway", ["REST APIs", "WebSocket /ws/audio", "Session status", "Metrics endpoint"], "#0F766E")
    box(380, 280, 120, 85, "Voice Agent", ["VoiceOrchestrator", "Prompt + memory", "Tool call loop", "Barge-in handling"], "#7C3AED")

    box(20, 145, 120, 80, "Deepgram STT", ["Live audio stream", "Interim + final text", "nova-2 model"], "#0891B2")
    box(190, 145, 140, 80, "Groq LLM", ["OpenAI-compatible API", "llama-3.1-8b-instant", "Tool choice auto"], "#9333EA")
    box(380, 145, 120, 80, "TTS", ["gTTS implementation", "Returns MP3 bytes", "Browser plays audio"], "#EA580C")

    box(20, 25, 120, 80, "Redis", ["Session messages", "1-hour TTL", "Fallback to memory"], "#D97706")
    box(190, 25, 140, 80, "PostgreSQL", ["Patients", "Doctors", "Appointments", "Availability slots"], "#1D4ED8")
    box(380, 25, 120, 80, "Celery Worker", ["Outbound campaigns", "Redis broker", "Future phone dialer"], "#475569")

    arrow(140, 322, 190, 322, "Audio / events")
    arrow(330, 322, 380, 322, "Context + tool loop")
    arrow(260, 280, 80, 225, "Audio")
    arrow(260, 280, 260, 225, "Messages")
    arrow(440, 280, 440, 225, "Reply text")
    arrow(80, 145, 220, 185, "Transcript")
    arrow(330, 185, 380, 185, "Response text")
    arrow(380, 185, 330, 185, "Tool decisions")
    arrow(440, 145, 140, 310, "MP3 audio")
    arrow(260, 145, 260, 105, "CRUD")
    arrow(220, 280, 80, 105, "Session cache")
    arrow(330, 65, 380, 65, "Campaign jobs")

    return d


def diagram_story():
    flowables = [section("Architecture Diagram")]
    flowables.append(p("This is the current runtime architecture derived from the actual codebase, not just the README summary."))
    flowables.append(Spacer(1, 0.3 * cm))
    flowables.append(_diagram_flowable())
    flowables.append(Spacer(1, 0.2 * cm))
    flowables.append(
        p(
            "In summary, the browser streams raw audio to FastAPI over WebSocket, Deepgram converts it to text, Groq reasons over the conversation and tool inventory, PostgreSQL and Redis support stateful actions, and the final answer is returned as both text and synthesized speech."
        )
    )
    return flowables


def _diagram_flowable():
    class DiagramFlowable(Flowable):
        def __init__(self):
            super().__init__()
            self.width = 520
            self.height = 420

        def wrap(self, avail_width, avail_height):
            self.width = min(avail_width, 520)
            self.height = 420
            return self.width, self.height

        def draw(self):
            drawing = architecture_diagram(self.width, self.height)
            renderPDF.draw(drawing, self.canv, 0, 0)

    return DiagramFlowable()


def build_story():
    story = []

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("Real-Time Voice AI Agent", STYLES["TitleCustom"]))
    story.append(Paragraph("Project Documentation", STYLES["TitleCustom"]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        p(
            "This PDF explains the working flow, architecture, routes, setup process, Docker usage, backend design, frontend design, and third-party AI integrations of the clinical appointment voice agent."
        )
    )
    story.append(
        p(
            "Current verified stack: <b>Groq for the LLM</b>, <b>Deepgram for speech-to-text</b>, and <b>Google TTS via gTTS</b> for text-to-speech in the running backend code."
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(section("Executive Summary"))
    story.append(
        p(
            "The application is a real-time healthcare appointment assistant. The user speaks in the browser, the frontend streams audio to a FastAPI backend, Deepgram transcribes speech, Groq decides what to say or which clinical tool to call, PostgreSQL stores the domain data, Redis stores short-lived session context, and the final answer is synthesized into audio and played back in the UI."
        )
    )
    story.append(
        p(
            "The project combines low-latency WebSocket streaming, agentic tool calling, structured backend APIs, real database mutations, and a modern real-time frontend in one end-to-end system."
        )
    )
    story.append(section("Technology Stack"))
    story.append(stack_table())
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        p(
            "<b>Important implementation note:</b> the code currently imports <b>gTTS</b> for TTS, but <b>backend/requirements.txt</b> still lists <b>edge-tts</b>. The active implementation is Google TTS, and dependency cleanup would be a good follow-up improvement."
        )
    )

    story.append(PageBreak())
    story.extend(diagram_story())

    story.append(PageBreak())
    story.append(section("Working Flow"))
    story.append(
        p(
            "This section explains what happens when a user tries to book an appointment through the voice interface."
        )
    )
    story.append(flow_table())
    story.append(Spacer(1, 0.25 * cm))
    story.append(subsection("Voice Booking Logic"))
    story.append(bullet("The system prompt enforces a receptionist-style flow: list doctors, ask for date, check availability, collect patient identity, then confirm booking."))
    story.append(bullet("Tool calls are limited to three consecutive rounds in one agent loop, which keeps the conversation from getting stuck in an infinite function-call cycle."))
    story.append(bullet("The orchestrator supports barge-in, so if the user speaks while the assistant is talking, playback is interrupted and the new utterance is prioritized."))
    story.append(bullet("Session messages are stored in Redis when available, but the app also has an in-memory fallback so local demos can still run."))

    story.append(section("Routes and Communication Channels"))
    story.append(routes_table())
    story.append(Spacer(1, 0.2 * cm))
    story.append(subsection("WebSocket Message Types"))
    story.append(bullet("Client to server: binary audio chunks, user_text, interrupt, ping."))
    story.append(bullet("Server to client: transcript, session_status, tool_call, booking_success, interrupt_tts, warning, error, pong, and binary MP3 audio."))

    story.append(PageBreak())
    story.append(section("Setup Guide"))
    story.append(
        p(
            "The setup is currently split into infrastructure services through Docker and application services run directly from the backend and frontend folders."
        )
    )
    story.append(subsection("1. Prerequisites"))
    story.append(bullet("Docker Desktop or Docker Engine"))
    story.append(bullet("Python 3.10+"))
    story.append(bullet("Node.js 18+"))
    story.append(bullet("Groq API key and Deepgram API key"))
    story.append(bullet("PostgreSQL and Redis ports available locally"))
    story.append(subsection("2. Backend Environment Variables"))
    story.append(code_block(
        """
GROQ_API_KEY=your_groq_key
DEEPGRAM_API_KEY=your_deepgram_key
DATABASE_URL=postgresql+asyncpg://admin:password@127.0.0.1:5433/voice_agent
REDIS_URL=redis://127.0.0.1:6379/0
        """
    ))
    story.append(subsection("3. Frontend Environment Variables"))
    story.append(code_block(
        """
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/audio
        """
    ))
    story.append(subsection("4. Start Docker Services"))
    story.append(code_block(
        """
docker-compose up -d
        """
    ))
    story.append(
        p(
            "Current Docker Compose provisions only <b>PostgreSQL</b> and <b>Redis</b>. The backend and frontend are started separately during development."
        )
    )
    story.append(subsection("5. Backend Setup and Execution"))
    story.append(code_block(
        """
cd backend
python -m venv venv
.\\venv\\Scripts\\activate
pip install -r requirements.txt
cd ..
python -m uvicorn backend.main:app --reload
        """
    ))
    story.append(
        p(
            "This flow creates the backend virtual environment, installs the Python dependencies, returns to the project root, and starts the FastAPI application with auto-reload enabled."
        )
    )
    story.append(subsection("6. Frontend Setup and Execution"))
    story.append(code_block(
        """
cd frontend
npm install
npm run dev
        """
    ))
    story.append(
        p(
            "After the backend is running, the frontend is started from the <b>frontend</b> folder using the standard Next.js development server."
        )
    )
    story.append(subsection("7. Optional: Start Celery Worker"))
    story.append(code_block(
        """
cd backend
celery -A scheduler.celery_app worker --loglevel=info
        """
    ))

    story.append(PageBreak())
    story.append(section("Docker Explanation"))
    story.append(
        p(
            "Docker is used here as an infrastructure bootstrap layer. It gives the project reproducible data services without requiring contributors to install Postgres and Redis manually."
        )
    )
    story.append(bullet("Postgres container stores persistent business data such as doctors, patients, appointment records, availability slots, memory logs, and campaign jobs."))
    story.append(bullet("Redis container stores session cache and also acts as the Celery broker/backend."))
    story.append(bullet("Health checks are defined for both services so startup ordering is more reliable during local development."))
    story.append(bullet("The compose file maps Postgres to local port 5433 and Redis to 6379."))
    story.append(
        p(
            "A reasonable future enhancement is to containerize the backend, frontend, and worker too, so the entire demo can be launched with one command."
        )
    )

    story.append(section("Backend Explanation"))
    story.append(subsection("Backend Responsibilities"))
    story.append(bullet("Expose HTTP and WebSocket endpoints through FastAPI."))
    story.append(bullet("Create database tables on startup and seed demo doctors, slots, and a demo patient."))
    story.append(bullet("Coordinate the speech pipeline inside VoiceOrchestrator."))
    story.append(bullet("Run tool-based business actions such as doctor listing, slot lookup, appointment booking, appointment cancellation, and patient lookup."))
    story.append(bullet("Track STT, LLM, and TTS latency through a simple metrics store."))
    story.append(subsection("Backend Design Notes"))
    story.append(bullet("Async FastAPI and SQLAlchemy are a good fit because voice workloads are I/O-heavy and need low waiting time."))
    story.append(bullet("Tool execution is separated from LLM reasoning, which keeps business logic deterministic and easier to test."))
    story.append(bullet("The data model clearly maps to the booking workflow: Patient, Doctor, Appointment, AvailabilitySlot, MemoryLog, and CampaignJob."))
    story.append(bullet("There is already an extension path for outbound reminders through Celery, even though the external telephony provider is still only stubbed in comments."))
    story.append(subsection("Current Limitations"))
    story.append(bullet("A reschedule_appointment tool is defined in the tool schema but is not yet implemented in the tool router."))
    story.append(bullet("The metrics endpoint reports recent in-memory timings, not long-term observability data."))
    story.append(bullet("The TTS dependency list and implementation are slightly out of sync, so production hardening would include dependency cleanup and streaming TTS optimization."))

    story.append(PageBreak())
    story.append(section("Frontend Explanation"))
    story.append(
        p(
            "The frontend is a Next.js dashboard focused on live voice interaction. The visual design is intentionally futuristic, while the technical responsibility of the UI is to capture microphone audio, stream it to the backend, render transcripts, and show booking history."
        )
    )
    story.append(subsection("Frontend Responsibilities"))
    story.append(bullet("Capture microphone input with getUserMedia."))
    story.append(bullet("Downsample browser audio to 16 kHz and convert Float32 buffers into Int16 PCM."))
    story.append(bullet("Send audio frames over WebSocket in real time."))
    story.append(bullet("Render user and assistant transcripts as a live conversation log."))
    story.append(bullet("Play returned MP3 audio from the backend."))
    story.append(bullet("Interrupt playback when barge-in happens."))
    story.append(bullet("Fetch recent appointment history from REST APIs every 15 seconds and render it on the dashboard."))
    story.append(subsection("Frontend Components"))
    story.append(bullet("page.tsx loads the dashboard."))
    story.append(bullet("Dashboard.tsx combines the voice panel with booking history."))
    story.append(bullet("VoiceInterface.tsx owns WebSocket, recording, waveform state, transcript rendering, and audio playback."))
    story.append(bullet("AICore.tsx renders the animated AI orb that reacts to speaking volume."))
    story.append(subsection("Frontend Summary"))
    story.append(
        p(
            "The frontend is not only a visual layer. It handles real-time media capture, sample-rate conversion, event-driven WebSocket messaging, transcript state management, interruption handling, and live synchronization with backend appointment data."
        )
    )
    story.append(section("Project Summary"))
    story.append(
        p(
            "This project is a real-time voice AI booking assistant where the browser streams microphone audio to a FastAPI backend over WebSocket, Deepgram converts speech to text, a Groq-hosted LLM decides the next conversational step and triggers booking tools against Postgres, and the final response is sent back both as text and synthesized audio. Redis keeps the live session lightweight, and the dashboard shows the booking history in near real time."
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Generated from the current codebase in D:\\voice-agent", STYLES["Small"]))
    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.2 * cm,
        title="Voice Agent Project Documentation",
        author="OpenAI Codex",
    )
    doc.build(build_story(), onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
