from __future__ import annotations

import io
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import create_document, get_documents
from schemas import (
    AnalyzeResponse,
    Explanation,
    MCQ,
    MCQOption,
    PlanItem,
    Study,
    StudyPlan,
    Tip,
)

app = FastAPI(title="StudySnap Web API")

# CORS for local dev and hosted frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RootResponse(BaseModel):
    message: str


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse(message="StudySnap backend is running")


@app.get("/test")
async def test_db():
    try:
        collections = await get_documents("study", limit=3)
        return {
            "backend": "ok",
            "database": "ok",
            "database_url": "env",
            "database_name": "env",
            "connection_status": "connected",
            "collections": [c.get("filename", "doc") for c in collections],
        }
    except Exception as e:
        return {"backend": "ok", "database": "error", "error": str(e)}


# Simple heuristic fake "AI" to simulate analysis fully in backend without external APIs
# In real deployment this would call a vision+LLM service. Here we parse text content if any.

def extract_text_from_upload(upload: UploadFile) -> str:
    # If image, we can't OCR without external libs; fall back to filename-based heuristics
    name = upload.filename.lower() if upload.filename else ""
    # Allow simple text uploads too for demo
    return name.replace("_", " ").replace("-", " ")


SUBJECT_HINTS = {
    "mathe": "Mathematik",
    "math": "Mathematik",
    "algebra": "Mathematik",
    "geometr": "Mathematik",
    "bio": "Biologie",
    "chem": "Chemie",
    "phys": "Physik",
    "deutsch": "Deutsch",
    "engl": "Englisch",
    "geschichte": "Geschichte",
}


def detect_subject(text: str) -> str:
    t = text.lower()
    for k, v in SUBJECT_HINTS.items():
        if k in t:
            return v
    return "Allgemein"


def generate_topics(text: str) -> List[str]:
    base = [w for w in text.split() if len(w) > 3][:4]
    if not base:
        base = ["Grundlagen", "Begriffe", "Aufgaben"]
    return list(dict.fromkeys(base))


def generate_subtopics(topics: List[str]) -> List[str]:
    subs: List[str] = []
    for t in topics:
        subs += [f"Einführung in {t}", f"Übungen zu {t}"]
    return subs[:8]


def generate_key_terms(subject: str, topics: List[str]) -> List[str]:
    fallback = {
        "Mathematik": ["Formel", "Variable", "Funktion"],
        "Biologie": ["Zelle", "Gen", "Protein"],
        "Physik": ["Kraft", "Energie", "Geschwindigkeit"],
        "Deutsch": ["Grammatik", "Analyse", "Interpretation"],
        "Englisch": ["Vocabulary", "Grammar", "Essay"],
        "Chemie": ["Molekül", "Reaktion", "Atom"],
        "Geschichte": ["Epoche", "Revolution", "Quelle"],
        "Allgemein": ["Begriff", "Definition", "Beispiel"],
    }
    return list(dict.fromkeys((topics[:2] if topics else []) + fallback.get(subject, fallback["Allgemein"])))


def build_plan(topics: List[str]) -> StudyPlan:
    items: List[PlanItem] = []
    for i, t in enumerate(topics[:5], start=1):
        items.append(
            PlanItem(
                day=i,
                title=f"{t} vertiefen",
                priority=["hoch", "mittel", "niedrig"][0 if i == 1 else (1 if i <= 3 else 2)],
                micro_goals=[f"10 Min Theorie zu {t}", f"15 Min Aufgaben zu {t}", "5 Min Wiederholung"],
                suggested_minutes=30 if i <= 2 else 25,
            )
        )
    if not items:
        items.append(
            PlanItem(
                day=1,
                title="Überblick & Ziele setzen",
                priority="hoch",
                micro_goals=["Lernziele aufschreiben", "Themenliste erstellen", "Zeitplan festlegen"],
                suggested_minutes=30,
            )
        )
    return StudyPlan(items=items)


def explanations_for(subject: str, topics: List[str]) -> List[Explanation]:
    base = ", ".join(topics) if topics else subject
    return [
        Explanation(level="kurz", content=f"Kurzüberblick: Worum geht es? Schwerpunkt: {base}."),
        Explanation(level="normal", content=f"Normale Erklärung mit Beispielen zu: {base}."),
        Explanation(level="tief", content=f"Tiefe Erklärung inkl. Herleitungen/Beweisen zu: {base}."),
    ]


def tips_for(subject: str) -> Tip:
    mapping = {
        "Mathematik": ["Beweise laut erklären", "Fehlerjournal führen", "Formelsammlung selbst bauen"],
        "Biologie": ["Skizzen anfertigen", "Karteikarten für Begriffe", "Erkläre Prozesse in eigenen Worten"],
        "Physik": ["Einheiten immer prüfen", "Alltagsbeispiele finden", "Formeln umstellen üben"],
        "Deutsch": ["Textmarker-Farbcodes", "Gliederung üben", "Zitate korrekt einbinden"],
        "Englisch": ["Täglich 10 neue Vokabeln", "Kurzaufsätze schreiben", "Shadowing beim Hören"],
        "Chemie": ["Reaktionsschemata zeichnen", "Stoffeigenschaften tabellieren", "Sicherheitsregeln wiederholen"],
        "Geschichte": ["Zeitstrahl erstellen", "Vergleiche Epochen", "Quellen kritisch prüfen"],
        "Allgemein": ["Pomodoro 25/5", "Alte Klausuren lösen", "Regelmäßig wiederholen"],
    }
    return Tip(subject=subject, tips=mapping.get(subject, mapping["Allgemein"]))


def quiz_for(subject: str, topics: List[str]) -> List[MCQ]:
    base_q = topics[:2] if topics else [subject]
    quiz: List[MCQ] = []
    for b in base_q:
        quiz.append(
            MCQ(
                question=f"Was beschreibt am besten: {b}?",
                options=[
                    MCQOption(text=f"Definition von {b}", correct=True),
                    MCQOption(text=f"Zufälliger Begriff", correct=False),
                    MCQOption(text=f"Unpassendes Beispiel", correct=False),
                ],
                explanation=f"Richtig ist die Definition von {b}, da sie den Kern trifft.",
            )
        )
    # Add a general question
    quiz.append(
        MCQ(
            question="Wie gehst du effizient vor?",
            options=[
                MCQOption(text="Konzentrationsblöcke + kurze Pausen", correct=True),
                MCQOption(text="Ohne Plan loslegen", correct=False),
                MCQOption(text="Alles aufschieben", correct=False),
            ],
            explanation="Strukturiertes Vorgehen hilft beim Lernen.",
        )
    )
    return quiz


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)):
    try:
        text_hint = extract_text_from_upload(file)
        subject = detect_subject(text_hint)
        topics = generate_topics(text_hint)
        subtopics = generate_subtopics(topics)
        key_terms = generate_key_terms(subject, topics)

        study = Study(
            filename=file.filename or "upload",
            mime_type=file.content_type or "application/octet-stream",
            topics=topics,
            subtopics=subtopics,
            key_terms=key_terms,
            summary=f"Automatische Analyse: Fach {subject}. Fokus: {', '.join(topics) if topics else 'Allgemein' }.",
        )

        plan = build_plan(topics)
        exps = explanations_for(subject, topics)
        tps = tips_for(subject)
        q = quiz_for(subject, topics)

        # Store minimal record
        await create_document("study", study.model_dump())

        return AnalyzeResponse(study=study, plan=plan, explanations=exps, tips=tps, quiz=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
