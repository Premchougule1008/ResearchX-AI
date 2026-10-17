# 🔬 ResearchX AI — Multi-Agent Research Assistant

**From a research question to a structured report, powered by collaborative AI agents.**

ResearchX AI is an AI-powered research assistant that automates the process of discovering information, extracting relevant web content, generating structured research reports, and reviewing the quality of those reports.

Built using Python, LangChain, Google Gemini, Tavily Search, and FastAPI, ResearchX AI combines four specialized AI components into a single research workflow.

Instead of manually searching multiple websites and compiling information, users can enter a research topic and let ResearchX AI perform the research process automatically.

## ✨ Key Features

* **🔎 Intelligent Web Search:** Uses Tavily Search to discover relevant web sources and retrieve information about a research topic.
* **📖 Automated Content Extraction:** Extracts readable content from web pages using Trafilatura, Readability, BeautifulSoup, and Requests.
* **✍️ AI-Powered Report Generation:** Generates structured research reports containing an introduction, key findings, conclusion, and source links.
* **🧠 AI Critic and Quality Review:** Evaluates generated reports, assigns a score out of 10, and provides actionable feedback.
* **🔄 Iterative Report Improvement:** Uses critic feedback to revise reports, with a maximum of three writing and review iterations.
* **🛡️ Quota-Aware Fallback:** When a recognized Gemini quota error occurs, the application attempts to generate a source-based research brief from available search results.
* **🌐 Interactive Web Interface:** Provides a dedicated frontend for submitting research topics and exploring the resulting reports.
* **📚 Source Transparency:** Displays collected search results and extracted content alongside the generated report.
* **📋 Export and Copy:** Allows users to copy research reports or download them through the interface.

## 🎯 Problem Statement

Researching a topic often involves several repetitive tasks:

1. Searching for relevant information across websites.
2. Identifying useful sources.
3. Reading and extracting important information.
4. Organizing findings into a structured document.
5. Reviewing the document for clarity and quality.
6. Revising the report based on feedback.

ResearchX AI brings these tasks together into an automated, multi-stage research pipeline.

## 💡 How ResearchX AI Works

ResearchX AI uses four specialized AI components to complete a research task.

### 1. Search Agent 🔎

The Search Agent uses the Tavily Search tool to discover relevant information about the user's topic.

Responsibilities:

* Search the web for relevant information.
* Retrieve source titles, URLs, and snippets.
* Provide search results to the next stage.

### 2. Reader Agent 📖

The Reader Agent uses a web-scraping tool to extract and summarize the content of a selected source.

Responsibilities:

* Retrieve content from a web page.
* Extract readable text.
* Remove irrelevant page elements where possible.
* Provide extracted information for report generation.

### 3. Writer Chain ✍️

The Writer Chain uses Google Gemini to generate a structured research report from the gathered information.

Responsibilities:

* Understand the research topic.
* Synthesize search results and extracted content.
* Organize the report into meaningful sections.
* Incorporate feedback when a revision is required.

The generated report follows a structured format:

* Introduction
* Key Findings
* Conclusion
* Sources

### 4. Critic Chain 🧠

The Critic Chain evaluates the generated report and provides a numerical score and written feedback.

Responsibilities:

* Assess the report's quality.
* Identify strengths and weaknesses.
* Suggest improvements.
* Provide feedback to the Writer Chain.

If the score is below the configured acceptance threshold of 7/10, the Writer Chain receives another opportunity to improve the report, up to the maximum iteration limit.

## 🔄 Research Workflow

```text
                  ┌─────────────────────┐
                  │    User Research    │
                  │        Topic        │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │    Search Agent     │
                  │   Tavily Search     │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │    Reader Agent     │
                  │   Web Extraction    │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │     Writer Chain    │
                  │  Gemini Report Gen. │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │     Critic Chain    │
                  │ Quality Evaluation  │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │    Score >= 7/10?   │
                  └──────────┬──────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                Yes                      No
                 │                       │
                 ▼                       ▼
        ┌────────────────┐     ┌────────────────┐
        │  Final Report  │     │ Revise Report  │
        └────────────────┘     │ Max 3 Attempts │
                               └───────┬────────┘
                                       │
                                       └──► Writer
```

**Note:** The research pipeline includes a quota-aware fallback that can produce a source-based research brief when a recognized Gemini quota error occurs. The fallback relies on available search snippets and does not perform the normal AI writing and critic-review process.

## 🏗️ System Architecture

ResearchX AI follows a modular architecture that separates the web interface, API layer, AI agents, research orchestration, and external tools.

```text
┌───────────────────────────────────────────┐
│              Frontend                     │
│         HTML + CSS + JavaScript           │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│              FastAPI Backend              │
│             POST /api/research             │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│          Research Pipeline                │
│                                           │
│  Search Agent → Reader Agent              │
│         → Writer Chain → Critic Chain     │
└──────────────┬────────────────┬───────────┘
               │                │
               ▼                ▼
┌──────────────────────┐  ┌─────────────────┐
│     Tavily Search    │  │   Google Gemini │
│                      │  │                 │
│ Web Search Results   │  │ Report Writing  │
│ Source Information   │  │ Critic Review   │
└──────────────────────┘  └─────────────────┘
               │
               ▼
┌───────────────────────────────────────────┐
│           Web Content Extraction          │
│ Requests + Trafilatura + Readability      │
│               + BeautifulSoup              │
└───────────────────────────────────────────┘
```

## 🛠️ Technology Stack

| Category             | Technologies             |
| -------------------- | ------------------------ |
| Programming Language | Python                   |
| Large Language Model | Google Gemini            |
| AI Framework         | LangChain                |
| AI Agent Creation    | LangChain Agents         |
| Web Search           | Tavily Search API        |
| Web Scraping         | Requests, BeautifulSoup  |
| Content Extraction   | Trafilatura, Readability |
| Backend API          | FastAPI                  |
| Data Validation      | Pydantic                 |
| Frontend             | HTML, CSS, JavaScript    |
| Configuration        | Python Dotenv            |
| ASGI Server          | Uvicorn                  |

## 📂 Project Structure

```text
ResearchX-AI/
│
├── Frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── src/
│   ├── Agents/
│   │   └── agents.py
│   │
│   ├── Pipelines/
│   │   └── pipeline.py
│   │
│   └── Tools/
│       └── tools.py
│
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

### Response Structure

A successful response contains the following fields:

| Field             | Description                                          |
| ----------------- | ---------------------------------------------------- |
| `topic`           | The submitted research topic                         |
| `report`          | The generated research report                        |
| `feedback`        | The critic's review or fallback status message       |
| `search_results`  | The collected search results                         |
| `scraped_content` | The extracted source content                         |
| `fallback`        | Indicates whether the source-based fallback was used |

The API validates incoming requests using Pydantic and returns structured JSON responses.

## 🧪 Example Use Cases

ResearchX AI can assist with preliminary research across several domains.

**Artificial Intelligence**

* Recent developments in generative AI.
* Comparison of machine learning approaches.
* Applications of AI in different industries.

**Technology Research**

* Emerging software technologies.
* Cloud computing trends.
* Cybersecurity developments.

**Business Research**

* Industry trends.
* Technology adoption.
* Market developments.

**Academic Research**

* Preliminary topic exploration.
* Finding relevant online sources.
* Preparing a structured starting point for further research.

The relevance and accuracy of the results depend on the available search sources, source accessibility, and the language model's output.

## 🛡️ Error Handling and Fallback

ResearchX AI includes basic error handling for failures during research execution.

* API validation errors are handled by FastAPI and Pydantic.
* Research pipeline failures are logged by the backend.
* The API returns an appropriate HTTP error when the pipeline fails.
* Recognized Gemini quota errors trigger an attempt to generate a source-based research brief.
* If the fallback cannot retrieve usable search results, the research request can still fail.

The fallback mode provides a limited alternative when the AI service quota is exhausted. It should not be treated as equivalent to the full AI-generated research workflow.

## 🔐 Environment Variables

| Variable         | Purpose                                         |
| ---------------- | ----------------------------------------------- |
| `GOOGLE_API_KEY` | Authenticates requests to the Google Gemini API |
| `TAVILY_API_KEY` | Authenticates Tavily web-search requests        |

Keep these credentials private and configure them through environment variables.

## 👨‍💻 Author

**Prem Chougule**

GitHub: [@Premchougule1008](https://github.com/Premchougule1008)

Project Repository: [ResearchX-AI](https://github.com/Premchougule1008/ResearchX-AI)

---

**ResearchX AI — Search smarter. Research faster. Build better insights.**

