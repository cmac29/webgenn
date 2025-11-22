#!/usr/bin/env python3
"""
Budget Test - Verify AI website generation with new Emergent LLM key
Tests the specific scenarios requested in the review
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BudgetTester:
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
    
    async def create_session(self, project_name: str = "Budget Test") -> str:
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
    
    async def generate_website_test(self, session_id: str, prompt: str, test_name: str) -> Dict[str, Any]:
        """Generate a website and return detailed test results"""
        async with aiohttp.ClientSession() as session:
            try:
                start_time = time.time()
                
                payload = {
                    "session_id": session_id,
                    "prompt": prompt,
                    "model": "claude-sonnet-4",  # Specific model requested
                    "framework": "html",
                    "conversation_history": []
                }
                
                logger.info(f"🚀 {test_name}: Generating website...")
                logger.info(f"   Prompt: '{prompt}'")
                logger.info(f"   Model: claude-sonnet-4")
                
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
                        
                        # Validation checks
                        has_embedded_styles = '<style>' in html_content
                        html_length = len(html_content)
                        generation_time_ok = generation_time > 5  # Should be > 5 seconds for real AI
                        html_length_ok = html_length > 2000  # Should be > 2000 chars
                        
                        result = {
                            "test_name": test_name,
                            "success": True,
                            "prompt": prompt,
                            "generation_time": generation_time,
                            "html_length": html_length,
                            "has_embedded_styles": has_embedded_styles,
                            "html_content": html_content,
                            "validation": {
                                "generation_time_ok": generation_time_ok,
                                "html_length_ok": html_length_ok,
                                "has_styles": has_embedded_styles,
                                "no_budget_error": True  # If we got here, no budget error
                            }
                        }
                        
                        logger.info(f"✅ {test_name} completed successfully!")
                        logger.info(f"   Generation time: {generation_time:.2f}s ({'✅' if generation_time_ok else '❌'} >5s)")
                        logger.info(f"   HTML length: {html_length} chars ({'✅' if html_length_ok else '❌'} >2000)")
                        logger.info(f"   Embedded styles: {'✅' if has_embedded_styles else '❌'}")
                        
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ {test_name} failed: {response.status} - {error_text}")
                        
                        # Check if it's a budget error
                        is_budget_error = "budget" in error_text.lower() or "exceeded" in error_text.lower()
                        
                        return {
                            "test_name": test_name,
                            "success": False,
                            "prompt": prompt,
                            "generation_time": generation_time,
                            "error": f"HTTP {response.status}: {error_text}",
                            "is_budget_error": is_budget_error,
                            "validation": {
                                "no_budget_error": not is_budget_error
                            }
                        }
                        
            except asyncio.TimeoutError:
                logger.error(f"❌ {test_name} timed out after 5 minutes")
                return {
                    "test_name": test_name,
                    "success": False,
                    "prompt": prompt,
                    "error": "Generation timed out",
                    "validation": {"no_budget_error": True}  # Timeout is not budget error
                }
            except Exception as e:
                logger.error(f"❌ {test_name} error: {e}")
                return {
                    "test_name": test_name,
                    "success": False,
                    "prompt": prompt,
                    "error": str(e),
                    "validation": {"no_budget_error": "budget" not in str(e).lower()}
                }
    
    def analyze_uniqueness(self, result1: Dict, result2: Dict) -> Dict[str, Any]:
        """Analyze if the two generated websites are unique"""
        if not (result1.get('success') and result2.get('success')):
            return {"error": "Both tests must succeed to compare uniqueness"}
        
        html1 = result1.get('html_content', '')
        html2 = result2.get('html_content', '')
        
        # Check if HTML is identical
        is_identical = html1 == html2
        
        # Check if HTML is very similar (same length within 5%)
        len1, len2 = len(html1), len(html2)
        length_diff_percent = abs(len1 - len2) / max(len1, len2) * 100 if max(len1, len2) > 0 else 0
        is_very_similar = length_diff_percent < 5 and len1 > 1000 and len2 > 1000
        
        # Extract titles for comparison
        title1 = self._extract_title(html1)
        title2 = self._extract_title(html2)
        same_title = title1 == title2 and title1 != ""
        
        is_unique = not is_identical and not (is_very_similar and same_title)
        
        return {
            "is_unique": is_unique,
            "is_identical": is_identical,
            "is_very_similar": is_very_similar,
            "same_title": same_title,
            "length_diff_percent": length_diff_percent,
            "html_lengths": [len1, len2],
            "titles": [title1, title2]
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
    
    async def run_budget_tests(self):
        """Run the specific budget tests requested"""
        logger.info("🚀 Starting Budget Resolution Tests")
        logger.info(f"Backend URL: {self.base_url}")
        logger.info("="*80)
        
        start_time = time.time()
        
        # Test 1: Recipe Blog
        logger.info("\n📝 TEST 1: RECIPE BLOG")
        logger.info("-" * 40)
        session1 = await self.create_session("Recipe Blog Test")
        if not session1:
            logger.error("❌ Failed to create session for Recipe Blog test")
            return {"error": "Session creation failed"}
        
        result1 = await self.generate_website_test(
            session1,
            "Create a beautiful recipe blog website with a hero section and recipe cards",
            "Recipe Blog"
        )
        self.test_results.append(result1)
        
        # Small delay between tests
        await asyncio.sleep(3)
        
        # Test 2: Portfolio Website
        logger.info("\n💼 TEST 2: PORTFOLIO WEBSITE")
        logger.info("-" * 40)
        session2 = await self.create_session("Portfolio Test")
        if not session2:
            logger.error("❌ Failed to create session for Portfolio test")
            return {"error": "Session creation failed"}
        
        result2 = await self.generate_website_test(
            session2,
            "Create a modern portfolio website for a web developer",
            "Portfolio Website"
        )
        self.test_results.append(result2)
        
        total_time = time.time() - start_time
        
        # Analyze uniqueness
        uniqueness = self.analyze_uniqueness(result1, result2)
        
        # Check backend logs for AI generation success
        await self.check_backend_logs()
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("🎯 BUDGET TEST RESULTS SUMMARY")
        logger.info("="*80)
        
        success_count = sum(1 for r in self.test_results if r.get('success'))
        
        logger.info(f"Total Tests: 2")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {2 - success_count}")
        logger.info(f"Total Time: {total_time:.2f}s")
        
        # Detailed validation
        logger.info("\n📊 VALIDATION RESULTS:")
        
        for result in self.test_results:
            test_name = result.get('test_name', 'Unknown')
            if result.get('success'):
                validation = result.get('validation', {})
                logger.info(f"\n✅ {test_name}:")
                logger.info(f"   ⏱️  Generation time: {result.get('generation_time', 0):.2f}s ({'✅' if validation.get('generation_time_ok') else '❌'} >5s required)")
                logger.info(f"   📏 HTML length: {result.get('html_length', 0)} chars ({'✅' if validation.get('html_length_ok') else '❌'} >2000 required)")
                logger.info(f"   🎨 Embedded styles: {'✅' if validation.get('has_styles') else '❌'}")
                logger.info(f"   💰 No budget error: {'✅' if validation.get('no_budget_error') else '❌'}")
            else:
                logger.info(f"\n❌ {test_name}:")
                logger.info(f"   Error: {result.get('error', 'Unknown error')}")
                logger.info(f"   💰 Budget error: {'❌ YES' if result.get('is_budget_error') else '✅ NO'}")
        
        # Uniqueness analysis
        if not uniqueness.get('error'):
            logger.info(f"\n🔍 UNIQUENESS ANALYSIS:")
            logger.info(f"   Unique content: {'✅' if uniqueness.get('is_unique') else '❌'}")
            logger.info(f"   Identical HTML: {'❌' if uniqueness.get('is_identical') else '✅'}")
            logger.info(f"   Length difference: {uniqueness.get('length_diff_percent', 0):.1f}%")
            logger.info(f"   HTML lengths: {uniqueness.get('html_lengths', [])}")
            logger.info(f"   Titles: {uniqueness.get('titles', [])}")
        else:
            logger.info(f"\n🔍 UNIQUENESS ANALYSIS: {uniqueness.get('error')}")
        
        # Overall assessment
        all_passed = (
            success_count == 2 and
            all(r.get('validation', {}).get('generation_time_ok', False) for r in self.test_results if r.get('success')) and
            all(r.get('validation', {}).get('html_length_ok', False) for r in self.test_results if r.get('success')) and
            all(r.get('validation', {}).get('has_styles', False) for r in self.test_results if r.get('success')) and
            all(r.get('validation', {}).get('no_budget_error', False) for r in self.test_results) and
            uniqueness.get('is_unique', False)
        )
        
        logger.info(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        
        if all_passed:
            logger.info("🎉 Budget issue appears to be resolved! AI generation is working with unique outputs.")
        else:
            logger.info("⚠️  Issues still present. Check individual test results above.")
        
        return {
            "overall_success": all_passed,
            "test_results": self.test_results,
            "uniqueness_analysis": uniqueness,
            "total_time": total_time,
            "summary": {
                "total_tests": 2,
                "successful_tests": success_count,
                "failed_tests": 2 - success_count,
                "all_validations_passed": all_passed
            }
        }
    
    async def check_backend_logs(self):
        """Check backend logs for AI generation indicators"""
        try:
            import subprocess
            result = subprocess.run(
                ['tail', '-n', '50', '/var/log/supervisor/backend.err.log'],
                capture_output=True,
                text=True
            )
            
            logs = result.stdout
            
            # Look for key indicators
            budget_errors = logs.count("Budget has been exceeded")
            generation_success = logs.count("Generation successful")
            ai_processing = logs.count("Starting complete project generation")
            
            logger.info(f"\n📋 BACKEND LOGS ANALYSIS:")
            logger.info(f"   Budget errors found: {budget_errors}")
            logger.info(f"   Generation success messages: {generation_success}")
            logger.info(f"   AI processing started: {ai_processing}")
            
            # Show recent relevant log lines
            relevant_lines = []
            for line in logs.split('\n')[-20:]:
                if any(keyword in line.lower() for keyword in ['budget', 'generation', 'extraction', 'final output', 'success']):
                    relevant_lines.append(line.strip())
            
            if relevant_lines:
                logger.info(f"\n📝 RECENT RELEVANT LOG ENTRIES:")
                for line in relevant_lines[-5:]:  # Show last 5 relevant lines
                    logger.info(f"   {line}")
            
        except Exception as e:
            logger.error(f"Could not check backend logs: {e}")

async def main():
    """Main test runner"""
    tester = BudgetTester()
    results = await tester.run_budget_tests()
    
    # Return exit code based on results
    if results.get('overall_success'):
        logger.info("\n🎉 All budget tests passed! The new API key is working correctly.")
        return 0
    else:
        logger.error(f"\n💥 Budget tests failed. Check the detailed results above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)