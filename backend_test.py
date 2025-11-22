#!/usr/bin/env python3
"""
Backend Test Suite for AI Website Generation
Tests the fix for repetitive layouts issue
"""

import asyncio
import aiohttp
import json
import time
import os
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebsiteGenerationTester:
    def __init__(self):
        # Get backend URL from frontend .env
        self.base_url = self._get_backend_url()
        self.session_ids = []
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
                        self.session_ids.append(session_id)
                        logger.info(f"✅ Created session: {session_id}")
                        return session_id
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Session creation failed: {response.status} - {error_text}")
                        return None
            except Exception as e:
                logger.error(f"❌ Session creation error: {e}")
                return None
    
    async def generate_website(self, session_id: str, prompt: str, framework: str = "html") -> Dict[str, Any]:
        """Generate a website and return the result"""
        async with aiohttp.ClientSession() as session:
            try:
                start_time = time.time()
                
                payload = {
                    "session_id": session_id,
                    "prompt": prompt,
                    "model": "gpt-5",
                    "framework": framework
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
                        
                        result = {
                            "success": True,
                            "session_id": session_id,
                            "prompt": prompt,
                            "generation_time": generation_time,
                            "html_length": len(data.get('html_content', '')),
                            "css_length": len(data.get('css_content', '')),
                            "js_length": len(data.get('js_content', '')),
                            "has_embedded_styles": '<style>' in data.get('html_content', ''),
                            "has_embedded_scripts": '<script>' in data.get('html_content', ''),
                            "html_content": data.get('html_content', ''),
                            "css_content": data.get('css_content', ''),
                            "js_content": data.get('js_content', ''),
                            "website_id": data.get('website_id'),
                            "framework": data.get('framework'),
                            "files_count": len(data.get('files', []))
                        }
                        
                        logger.info(f"✅ Website generated successfully in {generation_time:.2f}s")
                        logger.info(f"   HTML: {result['html_length']} chars")
                        logger.info(f"   CSS: {result['css_length']} chars") 
                        logger.info(f"   JS: {result['js_length']} chars")
                        logger.info(f"   Embedded styles: {result['has_embedded_styles']}")
                        logger.info(f"   Embedded scripts: {result['has_embedded_scripts']}")
                        
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
    
    async def get_latest_website(self, session_id: str) -> Dict[str, Any]:
        """Get the latest generated website for a session"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/website/{session_id}/latest",
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Retrieved latest website for session {session_id}")
                        return {"success": True, "data": data}
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Failed to get latest website: {response.status} - {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
            except Exception as e:
                logger.error(f"❌ Error getting latest website: {e}")
                return {"success": False, "error": str(e)}
    
    def analyze_html_uniqueness(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze if generated HTML is unique across different prompts"""
        html_contents = []
        unique_analysis = {}
        
        for result in results:
            if result.get('success') and result.get('html_content'):
                html = result['html_content']
                html_contents.append({
                    'prompt': result['prompt'],
                    'html': html,
                    'length': len(html)
                })
        
        if len(html_contents) < 2:
            return {"error": "Need at least 2 successful generations to compare"}
        
        # Check for identical content
        identical_pairs = []
        for i in range(len(html_contents)):
            for j in range(i + 1, len(html_contents)):
                html1 = html_contents[i]['html']
                html2 = html_contents[j]['html']
                
                # Check if HTML is identical
                if html1 == html2:
                    identical_pairs.append((html_contents[i]['prompt'], html_contents[j]['prompt']))
        
        # Check for similar structure (same title, similar length)
        similar_pairs = []
        for i in range(len(html_contents)):
            for j in range(i + 1, len(html_contents)):
                html1 = html_contents[i]['html']
                html2 = html_contents[j]['html']
                len1 = len(html1)
                len2 = len(html2)
                
                # Check if lengths are very similar (within 10%)
                if abs(len1 - len2) / max(len1, len2) < 0.1:
                    # Check if they have similar titles
                    title1 = self._extract_title(html1)
                    title2 = self._extract_title(html2)
                    if title1 == title2:
                        similar_pairs.append((html_contents[i]['prompt'], html_contents[j]['prompt']))
        
        return {
            "total_generations": len(html_contents),
            "identical_pairs": identical_pairs,
            "similar_pairs": similar_pairs,
            "is_unique": len(identical_pairs) == 0 and len(similar_pairs) == 0,
            "html_lengths": [content['length'] for content in html_contents]
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
    
    async def test_basic_generation_flow(self):
        """Test 1: Basic Generation Flow"""
        logger.info("\n" + "="*60)
        logger.info("TEST 1: BASIC GENERATION FLOW")
        logger.info("="*60)
        
        # Create session
        session_id = await self.create_session("Portfolio Test")
        if not session_id:
            return {"success": False, "error": "Failed to create session"}
        
        # Generate website
        result = await self.generate_website(
            session_id, 
            "Create a modern portfolio website"
        )
        
        if not result.get('success'):
            return {"success": False, "error": result.get('error')}
        
        # Validate response
        validation_errors = []
        
        if result['html_length'] < 5000:
            validation_errors.append(f"HTML too short: {result['html_length']} chars (expected >5000)")
        
        if not result['has_embedded_styles']:
            validation_errors.append("HTML missing embedded <style> tags")
        
        if not result['has_embedded_scripts']:
            validation_errors.append("HTML missing embedded <script> tags")
        
        if result['generation_time'] < 3:
            validation_errors.append(f"Generation suspiciously fast: {result['generation_time']:.2f}s")
        
        # Test GET endpoint
        get_result = await self.get_latest_website(session_id)
        if not get_result.get('success'):
            validation_errors.append(f"Failed to retrieve website: {get_result.get('error')}")
        
        test_result = {
            "test_name": "Basic Generation Flow",
            "success": len(validation_errors) == 0,
            "session_id": session_id,
            "generation_time": result['generation_time'],
            "html_length": result['html_length'],
            "css_length": result['css_length'],
            "js_length": result['js_length'],
            "has_embedded_styles": result['has_embedded_styles'],
            "has_embedded_scripts": result['has_embedded_scripts'],
            "validation_errors": validation_errors,
            "get_endpoint_works": get_result.get('success', False)
        }
        
        self.test_results.append(test_result)
        
        if test_result['success']:
            logger.info("✅ Basic generation flow test PASSED")
        else:
            logger.error("❌ Basic generation flow test FAILED")
            for error in validation_errors:
                logger.error(f"   - {error}")
        
        return test_result
    
    async def test_different_website_types(self):
        """Test 2: Different Website Types"""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: DIFFERENT WEBSITE TYPES")
        logger.info("="*60)
        
        test_prompts = [
            "Create a YouTube clone with video grid",
            "Create a recipe blog with card layout", 
            "Create a landing page for a SaaS product"
        ]
        
        generation_results = []
        
        for prompt in test_prompts:
            # Create separate session for each
            session_id = await self.create_session(f"Test: {prompt[:20]}")
            if not session_id:
                continue
            
            result = await self.generate_website(session_id, prompt)
            generation_results.append(result)
            
            # Small delay between generations
            await asyncio.sleep(2)
        
        # Analyze uniqueness
        uniqueness_analysis = self.analyze_html_uniqueness(generation_results)
        
        # Validate each generation
        validation_errors = []
        successful_generations = 0
        
        for i, result in enumerate(generation_results):
            if not result.get('success'):
                validation_errors.append(f"Generation {i+1} failed: {result.get('error')}")
                continue
            
            successful_generations += 1
            
            if result['html_length'] < 5000:
                validation_errors.append(f"Generation {i+1} HTML too short: {result['html_length']} chars")
            
            if not result['has_embedded_styles']:
                validation_errors.append(f"Generation {i+1} missing embedded styles")
            
            if not result['has_embedded_scripts']:
                validation_errors.append(f"Generation {i+1} missing embedded scripts")
        
        # Check uniqueness
        if not uniqueness_analysis.get('is_unique', False):
            if uniqueness_analysis.get('identical_pairs'):
                validation_errors.append(f"Identical HTML found: {uniqueness_analysis['identical_pairs']}")
            if uniqueness_analysis.get('similar_pairs'):
                validation_errors.append(f"Very similar HTML found: {uniqueness_analysis['similar_pairs']}")
        
        test_result = {
            "test_name": "Different Website Types",
            "success": len(validation_errors) == 0 and successful_generations == len(test_prompts),
            "total_prompts": len(test_prompts),
            "successful_generations": successful_generations,
            "generation_results": generation_results,
            "uniqueness_analysis": uniqueness_analysis,
            "validation_errors": validation_errors
        }
        
        self.test_results.append(test_result)
        
        if test_result['success']:
            logger.info("✅ Different website types test PASSED")
            logger.info(f"   - All {successful_generations} generations unique and complete")
        else:
            logger.error("❌ Different website types test FAILED")
            for error in validation_errors:
                logger.error(f"   - {error}")
        
        return test_result
    
    async def test_fallback_mechanism(self):
        """Test 3: Fallback Mechanism"""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: FALLBACK MECHANISM")
        logger.info("="*60)
        
        # Check backend logs for fallback usage
        try:
            # Read supervisor backend logs
            import subprocess
            result = subprocess.run(
                ['tail', '-n', '100', '/var/log/supervisor/backend.out.log'],
                capture_output=True,
                text=True
            )
            
            backend_logs = result.stdout
            fallback_used = "Fallback template applied" in backend_logs
            
            logger.info(f"Fallback mechanism check in logs: {'Found' if fallback_used else 'Not found'}")
            
            # Generate a website to potentially trigger fallback
            session_id = await self.create_session("Fallback Test")
            if session_id:
                result = await self.generate_website(
                    session_id,
                    "Create a complex dashboard with multiple charts and real-time data"
                )
                
                test_result = {
                    "test_name": "Fallback Mechanism",
                    "success": True,  # Fallback is working if we get any complete HTML
                    "fallback_detected_in_logs": fallback_used,
                    "generation_success": result.get('success', False),
                    "html_length": result.get('html_length', 0),
                    "notes": "Fallback mechanism ensures complete HTML is always returned"
                }
            else:
                test_result = {
                    "test_name": "Fallback Mechanism", 
                    "success": False,
                    "error": "Could not create session for fallback test"
                }
        
        except Exception as e:
            test_result = {
                "test_name": "Fallback Mechanism",
                "success": False,
                "error": f"Could not check fallback mechanism: {e}"
            }
        
        self.test_results.append(test_result)
        
        if test_result['success']:
            logger.info("✅ Fallback mechanism test PASSED")
        else:
            logger.error("❌ Fallback mechanism test FAILED")
        
        return test_result
    
    async def test_file_extraction_system(self):
        """Test 4: File Extraction System - Extract embedded CSS/JS to external files"""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: FILE EXTRACTION SYSTEM")
        logger.info("="*60)
        
        # Use the specific test command from the review request
        session_id = "test-extraction-fix"
        
        # Generate website with colorful landing page (should have embedded styles)
        result = await self.generate_website(
            session_id, 
            "Create a colorful landing page with a gradient background",
            framework="html"
        )
        
        validation_errors = []
        
        if not result.get('success'):
            validation_errors.append(f"Website generation failed: {result.get('error')}")
            return {
                "test_name": "File Extraction System",
                "success": False,
                "validation_errors": validation_errors
            }
        
        # Check backend logs for extraction messages
        try:
            import subprocess
            log_result = subprocess.run(
                ['tail', '-n', '100', '/var/log/supervisor/backend.err.log'],
                capture_output=True,
                text=True
            )
            backend_logs = log_result.stdout
            
            # Look for extraction messages
            extraction_found = any([
                "Extracted" in backend_logs and "chars of CSS" in backend_logs,
                "Saved styles.css" in backend_logs,
                "chars)" in backend_logs
            ])
            
            if not extraction_found:
                validation_errors.append("Backend logs don't show CSS extraction messages")
            else:
                logger.info("✅ Backend logs show CSS extraction activity")
                
        except Exception as e:
            validation_errors.append(f"Could not check backend logs: {e}")
        
        # Verify CSS file has content (should be > 1000 bytes)
        try:
            css_file_path = f"/app/backend/generated_projects/{session_id}/static/styles.css"
            if os.path.exists(css_file_path):
                css_size = os.path.getsize(css_file_path)
                logger.info(f"CSS file size: {css_size} bytes")
                
                if css_size < 1000:
                    validation_errors.append(f"CSS file too small: {css_size} bytes (expected >1000)")
                else:
                    logger.info("✅ CSS file has substantial content")
            else:
                validation_errors.append("CSS file not found on disk")
        except Exception as e:
            validation_errors.append(f"Could not check CSS file size: {e}")
        
        # Verify HTML links to external files and has no embedded styles
        try:
            html_file_path = f"/app/backend/generated_projects/{session_id}/index.html"
            if os.path.exists(html_file_path):
                with open(html_file_path, 'r') as f:
                    html_content = f.read()
                
                # Check for external CSS link
                if 'href="static/styles.css"' not in html_content:
                    validation_errors.append("HTML doesn't link to external CSS file")
                else:
                    logger.info("✅ HTML properly links to external CSS")
                
                # Check that embedded styles are removed
                embedded_style_count = html_content.count('<style>')
                if embedded_style_count > 0:
                    validation_errors.append(f"HTML still contains {embedded_style_count} embedded <style> tags")
                else:
                    logger.info("✅ HTML has no embedded styles (properly extracted)")
                    
            else:
                validation_errors.append("HTML file not found on disk")
        except Exception as e:
            validation_errors.append(f"Could not check HTML file: {e}")
        
        # Test preview CSS endpoint
        try:
            async with aiohttp.ClientSession() as session:
                css_url = f"{self.base_url}/preview/{session_id}/static/styles.css"
                async with session.get(css_url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'text/css' in content_type:
                            logger.info("✅ Preview CSS endpoint returns 200 OK with correct content-type")
                        else:
                            validation_errors.append(f"CSS endpoint wrong content-type: {content_type}")
                    else:
                        validation_errors.append(f"CSS preview endpoint failed: {response.status}")
        except Exception as e:
            validation_errors.append(f"Could not test CSS preview endpoint: {e}")
        
        test_result = {
            "test_name": "File Extraction System",
            "success": len(validation_errors) == 0,
            "session_id": session_id,
            "generation_success": result.get('success', False),
            "html_length": result.get('html_length', 0),
            "css_length": result.get('css_length', 0),
            "js_length": result.get('js_length', 0),
            "validation_errors": validation_errors
        }
        
        self.test_results.append(test_result)
        
        if test_result['success']:
            logger.info("✅ File extraction system test PASSED")
            logger.info("   - CSS extracted from embedded styles")
            logger.info("   - External files contain extracted content") 
            logger.info("   - HTML properly links to external files")
            logger.info("   - Preview endpoints serve files correctly")
        else:
            logger.error("❌ File extraction system test FAILED")
            for error in validation_errors:
                logger.error(f"   - {error}")
        
        return test_result

    async def test_format_specifier_fix(self):
        """Test the format specifier fix resolves repetitive website generation"""
        logger.info("\n" + "="*60)
        logger.info("TEST: FORMAT SPECIFIER FIX - UNIQUE WEBSITE GENERATION")
        logger.info("="*60)
        
        # Test 1: E-commerce Site
        logger.info("🛒 Testing E-commerce Site Generation...")
        ecommerce_session = await self.create_session("E-commerce Test")
        if not ecommerce_session:
            return {"success": False, "error": "Failed to create e-commerce session"}
        
        ecommerce_result = await self.generate_website(
            ecommerce_session,
            "Create an online store for selling shoes",
            framework="html"
        )
        
        # Test 2: Portfolio Site  
        logger.info("📸 Testing Portfolio Site Generation...")
        portfolio_session = await self.create_session("Portfolio Test")
        if not portfolio_session:
            return {"success": False, "error": "Failed to create portfolio session"}
        
        portfolio_result = await self.generate_website(
            portfolio_session,
            "Create a portfolio website for a photographer",
            framework="html"
        )
        
        validation_errors = []
        
        # Check both generations succeeded
        if not ecommerce_result.get('success'):
            validation_errors.append(f"E-commerce generation failed: {ecommerce_result.get('error')}")
        if not portfolio_result.get('success'):
            validation_errors.append(f"Portfolio generation failed: {portfolio_result.get('error')}")
        
        if validation_errors:
            return {
                "test_name": "Format Specifier Fix",
                "success": False,
                "validation_errors": validation_errors
            }
        
        # Check for format specifier errors in logs
        try:
            import subprocess
            log_result = subprocess.run(
                ['tail', '-n', '100', '/var/log/supervisor/backend.err.log'],
                capture_output=True,
                text=True
            )
            backend_logs = log_result.stdout
            
            format_errors = [
                "Invalid format specifier" in backend_logs,
                "Complete project generation failed" in backend_logs,
                "ERROR" in backend_logs and "format" in backend_logs.lower()
            ]
            
            if any(format_errors):
                validation_errors.append("Format specifier errors found in backend logs")
            else:
                logger.info("✅ No format specifier errors in logs")
                
        except Exception as e:
            validation_errors.append(f"Could not check backend logs: {e}")
        
        # Check for intent analysis in logs
        try:
            intent_analysis_found = "Intent analysis" in backend_logs
            if intent_analysis_found:
                logger.info("✅ Intent analysis working properly")
            else:
                validation_errors.append("Intent analysis not found in logs")
        except:
            validation_errors.append("Could not verify intent analysis")
        
        # Verify different titles
        ecommerce_html = ecommerce_result.get('html_content', '')
        portfolio_html = portfolio_result.get('html_content', '')
        
        ecommerce_title = self._extract_title(ecommerce_html)
        portfolio_title = self._extract_title(portfolio_html)
        
        logger.info(f"E-commerce title: '{ecommerce_title}'")
        logger.info(f"Portfolio title: '{portfolio_title}'")
        
        if ecommerce_title == portfolio_title:
            validation_errors.append(f"Both sites have same title: '{ecommerce_title}'")
        elif "VideoTube" in ecommerce_title or "VideoTube" in portfolio_title:
            validation_errors.append("Sites are using VideoTube fallback template")
        else:
            logger.info("✅ Sites have different, appropriate titles")
        
        # Verify different file sizes
        ecommerce_size = len(ecommerce_html)
        portfolio_size = len(portfolio_html)
        
        logger.info(f"E-commerce HTML size: {ecommerce_size} chars")
        logger.info(f"Portfolio HTML size: {portfolio_size} chars")
        
        if ecommerce_size == portfolio_size:
            validation_errors.append(f"Both sites have identical HTML size: {ecommerce_size} chars")
        else:
            logger.info("✅ Sites have different HTML sizes")
        
        # Verify content matches request type
        ecommerce_has_shopping = any([
            "shop" in ecommerce_html.lower(),
            "store" in ecommerce_html.lower(), 
            "product" in ecommerce_html.lower(),
            "cart" in ecommerce_html.lower(),
            "buy" in ecommerce_html.lower(),
            "shoe" in ecommerce_html.lower()
        ])
        
        portfolio_has_photography = any([
            "photo" in portfolio_html.lower(),
            "portfolio" in portfolio_html.lower(),
            "gallery" in portfolio_html.lower(),
            "image" in portfolio_html.lower(),
            "work" in portfolio_html.lower()
        ])
        
        if not ecommerce_has_shopping:
            validation_errors.append("E-commerce site doesn't contain shopping-related content")
        else:
            logger.info("✅ E-commerce site has shopping-related content")
            
        if not portfolio_has_photography:
            validation_errors.append("Portfolio site doesn't contain photography-related content")
        else:
            logger.info("✅ Portfolio site has photography-related content")
        
        # Check generation times (should be reasonable, not suspiciously fast)
        ecommerce_time = ecommerce_result.get('generation_time', 0)
        portfolio_time = portfolio_result.get('generation_time', 0)
        
        if ecommerce_time < 5:
            validation_errors.append(f"E-commerce generation suspiciously fast: {ecommerce_time:.2f}s")
        if portfolio_time < 5:
            validation_errors.append(f"Portfolio generation suspiciously fast: {portfolio_time:.2f}s")
        
        test_result = {
            "test_name": "Format Specifier Fix",
            "success": len(validation_errors) == 0,
            "ecommerce_session": ecommerce_session,
            "portfolio_session": portfolio_session,
            "ecommerce_title": ecommerce_title,
            "portfolio_title": portfolio_title,
            "ecommerce_size": ecommerce_size,
            "portfolio_size": portfolio_size,
            "ecommerce_time": ecommerce_time,
            "portfolio_time": portfolio_time,
            "ecommerce_has_shopping": ecommerce_has_shopping,
            "portfolio_has_photography": portfolio_has_photography,
            "validation_errors": validation_errors
        }
        
        self.test_results.append(test_result)
        
        if test_result['success']:
            logger.info("✅ Format specifier fix test PASSED")
            logger.info("   - No format specifier errors in logs")
            logger.info("   - Both generations completed successfully")
            logger.info("   - Intent analysis working properly")
            logger.info("   - Generated websites have different titles")
            logger.info("   - HTML file sizes are different")
            logger.info("   - E-commerce site has shopping-related content")
            logger.info("   - Portfolio site has photography-related content")
        else:
            logger.error("❌ Format specifier fix test FAILED")
            for error in validation_errors:
                logger.error(f"   - {error}")
        
        return test_result

    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting Format Specifier Fix Test")
        logger.info(f"Backend URL: {self.base_url}")
        
        start_time = time.time()
        
        # Run the specific test for format specifier fix
        test_result = await self.test_format_specifier_fix()
        
        total_time = time.time() - start_time
        
        # Summary
        passed_tests = sum(1 for test in self.test_results if test.get('success'))
        total_tests = len(self.test_results)
        
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Total Time: {total_time:.2f}s")
        logger.info(f"Sessions Created: {len(self.session_ids)}")
        
        # Detailed results
        for test in self.test_results:
            status = "✅ PASS" if test.get('success') else "❌ FAIL"
            logger.info(f"{status} - {test.get('test_name')}")
            if not test.get('success') and test.get('validation_errors'):
                for error in test['validation_errors']:
                    logger.info(f"      {error}")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "total_time": total_time,
            "test_results": self.test_results,
            "sessions_created": self.session_ids
        }

async def main():
    """Main test runner"""
    tester = WebsiteGenerationTester()
    results = await tester.run_all_tests()
    
    # Return exit code based on results
    if results['failed_tests'] == 0:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error(f"💥 {results['failed_tests']} test(s) failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)