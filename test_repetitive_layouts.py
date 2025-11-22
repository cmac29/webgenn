#!/usr/bin/env python3
"""
Specific test for repetitive layouts issue
Tests the 3 specific prompts requested by the user
"""

import asyncio
import aiohttp
import json
import time
import logging
import subprocess
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RepetitiveLayoutTester:
    def __init__(self):
        # Get backend URL from frontend .env
        self.base_url = self._get_backend_url()
        self.test_results = []
        
    def _get_backend_url(self) -> str:
        """Get backend URL from frontend .env file"""
        try:
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        url = line.split('=', 1)[1].strip()
                        return f"{url}/api"
        except Exception as e:
            logger.error(f"Could not read frontend .env: {e}")
        
        # Fallback
        return "https://webgen-ai-11.preview.emergentagent.com/api"
    
    async def create_session(self, project_name: str = "Test Project") -> str:
        """Create a new session and return session_id"""
        async with aiohttp.ClientSession() as session:
            try:
                payload = {"project_name": project_name}
                async with session.post(
                    f"{self.base_url}/session/create",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        session_id = data.get('session_id')
                        logger.info(f"✅ Created session: {session_id}")
                        return session_id
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Session creation failed: {response.status} - {error_text}")
                        return None
            except Exception as e:
                logger.error(f"❌ Session creation error: {e}")
                return None
    
    async def generate_website(self, session_id: str, prompt: str) -> Dict[str, Any]:
        """Generate a website and return the result"""
        async with aiohttp.ClientSession() as session:
            try:
                start_time = time.time()
                
                payload = {
                    "session_id": session_id,
                    "prompt": prompt,
                    "model": "claude-sonnet-4",
                    "framework": "html",
                    "conversation_history": []
                }
                
                logger.info(f"🚀 Generating website with prompt: '{prompt}'")
                
                async with session.post(
                    f"{self.base_url}/generate/website",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                ) as response:
                    generation_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        html_content = data.get('html_content', '')
                        
                        result = {
                            "success": True,
                            "session_id": session_id,
                            "prompt": prompt,
                            "generation_time": generation_time,
                            "html_length": len(html_content),
                            "has_embedded_styles": '<style>' in html_content,
                            "html_content": html_content,
                            "website_id": data.get('website_id'),
                        }
                        
                        logger.info(f"✅ Website generated successfully in {generation_time:.2f}s")
                        logger.info(f"   HTML: {result['html_length']} chars")
                        logger.info(f"   Embedded styles: {result['has_embedded_styles']}")
                        
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Website generation failed: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "session_id": session_id,
                            "prompt": prompt,
                            "generation_time": generation_time,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
                        
            except asyncio.TimeoutError:
                logger.error(f"❌ Website generation timed out after 5 minutes")
                return {
                    "success": False,
                    "session_id": session_id,
                    "prompt": prompt,
                    "error": "Generation timed out"
                }
            except Exception as e:
                logger.error(f"❌ Website generation error: {e}")
                return {
                    "success": False,
                    "session_id": session_id,
                    "prompt": prompt,
                    "error": str(e)
                }
    
    def check_backend_logs(self) -> Dict[str, Any]:
        """Check backend logs for generation process indicators"""
        try:
            # Read supervisor backend logs
            result = subprocess.run(
                ['tail', '-n', '100', '/var/log/supervisor/backend.err.log'],
                capture_output=True,
                text=True
            )
            
            backend_logs = result.stdout
            
            # Look for key indicators
            ai_generation_success = "✅ Generation successful - using AI-generated code" in backend_logs
            fallback_used = "Using dynamic fallback" in backend_logs or "Fallback template applied" in backend_logs
            extraction_issues = "extraction failed" in backend_logs.lower()
            validation_issues = "validation" in backend_logs.lower()
            
            return {
                "ai_generation_success": ai_generation_success,
                "fallback_used": fallback_used,
                "extraction_issues": extraction_issues,
                "validation_issues": validation_issues,
                "logs_sample": backend_logs[-1000:] if backend_logs else "No logs found"
            }
        except Exception as e:
            logger.error(f"Could not check backend logs: {e}")
            return {
                "error": f"Could not check logs: {e}",
                "logs_sample": ""
            }
    
    def analyze_uniqueness(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze if generated HTML is unique across different prompts"""
        successful_results = [r for r in results if r.get('success') and r.get('html_content')]
        
        if len(successful_results) < 2:
            return {"error": "Need at least 2 successful generations to compare"}
        
        # Check for identical content
        identical_pairs = []
        similar_pairs = []
        
        for i in range(len(successful_results)):
            for j in range(i + 1, len(successful_results)):
                html1 = successful_results[i]['html_content']
                html2 = successful_results[j]['html_content']
                prompt1 = successful_results[i]['prompt']
                prompt2 = successful_results[j]['prompt']
                
                # Check if HTML is identical
                if html1 == html2:
                    identical_pairs.append((prompt1, prompt2))
                
                # Check for very similar content (same length within 5% and similar structure)
                len1, len2 = len(html1), len(html2)
                if len1 > 0 and len2 > 0:
                    length_similarity = abs(len1 - len2) / max(len1, len2)
                    if length_similarity < 0.05:  # Within 5% length
                        # Check for similar titles or structure
                        title1 = self._extract_title(html1)
                        title2 = self._extract_title(html2)
                        if title1 == title2 and title1 != "":
                            similar_pairs.append((prompt1, prompt2))
        
        return {
            "total_generations": len(successful_results),
            "identical_pairs": identical_pairs,
            "similar_pairs": similar_pairs,
            "is_unique": len(identical_pairs) == 0 and len(similar_pairs) == 0,
            "html_lengths": [len(r['html_content']) for r in successful_results],
            "prompts": [r['prompt'] for r in successful_results]
        }
    
    def _extract_title(self, html: str) -> str:
        """Extract title from HTML"""
        try:
            start = html.find('<title>')
            if start != -1:
                end = html.find('</title>', start)
                if end != -1:
                    return html[start + 7:end].strip()
        except:
            pass
        return ""
    
    async def test_specific_prompts(self):
        """Test the 3 specific prompts requested"""
        logger.info("\n" + "="*80)
        logger.info("TESTING REPETITIVE LAYOUTS FIX")
        logger.info("="*80)
        
        test_prompts = [
            "Create a YouTube clone with dark theme",
            "Create a recipe blog website", 
            "Create an e-commerce admin dashboard"
        ]
        
        results = []
        
        for i, prompt in enumerate(test_prompts, 1):
            logger.info(f"\n--- TEST {i}/3: {prompt} ---")
            
            # Create session
            session_id = await self.create_session(f"Test {i}: {prompt[:20]}")
            if not session_id:
                results.append({
                    "success": False,
                    "prompt": prompt,
                    "error": "Failed to create session"
                })
                continue
            
            # Generate website
            result = await self.generate_website(session_id, prompt)
            results.append(result)
            
            # Check logs after each generation
            log_analysis = self.check_backend_logs()
            result['log_analysis'] = log_analysis
            
            if result.get('success'):
                logger.info(f"✅ Test {i} completed successfully")
                logger.info(f"   HTML Length: {result['html_length']} chars")
                logger.info(f"   Generation Time: {result['generation_time']:.2f}s")
                logger.info(f"   AI Success in Logs: {log_analysis.get('ai_generation_success', False)}")
                logger.info(f"   Fallback Used: {log_analysis.get('fallback_used', False)}")
            else:
                logger.error(f"❌ Test {i} failed: {result.get('error')}")
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Analyze uniqueness
        uniqueness_analysis = self.analyze_uniqueness(results)
        
        # Final summary
        logger.info("\n" + "="*80)
        logger.info("FINAL RESULTS")
        logger.info("="*80)
        
        successful_tests = sum(1 for r in results if r.get('success'))
        logger.info(f"Successful generations: {successful_tests}/3")
        
        if successful_tests >= 2:
            logger.info(f"Uniqueness analysis:")
            logger.info(f"  - Identical pairs: {len(uniqueness_analysis.get('identical_pairs', []))}")
            logger.info(f"  - Similar pairs: {len(uniqueness_analysis.get('similar_pairs', []))}")
            logger.info(f"  - All unique: {uniqueness_analysis.get('is_unique', False)}")
            logger.info(f"  - HTML lengths: {uniqueness_analysis.get('html_lengths', [])}")
            
            if uniqueness_analysis.get('identical_pairs'):
                logger.error(f"❌ IDENTICAL CONTENT FOUND: {uniqueness_analysis['identical_pairs']}")
            elif uniqueness_analysis.get('similar_pairs'):
                logger.warning(f"⚠️ VERY SIMILAR CONTENT: {uniqueness_analysis['similar_pairs']}")
            else:
                logger.info("✅ ALL GENERATIONS ARE UNIQUE")
        
        # Check if AI generation is working
        ai_working = any(r.get('log_analysis', {}).get('ai_generation_success', False) for r in results)
        fallback_used = any(r.get('log_analysis', {}).get('fallback_used', False) for r in results)
        
        logger.info(f"AI Generation Working: {ai_working}")
        logger.info(f"Fallback Used: {fallback_used}")
        
        # Validation criteria from the request
        validation_results = []
        for i, result in enumerate(results, 1):
            if result.get('success'):
                html_length = result.get('html_length', 0)
                has_styles = result.get('has_embedded_styles', False)
                
                validation_results.append({
                    "test": i,
                    "prompt": result['prompt'],
                    "html_length_ok": html_length > 1000,
                    "has_embedded_styles": has_styles,
                    "generation_time": result.get('generation_time', 0),
                    "html_length": html_length
                })
        
        return {
            "results": results,
            "uniqueness_analysis": uniqueness_analysis,
            "validation_results": validation_results,
            "ai_working": ai_working,
            "fallback_used": fallback_used,
            "successful_tests": successful_tests
        }

async def main():
    """Main test runner"""
    tester = RepetitiveLayoutTester()
    results = await tester.test_specific_prompts()
    
    # Print final summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    successful = results['successful_tests']
    unique = results['uniqueness_analysis'].get('is_unique', False) if successful >= 2 else True
    ai_working = results['ai_working']
    
    print(f"✅ Successful generations: {successful}/3")
    print(f"✅ All unique layouts: {unique}")
    print(f"✅ AI generation working: {ai_working}")
    print(f"⚠️ Fallback used: {results['fallback_used']}")
    
    if successful == 3 and unique and ai_working:
        print("\n🎉 ALL TESTS PASSED - Repetitive layouts issue is FIXED!")
        return 0
    else:
        print("\n💥 SOME TESTS FAILED - Issue may still exist")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)