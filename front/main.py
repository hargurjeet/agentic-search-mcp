import streamlit as st
import httpx
import json
from typing import Dict, Any


# -----------------------------
# Session State Initialization
# -----------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []


class Chatbot:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.current_tool_call = {"name": None, "args": None}

    # -----------------------------
    # Message Rendering
    # -----------------------------
    def display_message(self, message: Dict[str, Any]):
        # User text message
        if message["role"] == "user" and isinstance(message["content"], str):
            st.chat_message("user").markdown(message["content"])

        # Tool result message
        if message["role"] == "user" and isinstance(message["content"], list):
            for content in message["content"]:
                if content.get("type") == "tool_result":
                    with st.chat_message("assistant"):
                        st.write(f"Called tool: {self.current_tool_call['name']}")
                        try:
                            st.json(
                                {
                                    "name": self.current_tool_call["name"],
                                    "args": self.current_tool_call["args"],
                                    "content": json.loads(
                                        content["content"][0]["text"]
                                    ),
                                },
                                expanded=False,
                            )
                        except Exception:
                            st.write(content)

        # Assistant text message
        if message["role"] == "assistant" and isinstance(message["content"], str):
            st.chat_message("assistant").markdown(message["content"])

        # Assistant tool call
        if message["role"] == "assistant" and isinstance(message["content"], list):
            for content in message["content"]:
                if content.get("type") == "tool_use":
                    self.current_tool_call = {
                        "name": content.get("name"),
                        "args": content.get("input"),
                    }

    # -----------------------------
    # API Calls (Sync)
    # -----------------------------
    def get_tools(self):
        with httpx.Client(timeout=30.0, verify=False) as client:
            response = client.get(
                f"{self.api_url}/tools",
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    def handle_query(self, query: str):
        with httpx.Client(timeout=60.0, verify=False) as client:
            response = client.post(
                f"{self.api_url}/query",
                json={"query": query},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            messages = response.json().get("messages", [])
            st.session_state["messages"] = messages

            for message in messages:
                self.display_message(message)

    # -----------------------------
    # Main UI
    # -----------------------------
    def render(self):
        st.title("MCP Client")

        # Sidebar
        with st.sidebar:
            st.subheader("Settings")
            st.write("API URL:")
            st.code(self.api_url)

            st.subheader("Tools")
            try:
                result = self.get_tools()
                tools = [tool["name"] for tool in result.get("tools", [])]
                st.write(tools)
            except Exception as e:
                st.error(f"Failed to load tools: {e}")

        # Display chat history
        for message in st.session_state["messages"]:
            self.display_message(message)

        # Chat input
        query = st.chat_input("Enter your query here")
        if query:
            try:
                self.handle_query(query)
            except Exception as e:
                st.error(f"Frontend error: {e}")


# -----------------------------
# App Entry Point (REQUIRED)
# -----------------------------
bot = Chatbot(api_url="http://localhost:8000")
bot.render()
