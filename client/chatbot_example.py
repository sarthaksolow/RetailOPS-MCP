"""
Example chatbot using Groq, LangGraph, and MCP tools

This example demonstrates how to build a conversational chatbot using:
- Groq for fast LLM inference
- LangGraph for managing conversation state and workflow
- MCP (Model Context Protocol) client/server for tool calling
"""

import asyncio
import json
import os
import sys
from typing import TypedDict, Annotated, Sequence, Literal
from pathlib import Path

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv

# Import MCP client utilities
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()


class ChatState(TypedDict):
    """State for the chatbot conversation with tool support"""
    messages: Annotated[Sequence[BaseMessage], add_messages]


@asynccontextmanager
async def mcp_session():
    """Context manager for MCP session with proper cleanup"""
    # Get the path to the server script
    server_path = Path(__file__).parent.parent / "servers" / "forecasting" / "server.py"
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        env={"OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", "")}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_mcp_forecast_tool_async(category: str, days_ahead: int = 30) -> str:
    """
    Call the getForecast MCP tool (async version)
    
    Args:
        category: Product category to forecast (e.g., "tv", "laptop", "phone")
        days_ahead: Number of days to forecast ahead (default: 30)
    
    Returns:
        JSON string containing forecast results
    """
    try:
        async with mcp_session() as session:
            response = await session.call_tool(
                "getForecast",
                {
                    "category": category,
                    "days_ahead": days_ahead
                }
            )
            
            # Parse response
            if hasattr(response, 'content') and response.content:
                for content in response.content:
                    if hasattr(content, 'text'):
                        try:
                            result = json.loads(content.text)
                            # Format the result nicely
                            formatted = json.dumps(result, indent=2)
                            return formatted
                        except json.JSONDecodeError:
                            return content.text
            
            return "No valid response from MCP server"
            
    except Exception as e:
        return f"Error calling MCP tool: {str(e)}"


def call_mcp_forecast_tool(category: str, days_ahead: int = 30) -> str:
    """
    Synchronous wrapper for calling the getForecast MCP tool
    
    Args:
        category: Product category to forecast (e.g., "tv", "laptop", "phone")
        days_ahead: Number of days to forecast ahead (default: 30)
    
    Returns:
        JSON string containing forecast results
    """
    # Run the async function in a new event loop if needed
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, we need to use a different approach
            # Create a task and wait for it
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(call_mcp_forecast_tool_async(category, days_ahead))
                )
                return future.result()
        else:
            return loop.run_until_complete(call_mcp_forecast_tool_async(category, days_ahead))
    except RuntimeError:
        # No event loop running, create a new one
        return asyncio.run(call_mcp_forecast_tool_async(category, days_ahead))


def create_mcp_tools():
    """Create LangChain tools from MCP server tools"""
    # Use the async function directly with coroutine parameter
    forecast_tool = StructuredTool.from_function(
        func=call_mcp_forecast_tool_async,
        name="getForecast",
        coroutine=call_mcp_forecast_tool_async,
        description="""Generate a sales forecast for a product category.
        
Use this tool when the user asks about:
- Sales forecasts or predictions for products
- Demand forecasting for specific categories
- Future sales projections

Parameters:
- category: The product category (e.g., "tv", "laptop", "phone", "tablet")
- days_ahead: Number of days to forecast ahead (default: 30)

Returns a detailed forecast including:
- Base forecast
- Seasonal multiplier
- Historical surge factor
- Final forecast
- Event information
- Narrative explanation
"""
    )
    
    return [forecast_tool]


def create_chatbot_graph_with_tools(model_name: str = "llama-3.1-8b-instant"):
    """
    Create a LangGraph workflow for the chatbot with MCP tool support
    
    Args:
        model_name: Groq model to use (default: llama-3.1-8b-instant)
    
    Returns:
        Compiled LangGraph workflow with tool calling support
    """
    # Initialize Groq LLM
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError(
            "GROQ_API_KEY not found in environment variables. "
            "Please set it in your .env file or environment."
        )
    
    # Create tools from MCP server
    tools = create_mcp_tools()
    
    # Create base LLM
    base_llm = ChatGroq(
        model=model_name,
        temperature=0.7,
        groq_api_key=groq_api_key,
    )
    
    # Bind tools to LLM - this ensures only our tools are available
    llm = base_llm.bind_tools(tools)
    
    # Create tool node for executing tool calls
    # ToolNode handles async tools automatically
    tool_node = ToolNode(tools)
    
    # Define the chatbot node (async)
    async def chatbot_node(state: ChatState) -> ChatState:
        """Process user message and generate response or tool calls"""
        messages = state["messages"]
        
        # Generate response using Groq (may include tool calls)
        # Use ainvoke for async support
        response = await llm.ainvoke(messages)
        
        # Return updated state with AI response
        return {"messages": [response]}
    
    # Define routing logic
    def should_continue(state: ChatState) -> Literal["tools", "end"]:
        """Determine if we should call tools or end"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If the last message has tool calls, route to tools
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        # Otherwise, end
        return "end"
    
    # Create the graph
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_node("tools", tool_node)
    
    # Define the flow
    workflow.set_entry_point("chatbot")
    
    # Add conditional edge: check if we need to call tools
    workflow.add_conditional_edges(
        "chatbot",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # After tools, go back to chatbot
    workflow.add_edge("tools", "chatbot")
    
    # Compile with memory for conversation history
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def create_simple_chatbot_graph(model_name: str = "llama-3.1-8b-instant"):
    """Create a simple chatbot graph without tools for general conversation"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables.")
    
    llm = ChatGroq(
        model=model_name,
        temperature=0.7,
        groq_api_key=groq_api_key,
    )
    
    async def chatbot_node(state: ChatState) -> ChatState:
        """Process user message and generate response"""
        messages = state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}
    
    workflow = StateGraph(ChatState)
    workflow.add_node("chatbot", chatbot_node)
    workflow.set_entry_point("chatbot")
    workflow.add_edge("chatbot", END)
    
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


async def simple_chatbot_example():
    """Example: Simple chatbot conversation without tools"""
    print("\n" + "="*60)
    print("Example 1: Simple Chatbot Conversation")
    print("="*60)
    
    # Create the simple chatbot graph (no tools)
    graph = create_simple_chatbot_graph()
    
    # Create a thread for this conversation
    config = {"configurable": {"thread_id": "example-1"}}
    
    # System message to set the chatbot's personality
    system_message = SystemMessage(
        content="You are a helpful and friendly AI assistant. "
                "Keep your responses concise and informative. "
                "You do not have access to any tools - just answer questions directly."
    )
    
    # Initialize conversation with system message
    initial_state = {"messages": [system_message]}
    await graph.ainvoke(initial_state, config)
    
    # Simulate a conversation
    user_messages = [
        "Hello! What can you help me with?",
        "Tell me a fun fact about space",
        "What's the capital of France?",
    ]
    
    for user_msg in user_messages:
        print(f"\n👤 User: {user_msg}")
        
        # Add user message and get response
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=user_msg)]},
            config
        )
        
        # Extract and print AI response
        ai_response = result["messages"][-1].content
        print(f"🤖 Assistant: {ai_response}")


async def mcp_tool_calling_example():
    """Example: Chatbot using MCP tools"""
    print("\n" + "="*60)
    print("Example 2: Chatbot with MCP Tool Calling")
    print("="*60)
    
    # Create the chatbot graph with tools
    graph = create_chatbot_graph_with_tools()
    
    # Create a thread for this conversation
    config = {"configurable": {"thread_id": "mcp-tool-example"}}
    
    # System message for retail assistant
    system_message = SystemMessage(
        content="""You are a retail operations assistant. You have access to ONE tool called 'getForecast' 
that can predict sales for different product categories. 

IMPORTANT: Only use the getForecast tool when users ask about sales forecasts or predictions. 
Do NOT try to use any other tools - you only have access to getForecast.

When users ask about sales forecasts or predictions, use the getForecast tool to get accurate data. 
Be helpful and explain the forecast results clearly."""
    )
    
    # Initialize conversation
    await graph.ainvoke({"messages": [system_message]}, config)
    
    # Example questions that should trigger tool calls
    questions = [
        "Can you get me a sales forecast for TVs?",
        "What's the forecast for laptops for the next 30 days?",
        "I need a forecast for phones",
    ]
    
    for question in questions:
        print(f"\n👤 User: {question}")
        
        # Invoke the graph
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=question)]},
            config
        )
        
        # Process the result to show tool calls
        messages = result["messages"]
        for msg in messages[-3:]:  # Show last few messages (may include tool calls)
            if isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    print(f"\n🔧 Tool Calls:")
                    for tool_call in msg.tool_calls:
                        print(f"   - {tool_call['name']}({tool_call['args']})")
                if msg.content:
                    print(f"\n🤖 Assistant: {msg.content}")
            elif isinstance(msg, ToolMessage):
                print(f"   ✅ Tool Result: {msg.content[:200]}...")  # Truncate long results
        
        # Get final response
        final_msg = messages[-1]
        if isinstance(final_msg, AIMessage) and final_msg.content:
            if not any(hasattr(m, 'tool_calls') and m.tool_calls for m in messages[-3:] if isinstance(m, AIMessage)):
                print(f"🤖 Assistant: {final_msg.content}")


async def interactive_chatbot_with_tools():
    """Example: Interactive chatbot with MCP tools"""
    print("\n" + "="*60)
    print("Example 3: Interactive Chatbot with MCP Tools")
    print("="*60)
    print("Type your messages (type 'quit' or 'exit' to end)")
    print("Try asking about sales forecasts for: tv, laptop, phone, tablet\n")
    
    # Create the chatbot graph with tools
    graph = create_chatbot_graph_with_tools()
    
    # Create a unique thread for this conversation
    config = {"configurable": {"thread_id": "interactive-tools"}}
    
    # System message
    system_message = SystemMessage(
        content="""You are a helpful retail operations assistant. You can help with:
- Sales forecasting for product categories (use getForecast tool)
- General retail questions
- Business analytics

IMPORTANT: You only have access to ONE tool: 'getForecast'. Do NOT try to use any other tools.

When users ask about forecasts, use the getForecast tool to get accurate predictions."""
    )
    
    # Initialize conversation
    await graph.ainvoke({"messages": [system_message]}, config)
    
    print("Chatbot initialized! Start chatting...\n")
    
    while True:
        try:
            # Get user input
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Get response from chatbot
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config
            )
            
            # Process and display response
            messages = result["messages"]
            for msg in messages[-2:]:  # Show last couple messages
                if isinstance(msg, AIMessage):
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        print(f"\n🔧 Calling tools: {[tc['name'] for tc in msg.tool_calls]}")
                    if msg.content:
                        print(f"🤖 Assistant: {msg.content}\n")
                elif isinstance(msg, ToolMessage):
                    # Tool result - usually just show that it completed
                    pass
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()


async def detailed_tool_call_example():
    """Example: Detailed demonstration of MCP tool calling"""
    print("\n" + "="*60)
    print("Example 4: Detailed MCP Tool Call Demonstration")
    print("="*60)
    
    # Create the chatbot graph with tools
    graph = create_chatbot_graph_with_tools()
    
    config = {"configurable": {"thread_id": "detailed-tool-demo"}}
    
    system_message = SystemMessage(
        content="""You are a retail forecasting expert. You have access to ONE tool: 'getForecast'.
When asked about forecasts, always use the getForecast tool to provide accurate data.
Do NOT try to use any other tools - you only have getForecast available."""
    )
    
    await graph.ainvoke({"messages": [system_message]}, config)
    
    question = "What's the sales forecast for TVs over the next 30 days? Please explain the results."
    print(f"\n👤 User: {question}\n")
    
    # Invoke and show step-by-step
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=question)]},
        config
    )
    
    # Show the full conversation flow
    print("📋 Conversation Flow:")
    print("-" * 60)
    for i, msg in enumerate(result["messages"][-5:], 1):  # Show last 5 messages
        if isinstance(msg, HumanMessage):
            print(f"{i}. 👤 User: {msg.content}")
        elif isinstance(msg, AIMessage):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"{i}. 🤖 Assistant: [Deciding to call tools]")
                for tc in msg.tool_calls:
                    print(f"   🔧 Tool: {tc['name']}")
                    print(f"      Args: category={tc['args'].get('category')}, "
                          f"days_ahead={tc['args'].get('days_ahead', 30)}")
            if msg.content:
                print(f"{i}. 🤖 Assistant: {msg.content}")
        elif isinstance(msg, ToolMessage):
            print(f"{i}. ✅ Tool Result: Forecast data received")
            # Parse and show key info
            try:
                tool_result = json.loads(msg.content)
                if isinstance(tool_result, dict):
                    print(f"      Category: {tool_result.get('category', 'N/A')}")
                    print(f"      Final Forecast: {tool_result.get('final_forecast', 'N/A')}")
            except:
                pass
    
    print("-" * 60)


async def main():
    """Run all chatbot examples"""
    print("🚀 Groq + LangGraph + MCP Chatbot Examples")
    print("="*60)
    
    # Check for API keys
    if not os.getenv("GROQ_API_KEY"):
        print("\n⚠️  Warning: GROQ_API_KEY not found!")
        print("Please set it in your .env file:")
        print("GROQ_API_KEY=your_groq_api_key_here\n")
        return
    
    try:
        # Run examples
        await simple_chatbot_example()
        await mcp_tool_calling_example()
        await detailed_tool_call_example()
        
        # Uncomment to run interactive example
        # await interactive_chatbot_with_tools()
        
        print("\n✅ All examples completed!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
