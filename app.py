import json
import streamlit as st
import time
import os
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from typing_extensions import override
from openai import AssistantEventHandler
import openai as client
import yfinance


if "openai_api_key" not in st.session_state:
    st.session_state["openai_api_key"] = ""


st.set_page_config(page_title="AssistantGPT", page_icon="⛑️")

st.title("AssistantGPT")

st.markdown(
    """
    AssistantGPT에 오신 것을 환영합니다.
    궁금한 회사의 주식 정보에 대해 무엇이든 물어보세요!
"""
)

assistant_id = "asst_UiN9twcE5DAC9uPglNceet0M"

query = st.chat_input("AssistantGPT에게 주식 정보를 물어보세요!")

with st.sidebar:
    openai_api_key = st.text_input("Enter OpenAI API Key", type="password")

    if st.button("Save API Key"):
        if openai_api_key:
            st.session_state["openai_api_key"] = openai_api_key
            os.environ["OPENAI_API_KEY"] = openai_api_key
            st.success("API Key saved successfully!")
        else:
            st.error("Please enter a valid API Key.")

api_key = os.getenv("OPENAI_API_KEY", st.session_state.get("openai_api_key", ""))
 
if api_key :
    client.api_key = api_key
    def get_ticker(inputs):
        ddg = DuckDuckGoSearchAPIWrapper(backend="html")
        company_name = inputs["company_name"]
        time.sleep(5)
        return ddg.run(f"Ticker symbol of {company_name}")


    def get_income_statement(inputs):
        ticker = inputs["ticker"]
        stock = yfinance.Ticker(ticker)
        return json.dumps(stock.income_stmt.to_json())


    def get_balance_sheet(inputs):
        ticker = inputs["ticker"]
        stock = yfinance.Ticker(ticker)
        return json.dumps(stock.balance_sheet.to_json())


    def get_daily_stock_performance(inputs):
        ticker = inputs["ticker"]
        stock = yfinance.Ticker(ticker)
        return json.dumps(stock.history(period="3mo").to_json())


    def send_message(thread_id, content):
        return client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
        )


    def get_run(run_id, thread_id):
        return client.beta.threads.runs.retrieve(run_id=run_id, thread_id=thread_id)


    def get_messages(thread_id):
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        messages = list(messages)
        messages.reverse()
        return messages


    def get_tool_outputs(run_id, thread_id):
        run = get_run(run_id, thread_id)
        outputs = []
        for action in run.required_action.submit_tool_outputs.tool_calls:
            action_id = action.id
            function = action.function
            print(f"Calling function: {function.name} with args {function.arguments}")
            outputs.append(
                {
                    "tool_call_id": action_id,
                    "output": functions_map[function.name](json.loads(function.arguments)),
                }
            )
        return outputs


    def submit_tool_outputs(run_id, thread_id):
        outputs = get_tool_outputs(run.id, thread.id)
        return client.beta.threads.runs.submit_tool_outputs(
            run_id=run_id, thread_id=thread_id, tool_outputs=outputs
        )


    def paint_message(message, role, save=True):
        with st.chat_message(role):
            st.markdown(message)
        if save:
            st.session_state["messages"].append({"message": message, "role": role})


    functions_map = {
        "get_ticker": get_ticker,
        "get_income_statement": get_income_statement,
        "get_balance_sheet": get_balance_sheet,
        "get_daily_stock_performance": get_daily_stock_performance,
    }

    functions = [
        {
            "type": "function",
            "function": {
                "name": "get_ticker",
                "description": "Given the name of a company returns its ticker symbol",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "The name of the company",
                        }
                    },
                    "required": ["company_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_income_statement",
                "description": "Given a ticker symbol (i.e AAPL) returns the company's income statement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "Ticker symbol of the company",
                        },
                    },
                    "required": ["ticker"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_balance_sheet",
                "description": "Given a ticker symbol (i.e AAPL) returns the company's balance sheet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "Ticker symbol of the company",
                        },
                    },
                    "required": ["ticker"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_daily_stock_performance",
                "description": "Given a ticker symbol (i.e AAPL) returns the performance of the stock for the last 100 days.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "Ticker symbol of the company",
                        },
                    },
                    "required": ["ticker"],
                },
            },
        },
    ]




    def paint_history():
        for message in st.session_state["messages"]:
            paint_message(
                message["message"].replace("$", "\$"), message["role"], save=False
            )


    if "messages" not in st.session_state:
        st.session_state["messages"] = []


    if query:
        paint_history()
        paint_message(query, "human")
        if "thread" not in st.session_state:
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": query,
                    }
                ]
            )
            st.session_state["thread"] = thread
        else:
            thread = st.session_state["thread"]
            send_message(thread.id, query)
        run = client.beta.threads.runs.create(
            thread_id=st.session_state["thread"].id,
            assistant_id=assistant_id,
        )
        with st.chat_message("ai"):
            with st.spinner("답변 생성 중.."):
                while get_run(run.id, thread.id).status in [
                    "queued",
                    "in_progress",
                    "requires_action",
                ]:
                    if get_run(run.id, thread.id).status == "requires_action":
                        submit_tool_outputs(run.id, thread.id)
                        time.sleep(0.5)
                    else:
                        time.sleep(0.5)
                message = (
                    get_messages(thread.id)[-1].content[0].text.value.replace("$", "\$")
                )
                st.session_state["messages"].append(
                    {
                        "message": message,
                        "role": "ai",
                    }
                )
                st.markdown(message)