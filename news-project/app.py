from flask import Flask, render_template, request
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
import sqlite3
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Database connection function
def get_db_connection():
    try:
        conn = sqlite3.connect('news_analysis.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.DatabaseError as e:
        print("Error connecting to the database:", e)
        return None

# Create a new SQLite database schema if it doesn't exist already
def create_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS news (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            text TEXT,
                            country TEXT,
                            sentiment TEXT,
                            keywords TEXT,
                            summary TEXT,
                            channel TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()

# Manually define Albanian stopwords
albanian_stopwords = [
    'dhe', 'po', 'jo', 'në', 'me', 'për', 'nga', 'at', 'janë', 'kur', 'dy', 'të', 'se',
    'ka', 'këtu', 'përpara', 'gjatë', 'që', 'do', 'si', 'është', 'apo', 'ndaj', 'i', 
    'e', 'ka', 'kjo', 'këto', 'atë', 'pas', 'ne', 'pa', 'së', 'nëse', 'duke', 'tani'
]

# List of countries in Albanian
countries_albanian = [
    "Shqipëri", "Kosovë", "Francë", "Gjermani", "Itali", "Greqi", "Turqi", "Britani",
    "Spanjë", "Serbi", "Maqedoni", "Kroaci", "Bosnjë", "Mal i Zi", "Austri", "Zvicër"
]

# Function to extract text from URL
def extract_text_from_url(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = ' '.join([para.get_text() for para in paragraphs])
        return text
    except requests.exceptions.RequestException as e:
        return f"Error fetching the URL: {e}"

# Function for sentiment analysis
def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0:
        return 'Positive'
    elif polarity < 0:
        return 'Negative'
    else:
        return 'Neutral'

# Function to detect country
def detect_country(text):
    for country in countries_albanian:
        if country.lower() in text.lower():
            return country
    return "Unknown Country"

# Function to extract keywords using TF-IDF
def extract_keywords(text):
    def clean_text(text):
        # Clean the text by removing special characters, numbers, etc.
        return re.sub(r'[^a-zA-ZëËçÇüÜ\s]', '', text).strip()

    text = clean_text(text)
    if len(text.split()) < 2:
        return "Insufficient data for keyword extraction."
    vectorizer = TfidfVectorizer(
        stop_words=albanian_stopwords,
        token_pattern=r'\b[a-zA-ZëËçÇüÜ]{2,}\b',
        max_features=10
    )
    try:
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        return ', '.join(sorted(feature_names))
    except ValueError as e:
        return "Error extracting keywords: " + str(e)

# Function for text summarization
def summarize_text(text):
    sentences = text.split('. ')
    if len(sentences) <= 3:
        return text
    important_sentences = sorted(sentences, key=lambda s: len(s.split()), reverse=True)[:3]
    return '. '.join(important_sentences) + '.'

# Function to generate a chart image for statistics
def generate_chart(data, title, xlabel, ylabel, chart_type="bar"):
    fig, ax = plt.subplots(figsize=(8, 5))
    if chart_type == "bar":
        data.plot(kind="bar", ax=ax)
    elif chart_type == "line":
        data.plot(kind="line", ax=ax)
    
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.tight_layout()

    # Save the chart as a base64 string
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{chart_url}"

# Route for home page
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        text = request.form.get('text_input') or extract_text_from_url(request.form.get('url_input'))
        channel = request.form.get('category')
        country = detect_country(text)
        sentiment = analyze_sentiment(text)
        keywords = extract_keywords(text)
        summary = summarize_text(text)

        conn = get_db_connection()
        if conn:
            try:
                conn.execute(
                    'INSERT INTO news (text, country, sentiment, keywords, summary, channel) VALUES (?, ?, ?, ?, ?, ?)',
                    (text, country, sentiment, keywords, summary, channel)
                )
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                print(f"Error inserting data into the database: {e}")

        return render_template('results.html', country=country, text=text, sentiment=sentiment, keywords=keywords, summary=summary, channel=channel)

    return render_template('home.html')

@app.route('/history')
def history():
    conn = get_db_connection()
    if conn:
        try:
            records = conn.execute('SELECT * FROM news ORDER BY created_at DESC').fetchall()
            conn.close()
            return render_template('history.html', records=records)
        except sqlite3.Error as e:
            print(f"Error fetching history data: {e}")
            return "Error fetching history data."
    return "Error connecting to the database."

@app.route('/statistics')
def statistics():
    conn = get_db_connection()
    if conn:
        try:
            # Fetch sentiment statistics grouped by month
            stats = conn.execute(''' 
                SELECT strftime('%Y-%m', created_at) AS month, sentiment, COUNT(*) AS count
                FROM news
                GROUP BY month, sentiment
                ORDER BY month ASC
            ''').fetchall()
            conn.close()

            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(stats, columns=['month', 'sentiment', 'count'])

            # Debugging: Print the DataFrame to check structure
            print("DataFrame before aggregation:")
            print(df)

            # Aggregate counts to eliminate duplicates
            df = df.groupby(['month', 'sentiment'], as_index=False).sum()

            # Debugging: Print the DataFrame after aggregation
            print("DataFrame after aggregation:")
            print(df)

            # Ensure the DataFrame is ready for pivoting
            if df.empty:
                return render_template('statistics.html', sentiment_chart=None)

            # Pivot the DataFrame
            sentiment_pivot = df.pivot(index='month', columns='sentiment', values='count').fillna(0)

            # Debugging: Print the pivoted DataFrame
            print("Pivoted DataFrame:")
            print(sentiment_pivot)

            # Generate the sentiment chart
            sentiment_chart = generate_chart(
                sentiment_pivot,
                title="Sentiments Over Time",
                xlabel="Month",
                ylabel="Count",
                chart_type="bar"
            )

            return render_template('statistics.html', sentiment_chart=sentiment_chart)

        except ValueError as e:
            print(f"Error during pivot: {e}")
            return "Error generating statistics chart."
        except sqlite3.Error as e:
            print(f"Error loading statistics: {e}")
            return "Error loading statistics."

    return "Error connecting to the database."

if __name__ == '__main__':
    create_database()
    app.run(debug=True)
