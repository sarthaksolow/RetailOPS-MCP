"""
Natural Language Processing Interface for RetailOps Client
Uses LLM to understand queries and provide conversational answers
"""
import asyncio
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Add parent directory to path to find client modules
sys.path.insert(0, str(Path(__file__).parent))

# Robust import: Try importing from 'client' or 'orchestrator'
try:
    from client import RetailOpsClient
except ImportError:
    try:
        from orchestrator import RetailOpsClient
    except ImportError:
        print("❌ Error: Could not import RetailOpsClient. Ensure 'client.py' exists.")
        sys.exit(1)

load_dotenv()


class RetailOpsNLP:
    """NLP-powered interface for retail operations"""
    
    def __init__(self):
        self.client = RetailOpsClient()
        
        # Initialize OpenRouter client
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")
        
        self.llm = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "RetailOps NLP Interface"
            }
        )
        
        print("🤖 RetailOps NLP Interface initialized")
    
    async def understand_query(self, user_query: str) -> dict:
        """Use LLM to understand user intent and extract parameters"""
        
        system_prompt = """You are a retail operations assistant. Your job is to understand user queries and extract:
1. product_name: The specific product or category mentioned (e.g., "sony tv", "shoes", "iphone").
2. intent: What they want to know (pricing, forecast, inventory, full_analysis).
3. days_ahead: Number of days to look ahead (default 30).
4. context: Any specific context like events (Diwali, Christmas).

Respond ONLY with a JSON object. No markdown, no explanation.

Examples:
User: "What discount should I give on TVs for Diwali?"
Response: {"product_name": "tv", "intent": "pricing", "days_ahead": 30, "context": {"event": "diwali"}}

User: "How many laptops will I sell in the next 2 months?"
Response: {"product_name": "laptop", "intent": "forecast", "days_ahead": 60, "context": {}}

User: "Analyze electronics"
Response: {"product_name": "electronics", "intent": "full_analysis", "days_ahead": 30, "context": {}}
"""
        
        try:
            response = self.llm.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown if present
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            understanding = json.loads(result_text)
            return understanding
            
        except Exception as e:
            print(f"❌ Error understanding query: {e}")
            return None
    
    async def generate_answer(self, user_query: str, understanding: dict, data: dict) -> str:
        """Use LLM to generate a conversational answer"""
        
        system_prompt = """You are a friendly retail operations expert. Given user's question and retail data, provide a clear, actionable answer.

Guidelines:
- Be conversational and helpful
- Use emojis sparingly but appropriately
- Focus on actionable insights
- Mention specific numbers from the data
- Use Indian Rupee (₹) for prices
- If the forecast mentions an event (like Diwali), highlight it.
"""
        
        user_prompt = f"""User asked: "{user_query}"
User Intent Context: {json.dumps(understanding)}

Here's the retail data I gathered:
{json.dumps(data, indent=2)}

Please answer their question directly and conversationally."""
        
        try:
            response = self.llm.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            return answer
            
        except Exception as e:
            print(f"❌ Error generating answer: {e}")
            return "Sorry, I couldn't generate a proper answer. Please check the raw data below."
    
    async def ask(self, user_query: str) -> str:
        """Main method: Ask a question in natural language and get an answer"""
        
        print(f"\n{'='*70}")
        print(f"💬 You: {user_query}")
        print(f"{'='*70}\n")
        
        # Step 1: Understand the query
        print("🤔 Understanding your question...")
        understanding = await self.understand_query(user_query)
        
        if not understanding or 'product_name' not in understanding:
            return "❌ I couldn't understand the product you are asking about. Please mention a product like TV, laptop, etc."
        
        product_name = understanding['product_name']
        intent = understanding.get('intent', 'full_analysis')
        days_ahead = understanding.get('days_ahead', 30)
        
        print(f"✅ Got it! Product: '{product_name}', Intent: {intent}, Horizon: {days_ahead} days")
        
        # Step 2: Get data from servers
        # FIX: Always use run_full_workflow to ensure Enrichment happens first.
        # This maps products (e.g. "TV") to categories ("Electronics") needed for forecasting.
        print(f"📊 Running analysis for '{product_name}'...\n")
        
        data = await self.client.run_full_workflow(product_name, days_ahead=days_ahead)
        
        if data.get('status') == 'error':
            return f"❌ Workflow failed: {data.get('error')}"
        
        # Step 3: Generate conversational answer
        print("💭 Generating answer...\n")
        answer = await self.generate_answer(user_query, understanding, data)
        
        # Step 4: Add data summary
        full_response = f"""{'='*70}
🤖 RetailOps AI Assistant
{'='*70}

{answer}

"""
        
        # Add relevant data points summary
        if data.get('status') == 'completed':
            full_response += f"""
📊 Key Metrics for '{data.get('product_name')}':
"""
            # Enrichment Info
            if 'enrichment' in data and data['enrichment'].get('category'):
                full_response += f"   • Category: {data['enrichment']['category'].title()}\n"
                
            # Forecast Info
            if 'forecast' in data:
                full_response += f"   • Forecasted Demand: {data['forecast']['final']:.0f} units\n"
                if data['forecast'].get('event') and data['forecast']['event'] != "None":
                    full_response += f"   • Detected Event: {data['forecast']['event']}\n"
            
            # Replenishment Info
            if 'replenishment' in data:
                reorder = data['replenishment'].get('reorder_qty', 0)
                if reorder > 0:
                    full_response += f"   • 📦 Action: Reorder {reorder} units ({data['replenishment'].get('timing')})\n"
                else:
                    full_response += f"   • 📦 Action: No reorder needed yet\n"
            
            # Pricing Info
            if 'pricing' in data:
                price = data['pricing'].get('recommended_price', 0)
                change = data['pricing'].get('change_pct', 0)
                full_response += f"   • 🏷️  Pricing: ₹{price:,.0f} ({change:+.1f}%)\n"
        
        full_response += f"\n{'='*70}"
        
        return full_response
    
    async def chat(self):
        """Interactive chat mode"""
        print("\n" + "="*70)
        print("🤖 RetailOps AI Assistant - Chat Mode")
        print("="*70)
        print("\nAsk me anything about your retail operations!")
        print("Examples:")
        print('  • "What discount should I give on TVs for Diwali?"')
        print('  • "How many phones will I sell next month?"')
        print('  • "We are out of Ariel 2kg, what should I do?"')
        print("\nType 'exit' or 'quit' to leave.\n")
        
        while True:
            try:
                user_input = input("💬 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Goodbye! Happy selling!")
                    break
                
                if not user_input:
                    continue
                
                answer = await self.ask(user_input)
                print(answer)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


async def main():
    """CLI entry point"""
    
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        nlp = RetailOpsNLP()
        answer = await nlp.ask(query)
        print(answer)
    else:
        # Interactive chat mode
        nlp = RetailOpsNLP()
        await nlp.chat()


if __name__ == "__main__":
    asyncio.run(main())