from flask import Flask, render_template, request
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Custom Albanian stopwords list
albanian_stopwords = [
    "a", "as", "aty", "atyne", "atyneve", "atyneve", "bëhet", "bënë", "bëri", "bërë", 
    "bërë", "do", "duhet", "duhet", "e", "edhe", "ejani", "emri", "eni", "esa", "eshte", 
    "eshte", "eza", "ishte", "ishin", "ka", "kam", "kemi", "këtë", "kjo", "këtij", "këtij", 
    "kjo", "kështu", "kësaj", "ku", "kush", "lart", "ma", "me", "megjithatë", "mendimi", 
    "ndoshta", "ne", "në", "ndoshta", "nuk", "po", "po", "si", "së", "sipas", "të", "të", 
    "te", "të", "të", "të", "të", "të", "të", "të", "shumë", "se", "si", "duhet", "disa", 
    "për", "para", "prap", "sa", "së", "sapo", "të", "ai", "ata", "ata", "kjo", "të",
    "ndër", "mendoni"
]

# Function to remove stopwords
def remove_stopwords(text):
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in albanian_stopwords]
    return " ".join(filtered_words)

# Function to summarize text
def summarize_text(text):
    text = remove_stopwords(text)
    parser = PlaintextParser.from_string(text, None)  # `None` for default tokenizer
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, 3)  # Summarize into 3 sentences
    return " ".join(str(sentence) for sentence in summary)

# Function to fetch and summarize news from a URL
def summarize_from_url(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([para.get_text() for para in paragraphs])
        return summarize_text(text)
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        input_text = request.form.get('inputText')
        input_url = request.form.get('inputUrl')

        if input_text:
            summary = summarize_text(input_text)
            return render_template('results.html', summary=summary, input_text=input_text, input_url=None)

        if input_url:
            summary = summarize_from_url(input_url)
            return render_template('results.html', summary=summary, input_text=None, input_url=input_url)

    return render_template('home.html')

@app.route('/results', methods=['GET', 'POST'])
def results():
    return render_template('results.html')

if __name__ == '__main__':
    app.run(debug=True)
