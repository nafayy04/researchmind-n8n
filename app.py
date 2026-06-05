import streamlit as st
import requests
import re

# Webhook URLs
WEBHOOK_URL = "http://localhost:5678/webhook/9dc7305e-4aa3-4a9c-aea3-ba11d695e483"
DEEP_DIVE_URL = "http://localhost:5678/webhook/deep - dive"  # replace with your actual deep dive webhook URL

st.set_page_config(page_title="ResearchMind", page_icon="🔬", layout="centered")

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #0f1117; }
    .title { text-align: center; font-size: 2.8em; font-weight: bold; color: #ffffff; margin-bottom: 5px; }
    .subtitle { text-align: center; color: #888; margin-bottom: 30px; font-size: 1em; }
    .paper-card {
        background-color: #1e1e2e;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #2e2e3e;
    }
    .paper-title { font-size: 1.1em; font-weight: bold; color: #7eb8f7; }
    .paper-meta { color: #aaa; font-size: 0.85em; margin-top: 4px; }
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75em;
        font-weight: bold;
        margin-right: 6px;
    }
    .badge-arxiv { background-color: #2d4a7a; color: #7eb8f7; }
    .badge-openalex { background-color: #2d5a3d; color: #7ef7a0; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🔬 ResearchMind</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI Research Assistant for PhD Students</div>', unsafe_allow_html=True)

# SIDEBAR FILTERS
st.sidebar.header("Search Filters")
min_citations, max_citations = st.sidebar.slider(
    "Citation Range",
    min_value=0,
    max_value=10000,
    value=(0, 10000),
    step=50
)
st.sidebar.caption(f"Showing papers with **{min_citations} – {max_citations}** citations")

# MAIN TOPIC INPUT
topic = st.text_input("Enter your research topic", placeholder="e.g. machine learning in cancer detection")
search = st.button("🔍 Search Papers", use_container_width=True)

# SESSION STATE
if "papers" not in st.session_state:
    st.session_state.papers = []
if "deep_dive_results" not in st.session_state:
    st.session_state.deep_dive_results = {}
if "search_topic" not in st.session_state:
    st.session_state.search_topic = ""

def parse_papers(raw_text):
    """Parse raw Groq output into list of paper dicts"""
    papers = []
    blocks = re.split(r'\n(?=\d+\.)', raw_text.strip())

    for block in blocks:
        if not block.strip():
            continue
        paper = {}

        def extract(label):
            pattern = rf'{label}:\s*(.+?)(?=\n\s*\w[\w\s]*:|$)'
            match = re.search(pattern, block, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else "N/A"

        paper["title"]     = extract("Title")
        paper["authors"]   = extract("Authors")
        paper["year"]      = extract("Year")
        paper["citations"] = extract("Citations")
        paper["why"]       = extract("Why this matters")
        paper["summary"]   = extract("Summary")
        paper["source"]    = extract("Source")

        # Use summary as abstract for deep dive
        paper["abstract"] = paper["summary"] if paper["summary"] != "N/A" else ""

        # Skip hallucinated / incomplete papers
        if (paper["title"] == "N/A" or
            paper["authors"] == "N/A" or
            paper["year"] == "N/A" or
            paper["citations"] == "N/A" or
            "not available" in paper["title"].lower() or
            "not available" in paper["year"].lower() or
            "not available" in paper["citations"].lower() or
            "not available" in paper["authors"].lower()):
            continue

        papers.append(paper)

    return papers

def call_deep_dive(paper):
    """Call deep dive webhook with paper details"""
    payload = {
        "title": paper["title"],
        "abstract": paper["abstract"],
        "year": paper["year"],
        "citations": paper["citations"],
        "source": paper["source"]
    }

    # Debug — visible in terminal
    print("=== DEEP DIVE PAYLOAD ===")
    print(payload)
    print("=========================")

    response = requests.post(DEEP_DIVE_URL, json=payload, timeout=60)

    # Debug — visible in terminal
    print("=== DEEP DIVE RESPONSE ===")
    print(response.text[:500])
    print("==========================")

    return response.text.replace("\\n", "\n").replace("\\*", "*")

# SEARCH
if search:
    if not topic.strip():
        st.warning("Please enter a research topic!")
    else:
        with st.spinner("Searching millions of research papers..."):
            try:
                payload = {
                    "topic": topic,
                    "min_citations": min_citations,
                    "max_citations": max_citations
                }
                response = requests.post(WEBHOOK_URL, json=payload, timeout=60)
                result = response.text

                if result:
                    parsed = parse_papers(result)
                    st.session_state.papers = parsed
                    st.session_state.deep_dive_results = {}
                    st.session_state.search_topic = topic
                else:
                    st.error("No results returned. Check if your n8n workflow is active.")

            except Exception as e:
                st.error(f"Error: {str(e)}")

# DISPLAY PAPERS
if st.session_state.papers:
    st.success(f"Found **{len(st.session_state.papers)}** papers for: **{st.session_state.search_topic}** | Citations: {min_citations} – {max_citations}")
    st.markdown("---")

    for i, paper in enumerate(st.session_state.papers):
        badge_class = "badge-arxiv" if "arxiv" in paper["source"].lower() else "badge-openalex"

        st.markdown(f"""
            <div class="paper-card">
                <div class="paper-title">{paper['title']}</div>
                <div class="paper-meta">
                    👥 {paper['authors']}<br>
                    📅 {paper['year']} &nbsp;|&nbsp; 📊 {paper['citations']} citations &nbsp;|&nbsp;
                    <span class="badge {badge_class}">{paper['source']}</span>
                </div>
                <br>
                <b>💡 Why this matters:</b> {paper['why']}<br><br>
                <b>📄 Summary:</b> {paper['summary']}
            </div>
        """, unsafe_allow_html=True)

        # Deep Dive Button
        if st.button(f"🔍 Deep Dive", key=f"deep_dive_{i}"):
            with st.spinner(f"Analyzing '{paper['title'][:50]}...'"):
                try:
                    result = call_deep_dive(paper)
                    st.session_state.deep_dive_results[i] = result
                except Exception as e:
                    st.session_state.deep_dive_results[i] = f"Error: {str(e)}"

        # Show deep dive result if available
        if i in st.session_state.deep_dive_results:
            with st.expander(f"📊 Deep Dive — {paper['title'][:60]}...", expanded=True):
                st.markdown(st.session_state.deep_dive_results[i])

        st.markdown("---")

elif st.session_state.search_topic:
    st.warning("No valid papers found. Try a different topic or broader citation range.")
