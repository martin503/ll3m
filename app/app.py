import requests as rs
import streamlit as st

st.title("Chat with Champ")


# Function to get API response
def get_api_response(question):
    url = "http://api:8086/chat/"
    params = {"question": question}
    response = rs.post(url, json=params)
    return response.json()


# Initialize conversation history
if "conversation" not in st.session_state:
    st.session_state.conversation = []


# Function to process the query
def process_query():
    if st.session_state.user_question:
        try:
            response = get_api_response(st.session_state.user_question)
            st.write("Champ's Answer:")
            st.write(response["answer"])

            # Add to conversation history
            st.session_state.conversation.insert(0, ("Champ", response["answer"]))
            st.session_state.conversation.insert(0, ("You", st.session_state.user_question))

            # Clear the input area
            st.session_state.user_question = ""
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.warning("Please enter a question.")


# Text area for user's question
st.text_area("Ask a question to the Champ model:", key="user_question", on_change=process_query)

# Display conversation history
st.subheader("Conversation History:")
for role, text in st.session_state.conversation:
    st.write(f"**{role}:** {text}")
