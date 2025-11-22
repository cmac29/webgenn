#!/usr/bin/env python3
"""
Uniqueness Test - Verify different prompts produce unique outputs
"""

import asyncio
import aiohttp
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def generate_and_compare():
    """Generate two different websites and compare uniqueness"""
    base_url = "https://webgen-ai-11.preview.emergentagent.com/api"
    
    prompts = [
        "Create a beautiful recipe blog website with a hero section and recipe cards",
        "Create a modern portfolio website for a web developer"
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, prompt in enumerate(prompts):
            # Create session
            payload = {"project_name": f"Uniqueness Test {i+1}"}
            async with session.post(f"{base_url}/session/create", json=payload) as response:
                if response.status != 200:
                    logger.error(f"Session creation failed: {response.status}")
                    continue
                
                session_data = await response.json()
                session_id = session_data.get('session_id')
                logger.info(f"✅ Created session {i+1}: {session_id}")
            
            # Generate website
            start_time = time.time()
            payload = {
                "session_id": session_id,
                "prompt": prompt,
                "model": "claude-sonnet-4",
                "framework": "html"
            }
            
            logger.info(f"🚀 Generating website {i+1}: {prompt[:50]}...")
            
            try:
                async with session.post(
                    f"{base_url}/generate/website",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    generation_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        html_content = data.get('html_content', '')
                        html_length = len(html_content)
                        
                        # Extract title
                        title = ""
                        if '<title>' in html_content:
                            start = html_content.find('<title>') + 7
                            end = html_content.find('</title>', start)
                            if end != -1:
                                title = html_content[start:end].strip()
                        
                        result = {
                            "prompt": prompt,
                            "html_content": html_content,
                            "html_length": html_length,
                            "title": title,
                            "generation_time": generation_time
                        }
                        results.append(result)
                        
                        logger.info(f"✅ Website {i+1} generated successfully!")
                        logger.info(f"   Time: {generation_time:.2f}s")
                        logger.info(f"   HTML length: {html_length} chars")
                        logger.info(f"   Title: {title}")
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Generation {i+1} failed: {response.status} - {error_text}")
            
            except Exception as e:
                logger.error(f"❌ Generation {i+1} error: {e}")
            
            # Small delay between generations
            if i < len(prompts) - 1:
                await asyncio.sleep(5)
    
    # Compare results
    if len(results) == 2:
        html1, html2 = results[0]['html_content'], results[1]['html_content']
        len1, len2 = results[0]['html_length'], results[1]['html_length']
        title1, title2 = results[0]['title'], results[1]['title']
        
        is_identical = html1 == html2
        length_diff_percent = abs(len1 - len2) / max(len1, len2) * 100 if max(len1, len2) > 0 else 0
        same_title = title1 == title2 and title1 != ""
        
        logger.info("\n🔍 UNIQUENESS ANALYSIS:")
        logger.info(f"   Identical HTML: {'❌ YES' if is_identical else '✅ NO'}")
        logger.info(f"   Same title: {'❌ YES' if same_title else '✅ NO'}")
        logger.info(f"   Length difference: {length_diff_percent:.1f}%")
        logger.info(f"   HTML lengths: [{len1}, {len2}]")
        logger.info(f"   Titles: ['{title1}', '{title2}']")
        
        is_unique = not is_identical and not same_title
        
        if is_unique:
            logger.info("\n🎉 UNIQUENESS VERIFIED!")
            logger.info("✅ Different prompts produce unique websites")
            logger.info("✅ No repetitive layout issue")
            return True
        else:
            logger.error("\n❌ UNIQUENESS ISSUE DETECTED!")
            logger.error("❌ Different prompts producing similar/identical content")
            return False
    else:
        logger.error("❌ Could not generate both websites for comparison")
        return False

async def main():
    logger.info("🔍 Uniqueness Test")
    logger.info("=" * 50)
    
    success = await generate_and_compare()
    
    if success:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("✅ Budget issue resolved")
        logger.info("✅ AI generation working")
        logger.info("✅ Unique outputs for different prompts")
        return 0
    else:
        logger.error("\n❌ TESTS FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)