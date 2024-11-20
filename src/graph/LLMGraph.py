from langgraph.graph import StateGraph, START
# from langchain_community.chat_models import ChatOllama
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from src.helper.StateGraph import State
from src.helper.BasicToolNode import BasicToolNode
from src.graph.tools.tools import TavilySearchResults
from typing import Literal
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from src.helper.CustomCallbacks import CustomAsyncCallbackHandler, CustomCallbackHandler
from src.agent.Supervisor import Supervisor

load_dotenv()
import datetime

supervisor_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful supervisor for your boss Micah Forster. "
            " Use discretion when delegating inquiries for specific tasks. "
            "Anybody that asks about something outside of your knowledge "
            "be sure to use the web scraping tool Tavily."
            "\n\nCurrent user:\n<User>\n{user_info}\n</User>"
            "\nCurrent time: {time}."
        ),
        ("placeholder", "{messages}")
    ]
).partial(time=datetime.datetime.now)

class LLMGraph:
    def __init__(self, llm_type="ollama"):
        self.llm_type = llm_type
        self._init_llm()
        self.memory = MemorySaver()
        self.tools = [TavilySearchResults(max_results=2)]
        self.graph = self._initialize_graph()

    def _init_llm(self):
        # self.llm = ChatOllama(
        #     model="mistral-nemo", 
        #     temperature=0,
        #     callbacks=[CustomCallbackHandler(), CustomAsyncCallbackHandler()],
        #     streaming=True
        #     )
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=4000,
            streaming=True,
            callbacks=[CustomCallbackHandler(), CustomAsyncCallbackHandler()]
        )
        
    def chatbot(self, state: State):
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    def handle_tool_error(self, state) -> dict:
        error = state.get("error")
        tool_calls = state["messages"][-1].tool_calls
        return {
            "messages": [
                ToolMessage(
                    content=f"Error: {repr(error)}\n please fix your mistakes.",
                    tool_call_id=tc["id"],
                )
                for tc in tool_calls
            ]
        }

    def create_tool_node_with_fallback(self, tools: list) -> dict:
        return ToolNode(tools).with_fallbacks(
            [RunnableLambda(self.handle_tool_error)], exception_key="error"
        )
    def route_tools(self,
        state: State,
    ) -> Literal["tools", "__end__"]:
        """
        Use in the conditional_edge to route to the ToolNode if the last message
        has tool calls. Otherwise, route to the end.
        """
        if isinstance(state, list):
            ai_message = state[-1]
        elif messages := state.get("messages", []):
            ai_message = messages[-1]
        else:
            raise ValueError(f"No messages found in input state to tool_edge: {state}")
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return "tools"
        return "__end__"

    def _initialize_graph(self):
        tools = [TavilySearchResults(max_results=2)]
        runnable = supervisor_prompt | self.llm.bind_tools(tools)
        graph_builder = StateGraph(State)

        graph_builder.add_node("supervisor", Supervisor(runnable))
        graph_builder.add_node("tools", self.create_tool_node_with_fallback(tools))
        graph_builder.add_edge(START, "supervisor")
        # The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "__end__" if
        # it is fine directly responding. This conditional routing defines the main agent loop.
        graph_builder.add_conditional_edges(
            "supervisor",
            tools_condition
        )
        graph_builder.add_edge("tools", "supervisor")
        graph = graph_builder.compile(
        checkpointer=self.memory
        )
        return graph

    