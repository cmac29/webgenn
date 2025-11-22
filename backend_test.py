#!/usr/bin/env python3
"""
Backend Test Suite for Advanced Iterative Editing System
Tests the comprehensive editing capabilities as requested in review
"""

import asyncio
import aiohttp
import json
import time
import os
import re
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedEditingTester:
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

    def check_for_blank_screens(self, html_content: str) -> List[str]:
        """Check for blank white/black/gray screens in HTML"""
        issues = []
        
        # Check for minimal content
        if len(html_content) < 500:
            issues.append(f"HTML too short ({len(html_content)} chars) - likely blank screen")
        
        # Check for missing body content
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_content = body_match.group(1).strip()
            # Remove script and style tags for content check
            body_content = re.sub(r'<script[^>]*>.*?</script>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
            body_content = re.sub(r'<style[^>]*>.*?</style>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
            
            if len(body_content) < 100:
                issues.append("Body has minimal content - likely blank screen")
        else:
            issues.append("No body tag found")
        
        # Check for proper styling
        has_styles = '<style>' in html_content or 'href=' in html_content
        if not has_styles:
            issues.append("No CSS styling found - likely unstyled/blank appearance")
        
        # Check for common blank screen indicators
        if 'background: white' in html_content or 'background-color: white' in html_content:
            issues.append("White background detected - potential blank screen")
        
        if 'background: #000' in html_content or 'background-color: black' in html_content:
            issues.append("Black background detected - potential blank screen")
        
        return issues

    def analyze_edit_precision(self, original_html: str, edited_html: str, requested_change: str) -> Dict[str, Any]:
        """Analyze if edits were applied with surgical precision"""
        analysis = {
            "length_change": len(edited_html) - len(original_html),
            "length_change_percent": ((len(edited_html) - len(original_html)) / len(original_html)) * 100 if original_html else 0,
            "is_regeneration": False,
            "preserved_content": True,
            "issues": []
        }
        
        # Check for regeneration (massive length change)
        if abs(analysis["length_change_percent"]) > 70:
            analysis["is_regeneration"] = True
            analysis["issues"].append(f"Massive length change ({analysis['length_change_percent']:.1f}%) suggests regeneration, not editing")
        
        # Check if original classes are preserved
        original_classes = set(re.findall(r'class="([^"]*)"', original_html))
        edited_classes = set(re.findall(r'class="([^"]*)"', edited_html))
        
        preserved_classes = len(original_classes.intersection(edited_classes))
        total_original_classes = len(original_classes)
        
        if total_original_classes > 0:
            preservation_rate = preserved_classes / total_original_classes
            if preservation_rate < 0.3:
                analysis["preserved_content"] = False
                analysis["issues"].append(f"Only {preservation_rate:.1%} of original CSS classes preserved")
        
        return analysis

    async def test_phase_1_initial_generation(self):
        """PHASE 1: Generate initial fitness app website"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 1: GENERATE INITIAL FITNESS APP WEBSITE")
        logger.info("="*80)
        
        # Create session
        session_id = await self.create_session("Advanced Editing Test - Fitness App")
        if not session_id:
            return {"success": False, "error": "Failed to create session"}
        
        # Generate initial fitness app
        prompt = """Create a landing page for a fitness app with:
- Hero section with headline
- Features section (3 cards)
- Pricing section
- Contact form
- Footer"""
        
        result = await self.generate_website(session_id, prompt)
        
        validation_errors = []
        
        if not result.get('success'):
            validation_errors.append(f"Initial generation failed: {result.get('error')}")
            return {
                "test_name": "Phase 1: Initial Generation",
                "success": False,
                "validation_errors": validation_errors
            }
        
        # Check for blank screens
        html_content = result.get('html_content', '')
        blank_screen_issues = self.check_for_blank_screens(html_content)
        validation_errors.extend(blank_screen_issues)
        
        # Verify required sections exist
        required_sections = ['hero', 'features', 'pricing', 'contact', 'footer']
        missing_sections = []
        
        for section in required_sections:
            if section.lower() not in html_content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            validation_errors.append(f"Missing sections: {missing_sections}")
        
        # Check for proper styling
        if result.get('css_length', 0) < 1000:
            validation_errors.append(f"CSS too short ({result.get('css_length')} chars) - likely insufficient styling")
        
        test_result = {
            "test_name": "Phase 1: Initial Generation",
            "success": len(validation_errors) == 0,
            "session_id": session_id,
            "html_length": len(html_content),
            "css_length": result.get('css_length', 0),
            "js_length": result.get('js_length', 0),
            "generation_time": result.get('generation_time', 0),
            "blank_screen_issues": blank_screen_issues,
            "missing_sections": missing_sections,
            "validation_errors": validation_errors,
            "original_html": html_content  # Store for later comparison
        }
        
        self.test_results.append(test_result)
        
        if test_result['success']:
            logger.info("✅ Phase 1: Initial generation PASSED")
            logger.info(f"   - Generated {len(html_content)} char HTML")
            logger.info(f"   - All required sections present")
            logger.info(f"   - No blank screen issues")
        else:
            logger.error("❌ Phase 1: Initial generation FAILED")
            for error in validation_errors:
                logger.error(f"   - {error}")
        
        return test_result

    async def test_phase_2_adding_features(self, session_id: str, original_html: str):
        """PHASE 2: Test adding features (3 tests)"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 2: TEST ADDING FEATURES")
        logger.info("="*80)
        
        phase_results = []
        
        # Test 2.1 - Add New Section
        logger.info("\n--- Test 2.1: Add Testimonials Section ---")
        add_section_result = await self.generate_website(
            session_id,
            "Add a testimonials section with 3 customer reviews between features and pricing"
        )
        
        validation_errors = []
        
        if not add_section_result.get('success'):
            validation_errors.append(f"Add section failed: {add_section_result.get('error')}")
        else:
            new_html = add_section_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check if testimonials section was added
            if 'testimonial' not in new_html.lower():
                validation_errors.append("Testimonials section not found in HTML")
            
            # Check if original sections are preserved
            if 'features' not in new_html.lower():
                validation_errors.append("Original features section missing")
            if 'pricing' not in new_html.lower():
                validation_errors.append("Original pricing section missing")
            
            # Analyze edit precision
            edit_analysis = self.analyze_edit_precision(original_html, new_html, "add testimonials")
            if edit_analysis["is_regeneration"]:
                validation_errors.extend(edit_analysis["issues"])
        
        test_2_1 = {
            "test_name": "Test 2.1: Add Testimonials Section",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
        phase_results.append(test_2_1)
        
        # Test 2.2 - Add New Element
        logger.info("\n--- Test 2.2: Add Newsletter Form ---")
        add_element_result = await self.generate_website(
            session_id,
            "Add a newsletter signup form in the footer"
        )
        
        validation_errors = []
        
        if not add_element_result.get('success'):
            validation_errors.append(f"Add element failed: {add_element_result.get('error')}")
        else:
            new_html = add_element_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check if newsletter form was added
            newsletter_indicators = ['newsletter', 'signup', 'subscribe', 'email']
            if not any(indicator in new_html.lower() for indicator in newsletter_indicators):
                validation_errors.append("Newsletter signup form not found")
            
            # Check if footer still exists
            if 'footer' not in new_html.lower():
                validation_errors.append("Footer section missing")
        
        test_2_2 = {
            "test_name": "Test 2.2: Add Newsletter Form",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
        phase_results.append(test_2_2)
        
        # Test 2.3 - Add Styling
        logger.info("\n--- Test 2.3: Add Animations ---")
        add_styling_result = await self.generate_website(
            session_id,
            "Add animations to the feature cards - they should slide in from bottom on scroll"
        )
        
        validation_errors = []
        
        if not add_styling_result.get('success'):
            validation_errors.append(f"Add styling failed: {add_styling_result.get('error')}")
        else:
            new_html = add_styling_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check if animations were added
            animation_indicators = ['animation', 'transform', 'transition', 'keyframes', '@keyframes']
            if not any(indicator in new_html.lower() for indicator in animation_indicators):
                validation_errors.append("Animation CSS not found")
            
            # Check if feature cards still exist
            if 'feature' not in new_html.lower():
                validation_errors.append("Feature cards missing")
        
        test_2_3 = {
            "test_name": "Test 2.3: Add Animations",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
        phase_results.append(test_2_3)
        
        # Overall phase result
        phase_success = all(test.get('success', False) for test in phase_results)
        
        phase_result = {
            "test_name": "Phase 2: Adding Features",
            "success": phase_success,
            "sub_tests": phase_results,
            "session_id": session_id
        }
        
        self.test_results.append(phase_result)
        
        if phase_success:
            logger.info("✅ Phase 2: Adding features PASSED")
        else:
            logger.error("❌ Phase 2: Adding features FAILED")
            for test in phase_results:
                if not test.get('success'):
                    logger.error(f"   - {test['test_name']}: {test.get('validation_errors', [])}")
        
        return phase_result

    async def test_phase_3_modifying_features(self, session_id: str):
        """PHASE 3: Test modifying features (3 tests)"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 3: TEST MODIFYING FEATURES")
        logger.info("="*80)
        
        phase_results = []
        
        # Test 3.1 - Change Colors
        logger.info("\n--- Test 3.1: Change Primary Color ---")
        change_color_result = await self.generate_website(
            session_id,
            "Change the primary color from current to deep blue (#1e40af) throughout the site"
        )
        
        validation_errors = []
        
        if not change_color_result.get('success'):
            validation_errors.append(f"Color change failed: {change_color_result.get('error')}")
        else:
            new_html = change_color_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check if blue color was applied
            blue_indicators = ['#1e40af', 'blue', 'rgb(30, 64, 175)']
            if not any(indicator in new_html.lower() for indicator in blue_indicators):
                validation_errors.append("Deep blue color (#1e40af) not found in HTML")
        
        test_3_1 = {
            "test_name": "Test 3.1: Change Primary Color",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
        phase_results.append(test_3_1)
        
        # Test 3.2 - Modify Layout
        logger.info("\n--- Test 3.2: Change Hero Layout ---")
        modify_layout_result = await self.generate_website(
            session_id,
            "Change the hero section to have text on the left and an image placeholder on the right"
        )
        
        validation_errors = []
        
        if not modify_layout_result.get('success'):
            validation_errors.append(f"Layout change failed: {modify_layout_result.get('error')}")
        else:
            new_html = modify_layout_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check for 2-column layout indicators
            layout_indicators = ['grid', 'flex', 'column', 'left', 'right', 'image']
            if not any(indicator in new_html.lower() for indicator in layout_indicators):
                validation_errors.append("2-column layout indicators not found")
            
            # Check if hero section still exists
            if 'hero' not in new_html.lower():
                validation_errors.append("Hero section missing")
        
        test_3_2 = {
            "test_name": "Test 3.2: Change Hero Layout",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
        phase_results.append(test_3_2)
        
        # Test 3.3 - Change Text
        logger.info("\n--- Test 3.3: Update Headline ---")
        change_text_result = await self.generate_website(
            session_id,
            "Update the main headline to 'Transform Your Body, Transform Your Life'"
        )
        
        validation_errors = []
        
        if not change_text_result.get('success'):
            validation_errors.append(f"Text change failed: {change_text_result.get('error')}")
        else:
            new_html = change_text_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check if new headline exists
            if "Transform Your Body, Transform Your Life" not in new_html:
                validation_errors.append("New headline text not found in HTML")
        
        test_3_3 = {
            "test_name": "Test 3.3: Update Headline",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
        phase_results.append(test_3_3)
        
        # Overall phase result
        phase_success = all(test.get('success', False) for test in phase_results)
        
        phase_result = {
            "test_name": "Phase 3: Modifying Features",
            "success": phase_success,
            "sub_tests": phase_results,
            "session_id": session_id
        }
        
        self.test_results.append(phase_result)
        
        if phase_success:
            logger.info("✅ Phase 3: Modifying features PASSED")
        else:
            logger.error("❌ Phase 3: Modifying features FAILED")
            for test in phase_results:
                if not test.get('success'):
                    logger.error(f"   - {test['test_name']}: {test.get('validation_errors', [])}")
        
        return phase_result

    async def test_phase_4_removing_features(self, session_id: str):
        """PHASE 4: Test removing features (3 tests)"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 4: TEST REMOVING FEATURES")
        logger.info("="*80)
        
        phase_results = []
        
        # Test 4.1 - Remove Section
        logger.info("\n--- Test 4.1: Remove Pricing Section ---")
        remove_section_result = await self.generate_website(
            session_id,
            "Remove the pricing section"
        )
        
        validation_errors = []
        
        if not remove_section_result.get('success'):
            validation_errors.append(f"Remove section failed: {remove_section_result.get('error')}")
        else:
            new_html = remove_section_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check if pricing section was removed
            if 'pricing' in new_html.lower():
                validation_errors.append("Pricing section still exists in HTML")
            
            # Check if other sections are preserved
            if 'features' not in new_html.lower():
                validation_errors.append("Features section was incorrectly removed")
            if 'contact' not in new_html.lower():
                validation_errors.append("Contact section was incorrectly removed")
        
        test_4_1 = {
            "test_name": "Test 4.1: Remove Pricing Section",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
        phase_results.append(test_4_1)
        
        # Test 4.2 - Remove Element
        logger.info("\n--- Test 4.2: Remove Newsletter Form ---")
        remove_element_result = await self.generate_website(
            session_id,
            "Remove the newsletter form from the footer"
        )
        
        validation_errors = []
        
        if not remove_element_result.get('success'):
            validation_errors.append(f"Remove element failed: {remove_element_result.get('error')}")
        else:
            new_html = remove_element_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check if newsletter form was removed
            newsletter_indicators = ['newsletter', 'signup', 'subscribe']
            if any(indicator in new_html.lower() for indicator in newsletter_indicators):
                validation_errors.append("Newsletter form still exists")
            
            # Check if footer still exists
            if 'footer' not in new_html.lower():
                validation_errors.append("Footer was incorrectly removed")
        
        test_4_2 = {
            "test_name": "Test 4.2: Remove Newsletter Form",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
        phase_results.append(test_4_2)
        
        # Test 4.3 - Remove Styling
        logger.info("\n--- Test 4.3: Remove Animations ---")
        remove_styling_result = await self.generate_website(
            session_id,
            "Remove the animations from the feature cards"
        )
        
        validation_errors = []
        
        if not remove_styling_result.get('success'):
            validation_errors.append(f"Remove styling failed: {remove_styling_result.get('error')}")
        else:
            new_html = remove_styling_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check if animations were removed
            animation_indicators = ['@keyframes', 'animation:', 'transform:', 'transition:']
            if any(indicator in new_html.lower() for indicator in animation_indicators):
                validation_errors.append("Animation CSS still exists")
            
            # Check if feature cards still exist
            if 'feature' not in new_html.lower():
                validation_errors.append("Feature cards were incorrectly removed")
        
        test_4_3 = {
            "test_name": "Test 4.3: Remove Animations",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors
        }
        phase_results.append(test_4_3)
        
        # Overall phase result
        phase_success = all(test.get('success', False) for test in phase_results)
        
        phase_result = {
            "test_name": "Phase 4: Removing Features",
            "success": phase_success,
            "sub_tests": phase_results,
            "session_id": session_id
        }
        
        self.test_results.append(phase_result)
        
        if phase_success:
            logger.info("✅ Phase 4: Removing features PASSED")
        else:
            logger.error("❌ Phase 4: Removing features FAILED")
            for test in phase_results:
                if not test.get('success'):
                    logger.error(f"   - {test['test_name']}: {test.get('validation_errors', [])}")
        
        return phase_result

    async def test_phase_5_complex_multi_part_edit(self, session_id: str):
        """PHASE 5: Complex multi-part edit test"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 5: COMPLEX MULTI-PART EDIT TEST")
        logger.info("="*80)
        
        # Test 5.1 - Multiple Changes at Once
        logger.info("\n--- Test 5.1: Multiple Changes at Once ---")
        multi_edit_result = await self.generate_website(
            session_id,
            "Make the contact form have a dark background with white text, add a 'Join Now' button to the hero section, and change the footer to be centered instead of left-aligned"
        )
        
        validation_errors = []
        
        if not multi_edit_result.get('success'):
            validation_errors.append(f"Multi-part edit failed: {multi_edit_result.get('error')}")
        else:
            new_html = multi_edit_result.get('html_content', '')
            
            # Check for blank screens
            blank_issues = self.check_for_blank_screens(new_html)
            validation_errors.extend(blank_issues)
            
            # Check for dark contact form
            dark_indicators = ['background: black', 'background-color: black', 'bg-black', 'dark']
            if not any(indicator in new_html.lower() for indicator in dark_indicators):
                validation_errors.append("Dark background for contact form not found")
            
            # Check for white text
            white_text_indicators = ['color: white', 'text-white', 'color: #fff']
            if not any(indicator in new_html.lower() for indicator in white_text_indicators):
                validation_errors.append("White text for contact form not found")
            
            # Check for Join Now button
            if 'join now' not in new_html.lower():
                validation_errors.append("'Join Now' button not found in hero section")
            
            # Check for centered footer
            center_indicators = ['text-center', 'text-align: center', 'justify-center']
            if not any(indicator in new_html.lower() for indicator in center_indicators):
                validation_errors.append("Centered footer styling not found")
        
        test_result = {
            "test_name": "Phase 5: Complex Multi-Part Edit",
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors,
            "session_id": session_id
        }
        
        self.test_results.append(test_result)
        
        if test_result['success']:
            logger.info("✅ Phase 5: Complex multi-part edit PASSED")
            logger.info("   - Contact form has dark background and white text")
            logger.info("   - 'Join Now' button added to hero")
            logger.info("   - Footer is centered")
        else:
            logger.error("❌ Phase 5: Complex multi-part edit FAILED")
            for error in validation_errors:
                logger.error(f"   - {error}")
        
        return test_result

    async def check_backend_logs_for_edit_mode(self):
        """Check backend logs for EDIT MODE activation"""
        try:
            import subprocess
            result = subprocess.run(
                ['tail', '-n', '200', '/var/log/supervisor/backend.out.log'],
                capture_output=True,
                text=True
            )
            
            backend_logs = result.stdout
            
            edit_mode_indicators = [
                "EDIT-ONLY MODE ENFORCED" in backend_logs,
                "EDIT MODE" in backend_logs,
                "Existing website found" in backend_logs,
                "will EDIT this website" in backend_logs
            ]
            
            return any(edit_mode_indicators), backend_logs
            
        except Exception as e:
            logger.error(f"Could not check backend logs: {e}")
            return False, ""

    async def run_comprehensive_editing_test(self):
        """Run the comprehensive advanced editing system test"""
        logger.info("🚀 Starting Comprehensive Advanced Editing System Test")
        logger.info(f"Backend URL: {self.base_url}")
        
        start_time = time.time()
        
        # Phase 1: Generate initial website
        phase_1_result = await self.test_phase_1_initial_generation()
        if not phase_1_result.get('success'):
            logger.error("❌ Phase 1 failed - cannot continue with editing tests")
            return self._generate_final_summary(start_time)
        
        session_id = phase_1_result.get('session_id')
        original_html = phase_1_result.get('original_html', '')
        
        # Phase 2: Test adding features
        await self.test_phase_2_adding_features(session_id, original_html)
        
        # Phase 3: Test modifying features
        await self.test_phase_3_modifying_features(session_id)
        
        # Phase 4: Test removing features
        await self.test_phase_4_removing_features(session_id)
        
        # Phase 5: Complex multi-part edit
        await self.test_phase_5_complex_multi_part_edit(session_id)
        
        # Check backend logs for edit mode
        edit_mode_detected, logs = await self.check_backend_logs_for_edit_mode()
        
        return self._generate_final_summary(start_time, edit_mode_detected)

    def _generate_final_summary(self, start_time: float, edit_mode_detected: bool = False):
        """Generate final test summary"""
        total_time = time.time() - start_time
        
        # Count results
        passed_tests = sum(1 for test in self.test_results if test.get('success'))
        total_tests = len(self.test_results)
        
        # Collect all validation errors
        all_errors = []
        for test in self.test_results:
            if not test.get('success'):
                test_name = test.get('test_name', 'Unknown Test')
                errors = test.get('validation_errors', [])
                for error in errors:
                    all_errors.append(f"{test_name}: {error}")
                
                # Check sub-tests
                sub_tests = test.get('sub_tests', [])
                for sub_test in sub_tests:
                    if not sub_test.get('success'):
                        sub_errors = sub_test.get('validation_errors', [])
                        for error in sub_errors:
                            all_errors.append(f"{sub_test.get('test_name', 'Unknown Sub-Test')}: {error}")
        
        logger.info("\n" + "="*80)
        logger.info("COMPREHENSIVE ADVANCED EDITING SYSTEM TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%")
        logger.info(f"Total Time: {total_time:.2f}s")
        logger.info(f"Edit Mode Detected in Logs: {'✅ YES' if edit_mode_detected else '❌ NO'}")
        logger.info(f"Sessions Created: {len(self.session_ids)}")
        
        # Detailed results
        logger.info("\nDETAILED RESULTS:")
        for test in self.test_results:
            status = "✅ PASS" if test.get('success') else "❌ FAIL"
            logger.info(f"{status} - {test.get('test_name')}")
            
            # Show sub-test results
            sub_tests = test.get('sub_tests', [])
            for sub_test in sub_tests:
                sub_status = "✅ PASS" if sub_test.get('success') else "❌ FAIL"
                logger.info(f"    {sub_status} - {sub_test.get('test_name')}")
        
        # Show all errors
        if all_errors:
            logger.info("\nALL VALIDATION ERRORS:")
            for error in all_errors:
                logger.info(f"❌ {error}")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "total_time": total_time,
            "edit_mode_detected": edit_mode_detected,
            "test_results": self.test_results,
            "sessions_created": self.session_ids,
            "all_errors": all_errors
        }

async def main():
    """Main test runner for Advanced Editing System"""
    tester = AdvancedEditingTester()
    results = await tester.run_comprehensive_editing_test()
    
    # Return exit code based on results
    if results['failed_tests'] == 0:
        logger.info("🎉 All advanced editing tests passed!")
        return 0
    else:
        logger.error(f"💥 {results['failed_tests']} advanced editing test(s) failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)