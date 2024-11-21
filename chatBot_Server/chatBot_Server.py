import requests
from bs4 import BeautifulSoup
import random
import string
import warnings
import nltk
from sentence_transformers import SentenceTransformer, util
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import json
import torch
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# Suppress warnings
warnings.filterwarnings("ignore")

# Download necessary NLTK resources
nltk.download('punkt')
nltk.download('wordnet')

# Initialize the Sentence Transformer model and lemmatizer
model = SentenceTransformer('all-MiniLM-L6-v2')
lemmer = nltk.stem.WordNetLemmatizer()

# Fetches all links on the main page belonging to the same domain
def get_all_links(url, domain):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()
        for link in soup.find_all('a', href=True):
            href = urljoin(url, link['href'])
            if domain in href:
                links.add(href)
        return list(links)
    except Exception as e:
        print(f"Error fetching links from {url}: {e}")
        return []

# Removes unnecessary whitespace and newline characters
def preprocess_text(text):
    text = text.replace('\n', ' ').strip()
    return ' '.join(text.split())

# Extracts text from a webpage
def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = " ".join([p.get_text() for p in soup.find_all('p')])
        text_content = preprocess_text(text_content)
        return text_content.lower()
    except Exception as e:
        print(f"Failed to retrieve {url}: {e}")
        return ""

# Fetches text from multiple pages concurrently
def fetch_all_text(urls):
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(extract_text_from_url, urls))
    return " ".join(results)

# Preprocess sentences for embeddings
def LemTokens(tokens):
    return [lemmer.lemmatize(token) for token in tokens]

remove_punct_dict = dict((ord(punct), None) for punct in string.punctuation)

def LemNormalize(text):
    return ' '.join(LemTokens(nltk.word_tokenize(text.lower().translate(remove_punct_dict))))

# Read JSON intents
def load_intents(file_path):
    with open(file_path, "r") as file:
        return json.load(file)

# Initialize URLs and fetch content
main_url = "https://www.adidas.co.in/"
domain = "adidas.co.in"
page_links = get_all_links(main_url, domain)

print("Fetching website content...")
all_text_content = fetch_all_text(page_links)

# Tokenize text into individual sentences
sent_tokens = nltk.sent_tokenize(preprocess_text(all_text_content))

# Generate embeddings in batches
batch_size = 32
embeddings = []
for i in range(0, len(sent_tokens), batch_size):
    batch = [LemNormalize(sentence) for sentence in sent_tokens[i:i + batch_size]]
    embeddings_batch = model.encode(batch, convert_to_tensor=True)
    embeddings.append(embeddings_batch)
embeddings = torch.cat(embeddings)
print("Embeddings generated.")

# Greeting inputs and responses
GREETING_INPUTS = ("hello", "hi", "hey")
GREETING_RESPONSES = ["How can I help you?", "What can I do for you?", "How can I assist you today?"]

def greeting(sentence):
    for word in sentence.split():
        if word.lower() in GREETING_INPUTS:
            return random.choice(GREETING_RESPONSES)

def split_query(query):
    return query.split('and')

# Function to match query with JSON intents
def match_intent(user_query, intents_data):
    for intent in intents_data['intents']:
        for pattern in intent['patterns']:
            if user_query.lower() in pattern.lower():
                return random.choice(intent['responses'])
    return None

# Logs interactions to a log file
# def log_interaction(user_query, bot_responses, log_file, unanswered_queries):
#     with open(log_file, "a") as log:
#         log.write(f"User Query: {user_query}\n")
#         log.write(f"Bot Response: {' '.join(bot_responses)}\n")
#         if unanswered_queries:
#             log.write(f"Unanswered Queries: {', '.join(unanswered_queries)}\n")
#         log.write("\n")

# Responds to user queries
def response(user_response, intents_file="MDSResponse.json", log_file="bot_responses.log", threshold=0.7):
    intents_data = load_intents(intents_file)
    print(intents_data)
    sub_queries = split_query(LemNormalize(user_response))
    bot_response = []
    unanswered_queries = []

    for sub_query in sub_queries:
        # Check for JSON intent match
        json_response = match_intent(sub_query, intents_data)
        if json_response:
            bot_response.append(json_response)
            continue

        # Handle website content-based response
        user_input_embedding = model.encode(sub_query, convert_to_tensor=True)
        similarities = util.pytorch_cos_sim(user_input_embedding, embeddings)[0]

        top_k = 2
        top_matches_indices = similarities.argsort(descending=True)[:top_k]
        best_matches_scores = similarities[top_matches_indices]

        response_candidates = []

        for idx, score in zip(top_matches_indices, best_matches_scores):
            matched_sentence = sent_tokens[idx]
            if score > threshold and matched_sentence not in response_candidates:
                response_candidates.append(matched_sentence)

        if response_candidates:
            response_candidates = sorted(set(response_candidates), key=lambda x: -similarities[sent_tokens.index(x)])
            bot_response.append(" ".join(sentence.capitalize() for sentence in response_candidates))
        else:
            bot_response.append("I'm sorry, I couldn't find any relevant information for your query.")
            unanswered_queries.append(user_response)

    # log_interaction(user_response, bot_response, log_file, unanswered_queries)

    # Save unanswered questions to a file named with today's date
    
    if unanswered_queries:
    # Get today's date
        today_date = datetime.now().strftime("%Y-%m-%d")
    
    # Ensure the folder exists
        response_folder = ""
        os.makedirs(response_folder, exist_ok=True)
    
    # Define the file path
        file_name = f"noResponse_{today_date}.txt"
        file_path = os.path.join(response_folder, file_name)
    
        # Write the queries to the file
        with open(file_path, "a") as file:
            for query in unanswered_queries:
                file.write(query + "\n")

    return " ".join(bot_response)
# Flask App
app = Flask(__name__)
CORS(app, resources={r"/chatBot": {"origins": "*"}})

@app.route("/chatBot", methods=["POST"])
def chatBot():
    user_input = request.json.get("message", "").lower()

    if user_input == "bye":
        return jsonify({"reply": "Goodbye"})

    if user_input in ["thanks", "thank you"]:
        return jsonify({"reply": "You're welcome"})

    if greeting(user_input):
        return jsonify({"reply": greeting(user_input)})

    bot_reply = response(user_input)
    return jsonify({"reply": bot_reply})

if __name__ == "__main__":
    app.run(debug=True)
