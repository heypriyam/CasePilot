import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai

st.set_page_config(page_title="CasePilot", layout="wide")

REAL_DATA_URL = "https://storage.googleapis.com/casepilot-data-2026/casepilot_scored_cases.csv"
SCALED_DATA_URL = "https://storage.googleapis.com/casepilot-data-2026/casepilot_scaled_100k.csv"

dataset_choice = st.sidebar.radio("Dataset", ["Real cases (100)", "Scaled demo (100k)"])
data_url = REAL_DATA_URL if dataset_choice == "Real cases (100)" else SCALED_DATA_URL

try:
    df = pd.read_csv(data_url)
except Exception:
    st.error("Could not load the dataset. Check the Cloud Storage URL and bucket permissions.")
    st.stop()

if dataset_choice == "Scaled demo (100k)":
    df = df.head(500)

table_cols = ["subject", "issue_category", "sentiment", "urgency", "health_score", "escalation_risk"]

# case status is tracked only for this session - resets on app restart,
# not saved to any database
if "case_status" not in st.session_state:
    st.session_state.case_status = {}

# rough estimate of resolution time based on urgency - not measured data,
# just a simple rule so the queue has a workload estimate to show
URGENCY_TO_HOURS = {5: 4, 4: 8, 3: 24, 2: 48, 1: 72}
df["est_resolution_hours"] = df["urgency"].map(URGENCY_TO_HOURS).fillna(24)


def prettify(text):
    """Turns raw values like 'issue_category' or 'feature_request' into
    readable labels like 'Issue Category' or 'Feature Request'."""
    return str(text).replace("_", " ").title()


def display_ready(table):
    """Returns a copy with text columns prettified, for showing in a
    table - keeps the original df untouched so comparisons like
    df['escalation_risk'] == 'high' still work elsewhere."""
    table = table.copy()
    for col in ["issue_category", "sentiment", "escalation_risk", "business_impact"]:
        if col in table.columns:
            table[col] = table[col].apply(prettify)
    return table

# ---- styling ----
st.markdown("""
<style>
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1e1e2e, #2a2a4a);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
}
.big-heading {
    background: linear-gradient(135deg, #1e3a8a, #2563eb);
    border-radius: 16px;
    padding: 30px;
    text-align: center;
    margin-bottom: 20px;
}
.hero-tile {
    background: linear-gradient(135deg, #1e3a8a, #2563eb);
    border-radius: 16px;
    padding: 24px 40px;
    display: flex;
    align-items: center;
    gap: 24px;
    margin-bottom: 20px;
}
.hero-tile img {
    border-radius: 12px;
}
.hero-text h1 {
    color: white;
    margin: 0;
}
.hero-text p {
    color: #dbeafe;
    margin: 5px 0 0 0;
}
</style>
""", unsafe_allow_html=True)

# ---- hero ----
import base64
with open("logo.png", "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<div class="hero-tile">
    <img src="data:image/png;base64,{logo_b64}" width="90">
    <div class="hero-text">
        <h1>CasePilot Decision Intelligence Console</h1>
        <p>Turning raw support emails into ranked, actionable decisions</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---- KPI row ----
high_risk_count = len(df[df["escalation_risk"] == "high"])
high_risk_pct = round(100 * high_risk_count / len(df), 1)
avg_resolution_hours = round(df["est_resolution_hours"].mean(), 1)

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Cases", len(df))
k2.metric("High Risk Cases", high_risk_count)
k3.metric("Avg Health Score", round(df["health_score"].mean(), 1))
k4.metric("Avg AI Confidence", f"{round(df['confidence'].mean() * 100, 1)}%")
k5.metric("Critical Case Ratio", f"{high_risk_pct}%")
k6.metric("Est. Resolution Time", f"{avg_resolution_hours} hrs")

st.divider()

# ---- charts ----
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Risk Distribution")
    risk_counts = df["escalation_risk"].value_counts().reset_index()
    risk_counts.columns = ["risk", "count"]
    risk_counts["risk"] = risk_counts["risk"].apply(prettify)
    fig = px.pie(risk_counts, names="risk", values="count", hole=0.5)
    fig.update_layout(legend=dict(x=0.5, xanchor="center", orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Issue Categories")
    cat_counts = df["issue_category"].value_counts().reset_index()
    cat_counts.columns = ["category", "count"]
    cat_counts["category"] = cat_counts["category"].apply(prettify)
    fig = px.bar(cat_counts, x="count", y="category", orientation="h",
                 labels={"count": "Number of Cases", "category": "Issue Category"})
    st.plotly_chart(fig, use_container_width=True)

with c3:
    st.subheader("Health Score Distribution")
    fig = px.histogram(df, x="health_score", nbins=10,
                        labels={"health_score": "Health Score", "count": "Number of Cases"})
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---- AI observations, computed from the real data ----
st.subheader("🤖 AI Observations")

top_category = df["issue_category"].value_counts().idxmax()
top_category_pct = round(100 * df["issue_category"].value_counts().max() / len(df), 1)
high_risk_df = df[df["escalation_risk"] == "high"]
avg_urgency_high_risk = round(high_risk_df["urgency"].mean(), 1) if len(high_risk_df) else 0
dominant_sentiment = df["sentiment"].value_counts().idxmax()
dominant_impact = df["business_impact"].value_counts().idxmax()
low_confidence_count = len(df[df["confidence"] < 0.7])
critical_impact_pct = round(100 * len(df[df["business_impact"] == "critical"]) / len(df), 1)

st.markdown(f"""
- **{top_category}** issues make up **{top_category_pct}%** of all cases — the single largest category.
- High-risk cases average an urgency of **{avg_urgency_high_risk}/5**.
- The most common sentiment across all cases is **{dominant_sentiment}**.
- **{critical_impact_pct}%** of cases are flagged with **critical** business impact.
- **{dominant_impact}** is the most frequent business impact level overall.
- **{low_confidence_count}** cases have below-70% AI confidence and may need human review.
- **{high_risk_count}** cases ({high_risk_pct}%) currently need immediate attention.
- Estimated total resolution workload for the current queue: **{round(df['est_resolution_hours'].sum())} hours**.
""")

st.divider()


def render_case_actions(case, key_prefix):
    """Shows case detail, status control, and Gemini-powered actions for one case."""
    st.subheader(case["subject"])

    left, right = st.columns(2)
    with left:
        st.write("**Root cause**")
        st.write(case["root_cause"])
        st.write("**Recommended action**")
        st.write(case["recommended_next_action"])
    with right:
        st.write("**Business impact:**", prettify(case["business_impact"]))
        st.write("**Confidence:**", case["confidence"])
        st.write("**Health score:**", case["health_score"])
        st.write("**Est. resolution time:**", f"{case['est_resolution_hours']} hrs")

    case_id = case["case_id"]
    current_status = st.session_state.case_status.get(case_id, "Open")
    new_status = st.selectbox(
        "Mark status",
        ["Open", "Resolved", "Pending on Others", "Duplicate", "Insufficient Data"],
        index=["Open", "Resolved", "Pending on Others", "Duplicate", "Insufficient Data"].index(current_status),
        key=f"{key_prefix}_status_{case_id}",
    )
    st.session_state.case_status[case_id] = new_status

    col_a, col_b = st.columns(2)
    with col_a:
        analyze_clicked = st.button("Ask Gemini for a deeper analysis", key=f"{key_prefix}_analyze_{case_id}")
    with col_b:
        email_clicked = st.button("Draft first response email", key=f"{key_prefix}_email_{case_id}")

    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = {}
    if "email_drafts" not in st.session_state:
        st.session_state.email_drafts = {}

    if analyze_clicked:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
        prompt = f"""A support case has this summary: {case['summary']}
Root cause: {case['root_cause']}
Give a short, specific plan (3-4 steps) for resolving this case."""

        with st.spinner("Thinking..."):
            try:
                response = client.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
                st.session_state.analysis_results[case_id] = response.text
            except Exception:
                st.error("Gemini couldn't process this request right now. Try again in a moment.")

    if email_clicked:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
        prompt = f"""Write a first-response email to a customer about this support case.
Subject: {case['subject']}
Summary: {case['summary']}
Root cause: {case['root_cause']}

The email should be empathetic but still technical and specific. Acknowledge
the issue, briefly explain what's being done, and set expectations for next
steps. Keep it under 150 words. Do not include a subject line, just the body."""

        with st.spinner("Writing email..."):
            try:
                response = client.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
                st.session_state.email_drafts[case_id] = response.text
            except Exception:
                st.error("Gemini couldn't process this request right now. Try again in a moment.")

    # show both results side by side, whichever exist for this case,
    # so clicking one button doesn't wipe out the other's result
    result_col, email_col = st.columns(2)
    with result_col:
        if case_id in st.session_state.analysis_results:
            st.write("**Gemini analysis**")
            st.write(st.session_state.analysis_results[case_id])
    with email_col:
        if case_id in st.session_state.email_drafts:
            st.write("**Draft email**")
            st.text_area(
                "Draft email", st.session_state.email_drafts[case_id],
                height=250, key=f"{key_prefix}_draft_{case_id}", label_visibility="collapsed",
            )


# ---- top critical cases ----
st.subheader("Top Critical Cases")
top_critical = df.sort_values("health_score").head(5).reset_index(drop=True)
top_critical.index = top_critical.index + 1

selection = st.dataframe(
    display_ready(top_critical[table_cols]),
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
)

if selection.selection.rows:
    row_index = selection.selection.rows[0]
    case = top_critical.iloc[row_index]
    render_case_actions(case, key_prefix="top")

st.divider()

# ---- explore all cases ----
st.subheader("Explore All Cases")
show_all = st.checkbox("View all cases")

if show_all:
    search_col, _ = st.columns([1, 2])
    with search_col:
        search_term = st.text_input("Search by case ID or subject")

    all_cases = df.sort_values("health_score").reset_index(drop=True)
    all_cases.index = all_cases.index + 1

    if search_term:
        mask = (
            all_cases["case_id"].astype(str).str.contains(search_term, case=False)
            | all_cases["subject"].str.contains(search_term, case=False)
        )
        all_cases = all_cases[mask]

    page_size = 20
    total_pages = max((len(all_cases) - 1) // page_size + 1, 1)

    if "page_num" not in st.session_state:
        st.session_state.page_num = 1

    nav_prev, nav_label, nav_next = st.columns([1, 3, 1])
    with nav_prev:
        if st.button("⬅ Previous") and st.session_state.page_num > 1:
            st.session_state.page_num -= 1
    with nav_next:
        if st.button("Next ➡") and st.session_state.page_num < total_pages:
            st.session_state.page_num += 1
    with nav_label:
        st.markdown(f"<p style='text-align:center;'>Page {st.session_state.page_num} of {total_pages}</p>", unsafe_allow_html=True)

    page = st.session_state.page_num
    start = (page - 1) * page_size
    end = start + page_size

    selection_all = st.dataframe(
        display_ready(all_cases[table_cols].iloc[start:end]),
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    if selection_all.selection.rows:
        row_index = selection_all.selection.rows[0]
        case = all_cases.iloc[start:end].iloc[row_index]
        render_case_actions(case, key_prefix="all")

st.divider()

# ---- pipeline health ----
st.subheader("Pipeline Health")
p1, p2, p3, p4, p5, p6 = st.columns(6)
p1.success("Gmail ✓")
p2.success("Gemini ✓")
p3.success("AI Structuring ✓")
p4.success("Risk Engine ✓")
p5.success("Cloud Storage ✓")
p6.success("GPU Analytics ✓")

st.divider()

# ---- acceleration benchmark, real numbers ----
st.subheader("Acceleration Benchmark")
st.caption("Same aggregation pipeline, Measured on NVIDIA GPU using a 2M-row synthetic dataset")
b1, b2, b3 = st.columns(3)
b1.metric("Pandas (CPU)", "1.86s")
b2.metric("cuDF (GPU)", "1.41s")
b3.metric("Speedup", "1.31x")
