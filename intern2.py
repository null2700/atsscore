import streamlit as st
import speech_recognition as sr
from googlesearch import search
from pymongo import MongoClient
import datetime
import json
import webbrowser
from typing import List, Dict, Any

# Initialize MongoDB
try:
    mongo_client = MongoClient("mongodb://localhost:27017/")
    mongo_db = mongo_client["search_db"]
    transcripts_collection = mongo_db["voice_transcripts"]
    search_logs_collection = mongo_db["search_logs"]
except Exception as e:
    st.error(f"Error connecting to MongoDB: {e}")


def recognize_speech() -> str:
    """
    Captures audio from the microphone and returns the recognized text.
    Saves the transcript to MongoDB.
    """
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Please speak clearly.")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source)
            text = recognizer.recognize_google(audio)
            st.success(f"You said: {text}")
            # Save the transcript in MongoDB
            transcripts_collection.insert_one({
                "text": text,
                "timestamp": datetime.datetime.utcnow()
            })
            return text.lower()
        except sr.UnknownValueError:
            error_msg = "Sorry, I could not understand the audio."
            st.error(error_msg)
            return error_msg
        except sr.RequestError as e:
            error_msg = f"Could not request results; {e}"
            st.error(error_msg)
            return error_msg


def search_google(query: str) -> List[Dict[str, Any]]:
    """
    Searches Google for the given query and returns a list of results.
    Also logs the search query and results in MongoDB.
    """
    results = []
    try:
        for url in search(query, num_results=5):
            results.append({"title": url, "link": url})
        log_search(query, results)
    except Exception as e:
        st.error(f"An error occurred during the search: {e}")
    return results


def log_search(query: str, results: List[Dict[str, Any]]) -> None:
    """
    Logs the search query and results to MongoDB.
    """
    try:
        search_logs_collection.insert_one({
            "query": query,
            "results": json.dumps(results),
            "timestamp": datetime.datetime.utcnow()
        })
    except Exception as e:
        st.error(f"Error logging search: {e}")


def pdf_reader() -> None:
    """
    Allows the user to upload a PDF file (e.g., a resume) and logs the upload.
    """
    file = st.file_uploader(
        label="Upload your resume here. We will increase your ATS score", 
        type='pdf'
    )
    if file is not None:
        st.success(f"Uploaded file: {file.name}")
        try:
            search_logs_collection.insert_one({
                'filename': file.name,
                'uploaded_at': datetime.datetime.utcnow()
            })
        except Exception as e:
            st.error(f"Error logging file upload: {e}")


def main() -> None:
    """
    Main function to run the Streamlit app.
    """
    st.title("Voice Search and Resume ATS Optimizer")

    # Resume upload
    pdf_reader()

    # Start speech recognition when button is clicked
    if st.button('Start Speech Recognition'):
        field_of_interest = recognize_speech()

        if field_of_interest and "sorry" not in field_of_interest.lower():
            st.write(f"Searching for: {field_of_interest}")
            search_results = search_google(field_of_interest)

            if search_results:
                st.write("Search Results:")
                for idx, result in enumerate(search_results):
                    st.markdown(f"{idx + 1}. [{result['title']}]({result['link']})")

                # Select website to visit
                website_number = st.number_input(
                    "Select website number to visit", 
                    min_value=1, 
                    max_value=len(search_results), 
                    step=1,
                    key="website_number"
                )

                # Informational message about webbrowser usage in Streamlit
                if st.button("Open Selected Website"):
                    # Note: webbrowser.open() opens the link on the server,
                    # which might not reflect on the client's browser.
                    selected_link = search_results[website_number - 1]["link"]
                    st.info(f"Opening website: {selected_link}")
                    try:
                        webbrowser.open(selected_link)
                    except Exception as e:
                        st.error(f"Failed to open website: {e}")
            else:
                st.error("No search results found.")


if __name__ == "__main__":
    main()