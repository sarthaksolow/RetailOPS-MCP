"""
Test script for Catalog Enricher MCP Server
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession


async def test_catalog_enricher():
    """Test the catalog enricher server"""
    server_path = Path(__file__).parent / "server.py"
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        env={}
    )
    
    print("🚀 Testing Catalog Enricher MCP Server")
    print("=" * 60)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test Case 1: Basic enrichment
            print("\n📊 Test Case 1: Basic Product Enrichment")
            print("-" * 60)
            test_input_1 = {
                "product_name": "Ariel 2kg Pack",
                "product_data": {}
            }
            
            response_1 = await session.call_tool(
                "enrichProduct",
                test_input_1
            )
            
            if hasattr(response_1, 'content') and response_1.content:
                for content in response_1.content:
                    if hasattr(content, 'text'):
                        result_1 = json.loads(content.text)
                        print(f"Product: {result_1.get('product_name')}")
                        print(f"Category: {result_1.get('category')}")
                        print(f"Brand: {result_1.get('brand')}")
                        print(f"Description: {result_1.get('description')}")
                        print(f"Alternatives: {len(result_1.get('alternatives', []))}")
                        print(f"\nNarrative: {result_1.get('narrative')}")
            
            # Test Case 2: Stockout alternative finding
            print("\n📊 Test Case 2: Finding Alternatives (Stockout Scenario)")
            print("-" * 60)
            test_input_2 = {
                "product_name": "Ariel 2kg Detergent Pack",
                "product_data": {
                    "category": "groceries"
                }
            }
            
            response_2 = await session.call_tool(
                "enrichProduct",
                test_input_2
            )
            
            if hasattr(response_2, 'content') and response_2.content:
                for content in response_2.content:
                    if hasattr(content, 'text'):
                        result_2 = json.loads(content.text)
                        print(f"Product: {result_2.get('product_name')}")
                        print(f"Category: {result_2.get('category')}")
                        print(f"\nAlternatives Found:")
                        for alt in result_2.get('alternatives', []):
                            print(f"  - {alt.get('name')} ({alt.get('brand')})")
                        print(f"\nNarrative: {result_2.get('narrative')}")
            
            # Test Case 3: Missing fields
            print("\n📊 Test Case 3: Filling Missing Fields")
            print("-" * 60)
            test_input_3 = {
                "product_name": "Samsung TV 55 inch",
                "product_data": {
                    "price": 45000
                }
            }
            
            response_3 = await session.call_tool(
                "enrichProduct",
                test_input_3
            )
            
            if hasattr(response_3, 'content') and response_3.content:
                for content in response_3.content:
                    if hasattr(content, 'text'):
                        result_3 = json.loads(content.text)
                        print(f"Product: {result_3.get('product_name')}")
                        print(f"Category: {result_3.get('category')}")
                        print(f"Brand: {result_3.get('brand')}")
                        print(f"Description: {result_3.get('description')}")
                        print(f"Missing fields filled: {', '.join(result_3.get('missing_fields', []))}")
            
            print("\n" + "=" * 60)
            print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_catalog_enricher())

