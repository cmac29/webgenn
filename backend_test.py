#!/usr/bin/env python3
"""
Backend Test Suite for Netlify Generation and Deployment Flow
Tests the complete Netlify auto-deployment functionality as requested in review
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

class NetlifyDeploymentTester:
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
        return "https://code-weaver-9.preview.emergentagent.com/api"
    
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
    
    async def test_netlify_generate_and_deploy(self, session_id: str) -> Dict[str, Any]:
        """Test the complete Netlify generation and deployment flow with the EXACT prompt from review request"""
        logger.info("\n" + "="*80)
        logger.info("CRITICAL TEST - MAX TOKENS FIX VERIFICATION")
        logger.info("="*80)
        
        async with aiohttp.ClientSession() as session:
            try:
                start_time = time.time()
                
                # EXACT prompt from review request
                payload = {
                    "session_id": session_id,
                    "prompt": "make me a modern website for a renovation business, the home page background should have high quality images and the tab bar should be designed well along with the buttons that take you to different sections on the site such as services and the contact form. the renovation business's services are as follows: Flooring including epoxy flooring, Bathrooms, Kitchens, Full house, etc.. make it look good",
                    "model": "gpt-5",
                    "edit_mode": False
                }
                
                logger.info(f"🚀 Generating AND deploying website to Netlify...")
                logger.info(f"   Session ID: {session_id}")
                logger.info(f"   Prompt: {payload['prompt']}")
                
                async with session.post(
                    f"{self.base_url}/netlify/generate-and-deploy",
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
                            "generation_time": generation_time,
                            "response_data": data,
                            "project": data.get('project', {}),
                            "deployment": data.get('deployment', {}),
                            "deploy_preview_url": data.get('deploy_preview_url'),
                            "instant_url": data.get('instant_url')
                        }
                        
                        logger.info(f"✅ Netlify generation and deployment completed in {generation_time:.2f}s")
                        logger.info(f"   Project ID: {result['project'].get('project_id')}")
                        logger.info(f"   Deploy Preview URL: {result['deploy_preview_url']}")
                        
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Netlify generation and deployment failed: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "session_id": session_id,
                            "generation_time": generation_time,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
                        
            except asyncio.TimeoutError:
                logger.error(f"❌ Netlify generation and deployment timed out after 5 minutes")
                return {
                    "success": False,
                    "session_id": session_id,
                    "error": "Generation and deployment timed out"
                }
            except Exception as e:
                logger.error(f"❌ Netlify generation and deployment error: {e}")
                return {
                    "success": False,
                    "session_id": session_id,
                    "error": str(e)
                }

    async def test_live_url_accessibility(self, url: str) -> Dict[str, Any]:
        """Test if the live Netlify URL is accessible and contains expected content"""
        logger.info(f"🌐 Testing live URL accessibility: {url}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Check if it contains HTML content
                        has_html = '<html' in content.lower() or '<!doctype html' in content.lower()
                        has_renovation_content = any([
                            'renovation' in content.lower(),
                            'flooring' in content.lower(),
                            'bathroom' in content.lower(),
                            'kitchen' in content.lower(),
                            'epoxy' in content.lower(),
                            'services' in content.lower(),
                            'contact' in content.lower()
                        ])
                        
                        result = {
                            "success": True,
                            "status_code": response.status,
                            "content_length": len(content),
                            "has_html": has_html,
                            "has_renovation_content": has_renovation_content,
                            "content_preview": content[:500] + "..." if len(content) > 500 else content
                        }
                        
                        logger.info(f"✅ Live URL is accessible")
                        logger.info(f"   Status: {response.status}")
                        logger.info(f"   Content Length: {len(content)} chars")
                        logger.info(f"   Contains HTML: {has_html}")
                        logger.info(f"   Contains Renovation Content: {has_renovation_content}")
                        
                        return result
                    else:
                        logger.error(f"❌ Live URL returned status {response.status}")
                        return {
                            "success": False,
                            "status_code": response.status,
                            "error": f"HTTP {response.status}"
                        }
                        
            except Exception as e:
                logger.error(f"❌ Error accessing live URL: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

    async def check_backend_logs_for_deployment(self) -> Dict[str, Any]:
        """Check backend logs for deployment success messages and AI response details"""
        try:
            import subprocess
            result = subprocess.run(
                ['tail', '-n', '500', '/var/log/supervisor/backend.out.log'],
                capture_output=True,
                text=True
            )
            
            backend_logs = result.stdout
            
            # Look for deployment success indicators
            success_indicators = [
                "🚀 Creating Netlify site" in backend_logs,
                "✅ Site created" in backend_logs,
                "✅ Deployment created" in backend_logs,
                "✅ Build completed successfully!" in backend_logs,
                "DEPLOYMENT SUCCESS" in backend_logs
            ]
            
            # Look for error indicators
            error_indicators = [
                "text_unidecode" in backend_logs,
                "ERROR" in backend_logs and "netlify" in backend_logs.lower(),
                "DEPLOYMENT FAILED" in backend_logs,
                "Budget has been exceeded" in backend_logs,
                "encountered an error" in backend_logs,
                "PARSING COMPLETELY FAILED" in backend_logs
            ]
            
            # Look for AI response character count (max_tokens fix verification)
            ai_response_chars = None
            import re
            char_match = re.search(r'AI Response received: (\d+) characters', backend_logs)
            if char_match:
                ai_response_chars = int(char_match.group(1))
            
            # Look for truncation errors
            has_truncation_errors = any([
                "truncated" in backend_logs.lower(),
                "incomplete" in backend_logs.lower(),
                "cut off" in backend_logs.lower()
            ])
            
            return {
                "success_indicators_found": sum(success_indicators),
                "error_indicators_found": sum(error_indicators),
                "has_deployment_success": any(success_indicators),
                "has_deployment_errors": any(error_indicators),
                "ai_response_chars": ai_response_chars,
                "has_truncation_errors": has_truncation_errors,
                "logs_preview": backend_logs[-1500:] if backend_logs else "No logs found"
            }
            
        except Exception as e:
            logger.error(f"Could not check backend logs: {e}")
            return {
                "success_indicators_found": 0,
                "error_indicators_found": 0,
                "has_deployment_success": False,
                "has_deployment_errors": False,
                "ai_response_chars": None,
                "has_truncation_errors": False,
                "error": str(e)
            }

    async def run_netlify_deployment_test(self):
        """Run the complete Netlify deployment test"""
        logger.info("🚀 Starting Netlify Generation and Deployment Test")
        logger.info(f"Backend URL: {self.base_url}")
        
        start_time = time.time()
        validation_errors = []
        
        # Step 1: Create a test session
        logger.info("\n--- Step 1: Create Test Session ---")
        session_id = await self.create_session("Max Tokens Test")
        if not session_id:
            validation_errors.append("Failed to create test session")
            return self._generate_netlify_summary(start_time, validation_errors)
        
        # Step 2: Generate AND deploy website
        logger.info("\n--- Step 2: Generate and Deploy Website ---")
        deploy_result = await self.test_netlify_generate_and_deploy(session_id)
        
        if not deploy_result.get('success'):
            validation_errors.append(f"Generation and deployment failed: {deploy_result.get('error')}")
            return self._generate_netlify_summary(start_time, validation_errors)
        
        # Step 3: Verify response contains required fields and file completeness
        logger.info("\n--- Step 3: Verify Response Structure and File Completeness ---")
        project = deploy_result.get('project', {})
        deployment = deploy_result.get('deployment', {})
        deploy_preview_url = deploy_result.get('deploy_preview_url')
        
        # Check project fields
        if not project.get('project_id'):
            validation_errors.append("Response missing project.project_id")
        if not project.get('files'):
            validation_errors.append("Response missing project.files")
        else:
            files = project.get('files', {})
            expected_files = ['index.html', 'styles.css', 'app.js']
            for expected_file in expected_files:
                if expected_file not in files and not any(expected_file in f for f in files.keys()):
                    validation_errors.append(f"Missing expected file: {expected_file}")
            
            # CRITICAL CHECKS for max_tokens fix - verify files are COMPLETE
            html_content = None
            css_content = None
            js_content = None
            
            for filepath, content in files.items():
                if 'index.html' in filepath:
                    html_content = content
                elif 'styles.css' in filepath:
                    css_content = content
                elif 'app.js' in filepath:
                    js_content = content
            
            # Verify file sizes (max_tokens fix should produce substantial content)
            if html_content:
                html_chars = len(html_content)
                logger.info(f"HTML file size: {html_chars} characters")
                if html_chars < 5000:
                    validation_errors.append(f"HTML file too small ({html_chars} chars, minimum 5000)")
            else:
                validation_errors.append("HTML content not found in files")
            
            if css_content:
                css_chars = len(css_content)
                logger.info(f"CSS file size: {css_chars} characters")
                if css_chars < 2000:
                    validation_errors.append(f"CSS file too small ({css_chars} chars, minimum 2000)")
            else:
                validation_errors.append("CSS content not found in files")
            
            if js_content:
                js_chars = len(js_content)
                logger.info(f"JS file size: {js_chars} characters")
            
            # Check for truncation indicators in content
            if html_content and (html_content.endswith('...') or 'truncated' in html_content.lower()):
                validation_errors.append("HTML file appears to be truncated")
            if css_content and (css_content.endswith('...') or 'truncated' in css_content.lower()):
                validation_errors.append("CSS file appears to be truncated")
        
        # Check deployment fields
        if not deployment.get('site_id'):
            validation_errors.append("Response missing deployment.site_id")
        if not deployment.get('deploy_id'):
            validation_errors.append("Response missing deployment.deploy_id")
        if not deploy_preview_url:
            validation_errors.append("Response missing deploy_preview_url")
        
        # Check build status
        build_status = deployment.get('build_status', {})
        if build_status.get('state') != 'ready':
            validation_errors.append(f"Build status is not 'ready': {build_status.get('state')}")
        
        # Step 4: Verify Netlify URL format
        logger.info("\n--- Step 4: Verify Netlify URL Format ---")
        if deploy_preview_url:
            if not deploy_preview_url.startswith('https://'):
                validation_errors.append(f"Deploy URL is not HTTPS: {deploy_preview_url}")
            if '.netlify.app' not in deploy_preview_url:
                validation_errors.append(f"Deploy URL is not a Netlify URL: {deploy_preview_url}")
            
            logger.info(f"✅ Deploy Preview URL: {deploy_preview_url}")
        
        # Step 5: Test live URL accessibility
        logger.info("\n--- Step 5: Test Live URL Accessibility ---")
        url_test_result = None
        if deploy_preview_url:
            url_test_result = await self.test_live_url_accessibility(deploy_preview_url)
            
            if not url_test_result.get('success'):
                validation_errors.append(f"Live URL not accessible: {url_test_result.get('error')}")
            else:
                if url_test_result.get('status_code') != 200:
                    validation_errors.append(f"Live URL returned status {url_test_result.get('status_code')}")
                if not url_test_result.get('has_html'):
                    validation_errors.append("Live URL does not contain HTML content")
                if not url_test_result.get('has_renovation_content'):
                    validation_errors.append("Live URL does not contain expected renovation business content")
        
        # Step 6: Check backend logs for AI response and parsing
        logger.info("\n--- Step 6: Check Backend Logs for AI Response and Parsing ---")
        log_analysis = await self.check_backend_logs_for_deployment()
        
        # Check AI response character count (max_tokens fix verification)
        ai_response_chars = log_analysis.get('ai_response_chars')
        if ai_response_chars:
            logger.info(f"AI Response received: {ai_response_chars} characters")
            if ai_response_chars < 20000:
                validation_errors.append(f"AI response too small ({ai_response_chars} chars, expected >20,000)")
        else:
            validation_errors.append("No AI response character count found in logs")
        
        # Check for truncation and parsing errors
        if log_analysis.get('has_truncation_errors'):
            validation_errors.append("Backend logs show truncation errors")
        
        # Check deployment success/errors
        if not log_analysis.get('has_deployment_success'):
            validation_errors.append("Backend logs don't show deployment success messages")
        if log_analysis.get('has_deployment_errors'):
            validation_errors.append("Backend logs show deployment errors")
        
        # Generate final summary
        return self._generate_netlify_summary(start_time, validation_errors, {
            "session_id": session_id,
            "deploy_result": deploy_result,
            "url_test_result": url_test_result if deploy_preview_url else None,
            "log_analysis": log_analysis,
            "deploy_preview_url": deploy_preview_url
        })

    def _generate_netlify_summary(self, start_time: float, validation_errors: List[str], test_data: Dict[str, Any] = None):
        """Generate final Netlify test summary"""
        total_time = time.time() - start_time
        success = len(validation_errors) == 0
        
        logger.info("\n" + "="*80)
        logger.info("NETLIFY GENERATION AND DEPLOYMENT TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Overall Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        logger.info(f"Total Time: {total_time:.2f}s")
        logger.info(f"Validation Errors: {len(validation_errors)}")
        
        if test_data:
            logger.info(f"Session ID: {test_data.get('session_id')}")
            logger.info(f"Deploy Preview URL: {test_data.get('deploy_preview_url', 'N/A')}")
            
            deploy_result = test_data.get('deploy_result', {})
            if deploy_result.get('success'):
                logger.info(f"Generation Time: {deploy_result.get('generation_time', 0):.2f}s")
                project = deploy_result.get('project', {})
                deployment = deploy_result.get('deployment', {})
                logger.info(f"Project ID: {project.get('project_id', 'N/A')}")
                logger.info(f"Site ID: {deployment.get('site_id', 'N/A')}")
                logger.info(f"Deploy ID: {deployment.get('deploy_id', 'N/A')}")
                logger.info(f"Build Status: {deployment.get('build_status', {}).get('state', 'N/A')}")
        
        if validation_errors:
            logger.info("\nVALIDATION ERRORS:")
            for error in validation_errors:
                logger.error(f"❌ {error}")
        else:
            logger.info("\n✅ All validation criteria passed!")
            logger.info("   - Session created successfully")
            logger.info("   - Website generated and deployed to Netlify")
            logger.info("   - Response contains all required fields")
            logger.info("   - Deploy preview URL is valid Netlify URL")
            logger.info("   - Live URL is accessible and contains expected content")
            logger.info("   - Backend logs show deployment success")
        
        return {
            "success": success,
            "total_time": total_time,
            "validation_errors": validation_errors,
            "test_data": test_data or {}
        }

async def main():
    """Main test runner for Netlify Deployment System"""
    tester = NetlifyDeploymentTester()
    results = await tester.run_netlify_deployment_test()
    
    # Return exit code based on results
    if results['success']:
        logger.info("🎉 Netlify deployment test passed!")
        return 0
    else:
        logger.error(f"💥 Netlify deployment test failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
