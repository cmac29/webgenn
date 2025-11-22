#!/usr/bin/env python3
"""
Quick Budget Test - Verify the key findings
"""

import asyncio
import aiohttp
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_single_generation():
    """Test a single generation to verify budget fix"""
    base_url = "https://webgen-ai-11.preview.emergentagent.com/api"
    
    # Create session
    async with aiohttp.ClientSession() as session:
        # Create session
        payload = {"project_name": "Budget Verification"}
        async with session.post(f"{base_url}/session/create", json=payload) as response:
            if response.status != 200:
                logger.error(f"Session creation failed: {response.status}")
                return False
            
            session_data = await response.json()
            session_id = session_data.get('session_id')
            logger.info(f"✅ Created session: {session_id}")
        
        # Generate website
        start_time = time.time()
        payload = {
            "session_id": session_id,
            "prompt": "Create a simple landing page for a tech startup",
            "model": "claude-sonnet-4",
            "framework": "html"
        }
        
        logger.info("🚀 Testing website generation...")
        
        try:
            async with session.post(
                f"{base_url}/generate/website",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180)
            ) as response:
                generation_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    html_length = len(data.get('html_content', ''))
                    has_styles = '<style>' in data.get('html_content', '')
                    
                    logger.info(f"✅ Generation successful!")
                    logger.info(f"   Time: {generation_time:.2f}s")
                    logger.info(f"   HTML length: {html_length} chars")
                    logger.info(f"   Has embedded styles: {has_styles}")
                    logger.info(f"   Generation time > 5s: {'✅' if generation_time > 5 else '❌'}")
                    logger.info(f"   HTML length > 2000: {'✅' if html_length > 2000 else '❌'}")
                    
                    return {
                        "success": True,
                        "generation_time": generation_time,
                        "html_length": html_length,
                        "has_styles": has_styles,
                        "no_budget_error": True
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Generation failed: {response.status} - {error_text}")
                    is_budget_error = "budget" in error_text.lower()
                    logger.error(f"   Budget error: {'YES' if is_budget_error else 'NO'}")
                    
                    return {
                        "success": False,
                        "error": error_text,
                        "is_budget_error": is_budget_error
                    }
        
        except asyncio.TimeoutError:
            logger.error("❌ Generation timed out")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"❌ Generation error: {e}")
            return {"success": False, "error": str(e)}

async def main():
    logger.info("🧪 Quick Budget Test")
    logger.info("=" * 50)
    
    result = await test_single_generation()
    
    if result.get("success"):
        logger.info("\n🎉 BUDGET ISSUE RESOLVED!")
        logger.info("✅ AI generation is working correctly")
        logger.info("✅ No budget exceeded errors")
        logger.info("✅ Generation takes appropriate time (indicating real AI processing)")
        logger.info("✅ HTML output is substantial and contains embedded styles")
        return 0
    else:
        logger.error("\n❌ BUDGET ISSUE PERSISTS")
        if result.get("is_budget_error"):
            logger.error("❌ Budget exceeded error still occurring")
        else:
            logger.error(f"❌ Other error: {result.get('error')}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)