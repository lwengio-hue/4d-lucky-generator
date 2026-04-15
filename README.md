# 🎱 4D Lucky Number Generator

A fun, family-friendly Singapore Pools 4D number picker — statistical + lucky feel.  
Built for 清明节 reunions and weekly family chats. **Sharing is caring!** 🧧

---

## ✨ What It Does

- **Lucky Event Numbers** — enter car plates you witnessed, temple fortune sticks, dream numbers, receipt totals. The app derives related 4D picks from them
- **Pure Random** — completely uniform random picks
- **Statistically Weighted** — biased toward digits that have appeared more in history  
- **Hot Numbers** — numbers that appeared recently in the last 100 draws
- **Overdue Numbers** — numbers on the longest cold streak
- **Visual Analysis** — digit frequency charts, hot zone heatmaps

> ⚠️ Every 4D number has equal 1-in-10,000 odds. This app is for fun only and cannot predict winning numbers.

---

## 🚀 Run the App

### Option 1 — Streamlit Cloud (easiest, share a link)

1. Fork this repo on GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo → select `app.py`
4. Upload your `4d_results.db` in the app sidebar
5. Share the link with your family on Facebook / WhatsApp!

### Option 2 — Run locally on your MacBook

```bash
# Install dependencies
pip install -r requirements.txt

# Put your database in the data/ folder
mkdir -p data
cp /path/to/4d_results.db data/

# Run
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

## 📂 File Structure

```
4d_app/
├── app.py                    # Streamlit web app
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── 4D_Optimizer_v2.ipynb     # Jupyter notebook version
├── scrape_4d.py              # Singapore Pools 4D scraper
├── data/
│   └── 4d_results.db         # Scraped draw results (you provide this)
└── output/
    └── 4d_picks_YYYYMMDD.csv # Weekly picks history
```

---

## 🔄 Keeping Your Data Fresh

Run the scraper before each weekly session to get the latest draws:

```bash
python scrape_4d.py
```

The scraper automatically detects new draws and only fetches what's missing.  
4D draws happen on **Wednesday, Saturday, Sunday**.

---

## 📓 Jupyter Notebook Version

If you prefer working in Jupyter:

```bash
jupyter lab 4D_Optimizer_v2.ipynb
```

Edit `LUCKY_EVENTS` in Block 1, then **Kernel → Restart & Run All**.

---

## ⚠️ Responsible Gambling

4D is a game of chance. Set a budget and stick to it.  
**National Problem Gambling Helpline: 1800-6-668-668** (Singapore, 24/7)

---

*Built for family · 清明节 2026 · Sharing is caring 🍀*
