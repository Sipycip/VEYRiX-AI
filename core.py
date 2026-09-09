import math
import re

import requests

from research import research


# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

MODEL = "qwen3:1.7b"

OLLAMA_TIMEOUT = 120


# ============================================================
# RESEARCH DETECTION
# ============================================================

RESEARCH_PATTERNS = [
    r"\bright now\b",
    r"\bcurrently\b",
    r"\btoday\b",
    r"\blatest\b",
    r"\bmost recent\b",
    r"\bcurrent\b",
    r"\bwho is\b.*\bnow\b",
    r"\bwhat is\b.*\bnow\b",
    r"\bhow much\b.*\bworth\b",
    r"\bnet worth\b",
    r"\bnews\b",
    r"\brecent\b",
    r"\b2026\b",
    r"\bthis year\b",
    r"\bresearch\b",
    r"\blook up\b",
    r"\bsearch\b",
    r"\bfind out\b",
    r"\baccording to\b",
]


def should_research(question):

    q = (
        question or ""
    ).lower().strip()

    for pattern in RESEARCH_PATTERNS:

        if re.search(
            pattern,
            q,
        ):
            return True

    return False


# ============================================================
# OLLAMA
# ============================================================

def ask_qwen(prompt):

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,

        # Keep responses faster and more deterministic.
        "options": {
            "temperature": 0.3,
        },
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        answer = data.get(
            "response",
            "",
        )

        if not answer:

            return (
                "I wasn't able to generate "
                "a response."
            )

        return answer.strip()

    except requests.exceptions.ConnectionError:

        return (
            "I can't connect to Ollama right now. "
            "Make sure Ollama is running."
        )

    except requests.exceptions.Timeout:

        return (
            "The local AI model took too long "
            "to respond."
        )

    except requests.exceptions.RequestException as error:

        print(
            f"[VEYRiX] Ollama error: {error}"
        )

        return (
            "I encountered an error while "
            "communicating with the local AI model."
        )

    except Exception as error:

        print(
            "[VEYRiX] Unexpected Ollama error: "
            f"{error}"
        )

        return (
            "Something went wrong while generating "
            "the response."
        )


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are VEYRiX, a local AI assistant.

You are designed to eventually serve as the intelligence
system for Project AXION, a humanoid robotics project.

Project AXION is the user's own humanoid robotics project.

Do not invent organizations, universities, companies, or
other owners for Project AXION.

You are running locally through Ollama using Qwen3 1.7B.

Rules:

- Be accurate.
- Be concise unless detail is useful.
- Do not pretend to know something you do not know.
- Do not claim to have performed actions you did not perform.
- Do not claim to physically control AXION.
- AXION is the user's humanoid robotics project.
- VEYRiX is intended to eventually become part of AXION's
  intelligence system.
- Explain technical subjects clearly.
- When the user asks for code, provide working code.
"""


# ============================================================
# RESEARCH PROMPT
# ============================================================

RESEARCH_SYSTEM_PROMPT = """
You are VEYRiX, a local AI research-capable assistant.

The research system has gathered external evidence.

The structured section called VERIFIED CURRENT FACT has
priority over your training knowledge.

Rules:

1. Never contradict a verified structured fact.
2. Never replace a verified current value with an older value.
3. Never invent a missing number.
4. Prefer direct authoritative evidence.
5. Prefer current evidence for current questions.
6. Forbes and Bloomberg are authoritative sources for
   billionaire rankings and estimated net worth.
7. If no verified value exists, clearly say so.
8. Do not describe the internal research pipeline unless asked.
9. Answer the user's question directly.
"""


# ============================================================
# CONVERSATION
# ============================================================

def extract_conversation(conversation):

    # --------------------------------------------------------
    # Single string
    # --------------------------------------------------------

    if isinstance(
        conversation,
        str,
    ):

        return (
            conversation.strip(),
            "",
        )

    # --------------------------------------------------------
    # Invalid input
    # --------------------------------------------------------

    if not isinstance(
        conversation,
        list,
    ):

        return (
            "",
            "",
        )

    latest_user_message = ""

    messages = []

    for message in conversation:

        if not isinstance(
            message,
            dict,
        ):
            continue

        role = message.get(
            "role",
            "",
        )

        content = message.get(
            "content",
            "",
        )

        if not isinstance(
            content,
            str,
        ):
            continue

        content = content.strip()

        if not content:
            continue

        if role == "user":

            latest_user_message = content

            messages.append(
                f"User: {content}"
            )

        elif role == "assistant":

            messages.append(
                f"VEYRiX: {content}"
            )

    if not latest_user_message:

        return (
            "",
            "",
        )

    # Do not include the newest user message twice.
    if (
        messages
        and messages[-1]
        == f"User: {latest_user_message}"
    ):
        messages = messages[:-1]

    context = "\n".join(
        messages[-8:]
    )

    return (
        latest_user_message,
        context,
    )


# ============================================================
# SOURCE HELPERS
# ============================================================

def clean_source_content(source):

    evidence = source.get(
        "evidence_excerpt",
        "",
    )

    if isinstance(
        evidence,
        str,
    ) and evidence.strip():

        return evidence.strip()

    content = source.get(
        "content",
        "",
    )

    if isinstance(
        content,
        str,
    ) and content.strip():

        return content.strip()

    snippet = source.get(
        "snippet",
        "",
    )

    if isinstance(
        snippet,
        str,
    ) and snippet.strip():

        return snippet.strip()

    return ""


def source_priority(source):

    domain = (
        source.get(
            "domain",
            "",
        )
        or ""
    ).lower()

    authority = source.get(
        "authority",
        0,
    )

    if not isinstance(
        authority,
        (int, float),
    ):
        authority = 0

    score = authority * 10

    verified_fact = source.get(
        "verified_fact"
    )

    if isinstance(
        verified_fact,
        dict,
    ):
        score += 5000

    if source.get(
        "direct",
        False,
    ):
        score += 1000

    if source.get(
        "page_readable",
        False,
    ):
        score += 200

    if domain in {
        "forbes.com",
        "www.forbes.com",
        "bloomberg.com",
        "www.bloomberg.com",
    }:
        score += 500

    elif domain in {
        "reuters.com",
        "www.reuters.com",
        "apnews.com",
        "www.apnews.com",
        "bbc.com",
        "www.bbc.com",
        "cnbc.com",
        "www.cnbc.com",
    }:
        score += 300

    return score


# ============================================================
# RICHEST-PERSON QUESTION DETECTION
# ============================================================

def is_richest_person_question(question):

    q = (
        question or ""
    ).lower()

    patterns = [
        r"\brichest person\b",
        r"\briches person\b",
        r"\brichest man\b",
        r"\brichest woman\b",
        r"\bwho is the richest\b",
        r"\bwho's the richest\b",
        r"\bwho is richest\b",
        r"\bwealthiest person\b",
        r"\bworld'?s richest\b",
    ]

    return any(
        re.search(
            pattern,
            q,
        )
        for pattern in patterns
    )


# ============================================================
# VERIFIED FACT EXTRACTION
# ============================================================

def get_verified_richest_fact(sources):

    if not isinstance(
        sources,
        list,
    ):
        return None

    verified_sources = []

    for source in sources:

        if not isinstance(
            source,
            dict,
        ):
            continue

        fact = source.get(
            "verified_fact"
        )

        if not isinstance(
            fact,
            dict,
        ):
            continue

        person = fact.get(
            "person"
        )

        amount = fact.get(
            "amount"
        )

        if not isinstance(
            person,
            str,
        ):
            continue

        person = person.strip()

        if not person:
            continue

        if isinstance(
            amount,
            bool,
        ):
            continue

        if not isinstance(
            amount,
            (int, float),
        ):
            continue

        if not math.isfinite(
            amount
        ):
            continue

        if amount <= 0:
            continue

        verified_sources.append(
            source
        )

    if not verified_sources:

        return None

    best_source = max(
        verified_sources,
        key=source_priority,
    )

    fact = best_source[
        "verified_fact"
    ]

    amount_raw = fact.get(
        "amount_raw"
    )

    if not isinstance(
        amount_raw,
        str,
    ) or not amount_raw.strip():

        currency = fact.get(
            "currency",
            "$",
        )

        amount_raw = (
            f"{currency}"
            f"{fact['amount']:,.0f}"
        )

    title = best_source.get(
        "title",
        "",
    )

    domain = best_source.get(
        "domain",
        "",
    )

    source_name = (
        title
        or domain
        or "authoritative source"
    )

    return {
        "person": fact[
            "person"
        ].strip(),

        "amount": fact[
            "amount"
        ],

        "net_worth": (
            amount_raw.strip()
        ),

        "currency": fact.get(
            "currency",
            "",
        ),

        "unit": fact.get(
            "unit",
            "",
        ),

        "supporting_sources": fact.get(
            "supporting_sources",
            1,
        ),

        "source": source_name,

        "domain": domain,

        "url": best_source.get(
            "url",
            "",
        ),

        "evidence": clean_source_content(
            best_source
        ),
    }


# ============================================================
# FORMAT RESEARCH EVIDENCE
# ============================================================

def format_research_evidence(sources):

    if not sources:

        return (
            "No usable research evidence "
            "was found."
        )

    ranked = sorted(
        sources,
        key=source_priority,
        reverse=True,
    )

    sections = []

    for index, source in enumerate(
        ranked,
        start=1,
    ):

        if not isinstance(
            source,
            dict,
        ):
            continue

        title = source.get(
            "title",
            source.get(
                "name",
                "Untitled source",
            ),
        )

        domain = source.get(
            "domain",
            "unknown",
        )

        url = source.get(
            "url",
            "",
        )

        evidence = clean_source_content(
            source
        )

        fact = get_verified_richest_fact(
            [source]
        )

        section = [
            f"SOURCE {index}",
            f"Title: {title}",
            f"Domain: {domain}",
        ]

        if fact:

            section.extend(
                [
                    "VERIFIED CURRENT FACT",
                    (
                        "Person: "
                        f"{fact['person']}"
                    ),
                    (
                        "Current net worth: "
                        f"{fact['net_worth']}"
                    ),
                ]
            )

        if url:

            section.append(
                f"URL: {url}"
            )

        if evidence:

            section.append(
                "\nEVIDENCE:\n"
                + evidence[:2500]
            )

        sections.append(
            "\n".join(
                section
            )
        )

    return (
        "\n\n"
        + (
            "\n\n"
            + ("-" * 60)
            + "\n\n"
        ).join(
            sections
        )
    )


# ============================================================
# RESEARCH ANSWER
# ============================================================

def answer_with_research(
    question,
    sources,
    conversation_context="",
):

    richest_fact = None

    if is_richest_person_question(
        question
    ):

        richest_fact = (
            get_verified_richest_fact(
                sources
            )
        )

    # --------------------------------------------------------
    # IMPORTANT FAST STRUCTURED ANSWER
    #
    # If research.py already verified the fact, do NOT make
    # Qwen regenerate it.
    #
    # This:
    # - prevents hallucination
    # - prevents old training data
    # - makes responses faster
    # --------------------------------------------------------

    if richest_fact:

        source_name = (
            richest_fact[
                "source"
            ]
        )

        return (
            f"{richest_fact['person']} is currently "
            f"the richest person in the world, with "
            f"an estimated net worth of "
            f"{richest_fact['net_worth']}, according "
            f"to {source_name}."
        )

    # --------------------------------------------------------
    # No structured fact.
    # Let Qwen synthesize normal research evidence.
    # --------------------------------------------------------

    evidence = format_research_evidence(
        sources
    )

    prompt = f"""
{RESEARCH_SYSTEM_PROMPT}

CURRENT USER QUESTION:
{question}

CONVERSATION CONTEXT:
{conversation_context}

RESEARCH EVIDENCE:
{evidence}

Answer the user's current question.

Use the supplied evidence.

Do not invent facts that are not supported by the evidence.

If current information could not be verified, say so briefly.
"""

    return ask_qwen(
        prompt
    )


# ============================================================
# NON-RESEARCH ANSWER
# ============================================================

def answer_without_research(
    question,
    conversation_context="",
):

    prompt = f"""
{SYSTEM_PROMPT}

CONVERSATION CONTEXT:
{conversation_context}

CURRENT USER QUESTION:
{question}

VEYRiX:
"""

    return ask_qwen(
        prompt
    )


# ============================================================
# MAIN VEYRIX FUNCTION
# ============================================================

def ask_veyrix(conversation):

    question, conversation_context = (
        extract_conversation(
            conversation
        )
    )

    if not question:

        return (
            "Please enter a message."
        )

    print()

    print(
        f"[VEYRiX] Question: {question}"
    )

    if conversation_context:

        print(
            "[VEYRiX] Conversation context detected."
        )

    # --------------------------------------------------------
    # RESEARCH
    # --------------------------------------------------------

    if should_research(
        question
    ):

        print(
            "[VEYRiX] Research required."
        )

        try:

            sources = research(
                question
            )

            print(
                f"[VEYRiX] Research returned "
                f"{len(sources)} sources."
            )

            if is_richest_person_question(
                question
            ):

                verified_fact = (
                    get_verified_richest_fact(
                        sources
                    )
                )

                if verified_fact:

                    print()
                    print(
                        "[VEYRiX] VERIFIED CURRENT FACT"
                    )

                    print(
                        f"[VEYRiX] Person: "
                        f"{verified_fact['person']}"
                    )

                    print(
                        f"[VEYRiX] Net worth: "
                        f"{verified_fact['net_worth']}"
                    )

                    print(
                        f"[VEYRiX] Source: "
                        f"{verified_fact['source']}"
                    )

                    # Direct structured response.
                    # No second model call necessary.
                    return answer_with_research(
                        question,
                        sources,
                        conversation_context,
                    )

                print(
                    "[VEYRiX] No verified current "
                    "richest-person fact found."
                )

                return (
                    "The current richest person's "
                    "net worth could not be verified."
                )

            # ------------------------------------------------
            # GENERAL RESEARCH
            # ------------------------------------------------

            if not sources:

                print(
                    "[VEYRiX] No usable research evidence."
                )

                return (
                    "I couldn't find enough reliable "
                    "current information to answer that."
                )

            print(
                "[VEYRiX] Sending research evidence "
                "to Qwen..."
            )

            return answer_with_research(
                question,
                sources,
                conversation_context,
            )

        except Exception as error:

            print(
                "[VEYRiX] Research error: "
                f"{error}"
            )

            # Do not let model memory pretend
            # to know current information.
            if is_richest_person_question(
                question
            ):

                return (
                    "I couldn't verify the current "
                    "richest-person ranking."
                )

            return (
                "I couldn't complete the current "
                "research request."
            )

    # --------------------------------------------------------
    # NORMAL LOCAL RESPONSE
    # --------------------------------------------------------

    print(
        "[VEYRiX] No research required."
    )

    return answer_without_research(
        question,
        conversation_context,
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print(
        "=" * 70
    )

    print(
        "VEYRiX CORE TEST"
    )

    print(
        "=" * 70
    )

    answer = ask_veyrix(
        "Who is the richest person right now?"
    )

    print()

    print(
        "VEYRiX:"
    )

    print(
        answer
    )
