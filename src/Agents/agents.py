import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from src.Tools.tools import scrape_url, web_search

load_dotenv()

# ── Shared LLM ────────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2,
)


# ── Agent 1 : Search Agent ────────────────────────────────────────────────────
# Uses web_search tool to autonomously find recent information on a topic.
search_agent = create_agent(
    model=llm,
    tools=[web_search],
    system_prompt=(
        "You are a research search specialist. "
        "Use the web_search tool to find the most relevant and recent information "
        "about the given topic. Return all titles, URLs, and key snippets you find."
    ),
    name="SearchAgent",
)


# ── Agent 2 : Reader Agent ────────────────────────────────────────────────────
# Uses scrape_url tool to extract clean readable content from a web page.
reader_agent = create_agent(
    model=llm,
    tools=[scrape_url],
    system_prompt=(
        "You are a content extraction specialist. "
        "Use the scrape_url tool to extract and summarise the most important "
        "information from the given URL. Return only clean, readable text."
    ),
    name="ReaderAgent",
)


# ── Chain 3 : Writer Chain ────────────────────────────────────────────────────
# Writes a structured research report. Accepts optional critic feedback
# so it can improve on previous drafts.
writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured, and insightful reports."),
    (
        "human",
        """Write a concise, useful research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

{feedback}

Keep the report under 500 words and structure it as:
- Introduction
- Key Findings (3 concise points)
- Conclusion
- Sources (list all URLs found in the research)

Be factual and professional. Avoid repetition.""",
    ),
])

writer_chain = writer_prompt | llm | StrOutputParser()


# ── Chain 4 : Critic Chain ────────────────────────────────────────────────────
# Reviews the report and gives a strict numeric score + actionable feedback.
critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    (
        "human",
        """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this EXACT format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
...""",
    ),
])

critic_chain = critic_prompt | llm | StrOutputParser()
