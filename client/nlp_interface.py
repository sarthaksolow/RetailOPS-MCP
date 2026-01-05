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

sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import RetailOpsClient

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
1. category: The product category (tv, laptop, phone, electronics, kitchen_appliances, fashion, groceries, smartphones)
2. intent: What they want to know (pricing, forecast, inventory, full_analysis, catalog_enrichment, find_alternatives)
3. context: Any specific context like events (diwali, christmas), time periods, product names, etc.

Respond ONLY with a JSON object. No markdown, no explanation, just pure JSON.

Examples:
User: "What discount should I give on TVs for Diwali?"
Response: {"category": "tv", "intent": "pricing", "context": {"event": "diwali", "action": "discount"}}

User: "How many laptops will I sell next month?"
Response: {"category": "laptop", "intent": "forecast", "context": {"period": "next_month"}}

User: "Should I reorder phones?"
Response: {"category": "phone", "intent": "inventory", "context": {}}

User: "Analyze electronics category"
Response: {"category": "electronics", "intent": "full_analysis", "context": {}}

User: "We're out of 2kg Ariel packs — what should I do?"
Response: {"category": "groceries", "intent": "find_alternatives", "context": {"product_name": "Ariel 2kg packs", "stockout": true}}

User: "Enrich product data for Samsung TV"
Response: {"category": "electronics", "intent": "catalog_enrichment", "context": {"product_name": "Samsung TV"}}
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
- Keep it concise (3-5 sentences for simple queries, more for complex)
- Use Indian Rupee (₹) for prices
"""
        
        user_prompt = f"""User asked: "{user_query}"

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
            return "Sorry, I couldn't generate a proper answer. But here's the raw data I found."
    
    async def ask(self, user_query: str) -> str:
        """Main method: Ask a question in natural language and get an answer"""
        
        print(f"\n{'='*70}")
        print(f"💬 You: {user_query}")
        print(f"{'='*70}\n")
        
        # Step 1: Understand the query
        print("🤔 Understanding your question...")
        understanding = await self.understand_query(user_query)
        
        if not understanding or 'category' not in understanding:
            return "❌ I couldn't understand your question. Could you rephrase it? Please mention a product category like TV, laptop, phone, etc."
        
        category = understanding['category']
        intent = understanding.get('intent', 'full_analysis')
        context = understanding.get('context', {})
        
        print(f"✅ Got it! Category: {category}, Intent: {intent}")
        
        # Step 2: Get data from servers
        print(f"📊 Analyzing {category} data...\n")
        
        if intent == 'forecast':
            data = await self.client.run_forecast_only(category)
        elif intent in ['catalog_enrichment', 'find_alternatives']:
            product_name = context.get('product_name', understanding.get('category', ''))
            product_data = context.get('product_data', {})
            data = await self.client.enrich_product(product_name, product_data)
        elif intent in ['pricing', 'inventory', 'full_analysis']:
            data = await self.client.run_full_workflow(category)
        else:
            data = await self.client.run_full_workflow(category)
        
        # Step 3: Generate conversational answer
        print("💭 Generating answer...\n")
        answer = await self.generate_answer(user_query, understanding, data)
        
        # Step 4: Add data summary
        full_response = f"""{'='*70}
🤖 RetailOps AI Assistant
{'='*70}

{answer}

"""
        
        # Add relevant data points
        if data.get('status') == 'completed':
            full_response += f"""
📊 Key Metrics:
"""
            if 'forecast' in data:
                full_response += f"   • Forecasted Demand: {data['forecast']['final']:.0f} units\n"
                full_response += f"   • Event: {data['forecast']['event']}\n"
            
            if 'replenishment' in data:
                full_response += f"   • Reorder: {data['replenishment']['reorder_qty']} units ({data['replenishment']['timing']})\n"
                full_response += f"   • Stock Risk: {data['replenishment']['stockout_risk']}\n"
            
            if 'pricing' in data:
                full_response += f"   • Current Price: ₹{data['pricing']['current_price']:,.0f}\n"
                full_response += f"   • Recommended: ₹{data['pricing']['recommended_price']:,.0f} ({data['pricing']['change_pct']:+.1f}%)\n"
        
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
        print('  • "Should I reorder laptops?"')
        print('  • "Analyze electronics category"')
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
