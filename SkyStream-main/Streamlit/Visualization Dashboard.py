# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

st.set_page_config(page_title="Flight Delay Dashboard", layout="wide")
st.title("✈️ Flight Delay Dashboard")

# ----------------- Efficient Loader with Row Sampling -----------------

@st.cache_data
def load_sampled_csvs():
    df_2021 = pd.read_csv("Combined_Flights_2021.csv", skiprows=lambda i: i > 0 and np.random.rand() > 20000/2500000, low_memory=False)
    df_2022 = pd.read_csv("Combined_Flights_2022.csv", skiprows=lambda i: i > 0 and np.random.rand() > 20000/1800000, low_memory=False)
    return pd.concat([df_2021, df_2022], ignore_index=True)

df = load_sampled_csvs()

# ----------------- Sidebar Filters -----------------

st.sidebar.header("🔍 Filters")

# Month Slider
if "Month" in df.columns:
    min_month, max_month = int(df["Month"].min()), int(df["Month"].max())
    month_range = st.sidebar.slider("🗓️ Select Month Range", min_month, max_month, (min_month, max_month))
    df = df[(df["Month"] >= month_range[0]) & (df["Month"] <= month_range[1])]

# Checkbox filter for each weekday
if "DayOfWeek" in df.columns:
    st.sidebar.markdown("📅 **Select Days of Week**")
    weekdays = {
        1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday",
        5: "Friday", 6: "Saturday", 7: "Sunday"
    }
    selected_days = []
    for num, name in weekdays.items():
        if st.sidebar.checkbox(name, value=True, key=f"day_{num}"):
            selected_days.append(num)
    df = df[df["DayOfWeek"].isin(selected_days)]


# Airline Selector
airlines = df["Airline"].dropna().unique()
selected_airline = st.sidebar.selectbox("✈️ Select Airline", sorted(airlines))

# Origin Airport Selector
#if "Origin" in df.columns:
 #   origins = df["Origin"].dropna().unique()
  #  selected_origin = st.sidebar.selectbox("🛫 Select Origin Airport (optional)", ["All"] + sorted(origins.tolist()))
   # if selected_origin != "All":
    #    df = df[df["Origin"] == selected_origin]

# Departure Delay Slider
if "DepDelayMinutes" in df.columns:
    min_delay = int(df["DepDelayMinutes"].min())
    max_delay = int(df["DepDelayMinutes"].max())
    delay_range = st.sidebar.slider("⏱️ Filter by Departure Delay (min)", min_delay, max_delay, (min_delay, max_delay))
    df = df[(df["DepDelayMinutes"] >= delay_range[0]) & (df["DepDelayMinutes"] <= delay_range[1])]

# Cancelled/Diverted Checkboxes
show_cancelled = st.sidebar.checkbox("✅ Show Cancelled Flights Only", value=False)
show_diverted = st.sidebar.checkbox("🔀 Show Diverted Flights Only", value=False)

# ----------------- Apply Filters -----------------

filtered_df = df[df["Airline"] == selected_airline]

if show_cancelled:
    filtered_df = filtered_df[filtered_df["Cancelled"] == 1]

if show_diverted:
    filtered_df = filtered_df[filtered_df["Diverted"] == 1]

# ----------------- Display Data -----------------

st.subheader(f"📋 Sample Data for {selected_airline}")
st.dataframe(filtered_df.head(20))

# ----------------- Delay Percentage -----------------

if "DepDel15" in filtered_df.columns and len(filtered_df) > 0:
    delay_pct = (filtered_df["DepDel15"].sum() / len(filtered_df)) * 100
    st.metric(label=f"🚦 Delay Percentage", value=f"{delay_pct:.2f}%")
elif len(filtered_df) == 0:
    st.warning("No records match the selected filters.")

# ----------------- Graphs -----------------

# 1. Avg Delay by Hour
if "CRSDepTime" in filtered_df.columns and "DepDelayMinutes" in filtered_df.columns:
    st.subheader("⏰ Avg Departure Delay by Hour")
    filtered_df["Hour"] = (filtered_df["CRSDepTime"] // 100).astype(int)
    delay_by_hour = filtered_df.groupby("Hour")["DepDelayMinutes"].mean().dropna()

    fig1, ax1 = plt.subplots()
    delay_by_hour.plot(kind='line', marker='o', ax=ax1)
    ax1.set_xlabel("Hour")
    ax1.set_ylabel("Avg Delay (min)")
    ax1.set_title("Average Departure Delay by Hour")
    st.pyplot(fig1)

# 2. Cancelled vs Diverted
if "Cancelled" in filtered_df.columns and "Diverted" in filtered_df.columns:
    st.subheader("⚠️ Cancelled vs Diverted Flights")
    status_df = pd.DataFrame({
        "Cancelled": [filtered_df["Cancelled"].sum()],
        "Diverted": [filtered_df["Diverted"].sum()]
    }).T.rename(columns={0: "Count"})

    fig2, ax2 = plt.subplots()
    status_df.plot(kind="bar", ax=ax2, legend=False)
    ax2.set_ylabel("Count")
    st.pyplot(fig2)

# 3. Delay Rate by Airline and Departure Time Block (with multi-select)
if "Airline" in df.columns and "DepTimeBlk" in df.columns and "DepDel15" in df.columns:
    st.subheader("📊 Delay Rate (%) by Airline and Departure Time Block")

    # User selects airlines for this chart only
    all_airlines = sorted(df["Airline"].dropna().unique())
    selected_airlines_chart = st.multiselect("✈️ Choose Airlines to Compare", all_airlines, default=all_airlines[:3])

    delay_rate_df = df.dropna(subset=["DepDel15", "DepTimeBlk", "Airline"])
    delay_rate_df = delay_rate_df[delay_rate_df["Airline"].isin(selected_airlines_chart)]

    if not delay_rate_df.empty:
        delay_group = delay_rate_df.groupby(["Airline", "DepTimeBlk"])["DepDel15"].mean().reset_index()
        delay_group["DepDel15"] *= 100  # Convert to %
        pivot = delay_group.pivot(index="DepTimeBlk", columns="Airline", values="DepDel15").fillna(0)

        fig3, ax3 = plt.subplots(figsize=(12, 6))
        pivot.plot(kind="bar", ax=ax3)
        ax3.set_title("Delay Rate (%) by Airline and Departure Time Block")
        ax3.set_ylabel("Delay Rate (%)")
        ax3.set_xlabel("Departure Time Block")
        ax3.legend(title="Airline", bbox_to_anchor=(1.05, 1), loc='upper left')
        st.pyplot(fig3)
    else:
        st.warning("No data available for the selected airlines.")

# 4. Average Delay by Origin and Day of Week
if "Origin" in df.columns and "DayOfWeek" in df.columns and "DepDelayMinutes" in df.columns:
    st.subheader("📍 Average Delay by Origin Airport and Day of Week")

    # User selects top N airports to compare
    origin_counts = df["Origin"].value_counts()
    top_origins = st.multiselect("🛫 Choose Origin Airports", origin_counts.index[:5].tolist(), default=origin_counts.index[:3].tolist())

    delay_origin_df = df[df["Origin"].isin(top_origins)]
    avg_delay = delay_origin_df.groupby(["Origin", "DayOfWeek"])["DepDelayMinutes"].mean().reset_index()
    pivot_origin = avg_delay.pivot(index="DayOfWeek", columns="Origin", values="DepDelayMinutes").fillna(0)

    fig4, ax4 = plt.subplots(figsize=(10, 6))
    pivot_origin.plot(kind="bar", ax=ax4)
    ax4.set_title("Average Departure Delay by Origin Airport and Day of Week")
    ax4.set_xlabel("Day of Week (1=Mon ... 7=Sun)")
    ax4.set_ylabel("Average Delay (minutes)")
    ax4.legend(title="Origin", bbox_to_anchor=(1.05, 1), loc='upper left')
    st.pyplot(fig4)

# 5. Scatter Plot: Distance vs Departure Delay by Airline
if "Distance" in df.columns and "DepDelayMinutes" in df.columns and "Airline" in df.columns:
    st.subheader("📈 Distance vs. Departure Delay by Airline")

    selected_airlines_scatter = st.multiselect("✈️ Select Airlines for Scatter Plot", sorted(df["Airline"].dropna().unique()), default=sorted(df["Airline"].dropna().unique())[:2])

    scatter_df = df[
        df["Airline"].isin(selected_airlines_scatter) &
        df["Distance"].notnull() & df["DepDelayMinutes"].notnull()
    ]

    fig5, ax5 = plt.subplots(figsize=(10, 6))
    for airline in selected_airlines_scatter:
        airline_data = scatter_df[scatter_df["Airline"] == airline]
        ax5.scatter(airline_data["Distance"], airline_data["DepDelayMinutes"], alpha=0.4, label=airline)

    ax5.set_xlabel("Distance (miles)")
    ax5.set_ylabel("Departure Delay (minutes)")
    ax5.set_title("Distance vs Departure Delay by Airline")
    ax5.legend(title="Airline")
    st.pyplot(fig5)

