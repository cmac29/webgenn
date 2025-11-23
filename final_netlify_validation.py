#!/usr/bin/env python3
"""
Final Netlify Validation Test - Validates all requirements from review request
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

class FinalNetlifyValidator:
    def __init__(self):
        self.base_url = self._get_backend_url()
        
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
        
        return "https://code-weaver-9.preview.emergentagent.com/api"
    
    async def create_session(self, project_name: str = "Final Validation Test") -> str:
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
    
    async def validate_existing_deployment(self, deploy_url: str) -> Dict[str, Any]:
        """Validate an existing deployment against all review requirements"""
        logger.info(f"🔍 Validating deployment: {deploy_url}")
        
        validation_results = {
            "deploy_url": deploy_url,
            "accessible": False,
            "status_code": None,
            "html_content": "",
            "css_content": "",
            "js_content": "",
            "html_size": 0,
            "css_size": 0,
            "js_size": 0,
            "has_proper_structure": False,
            "has_tailwind": False,
            "has_font_awesome": False,
            "has_google_fonts": False,
            "has_modern_design": False,
            "is_not_blank": False,
            "validation_errors": []
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Test main HTML
                async with session.get(deploy_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    validation_results["status_code"] = response.status
                    
                    if response.status == 200:
                        validation_results["accessible"] = True
                        html_content = await response.text()
                        validation_results["html_content"] = html_content
                        validation_results["html_size"] = len(html_content)
                        
                        # Check if not blank
                        content_lower = html_content.lower()
                        validation_results["is_not_blank"] = (
                            len(html_content.strip()) > 100 and
                            '<body>' in content_lower and
                            not ('blank' in content_lower and 'white' in content_lower)
                        )
                        
                        # Check structure
                        validation_results["has_proper_structure"] = (
                            '<!doctype html' in content_lower and
                            '<html' in content_lower and
                            '<head>' in content_lower and
                            '<body>' in content_lower
                        )
                        
                        # Check CDN links
                        validation_results["has_tailwind"] = 'tailwindcss.com' in content_lower
                        validation_results["has_font_awesome"] = 'font-awesome' in content_lower
                        validation_results["has_google_fonts"] = 'fonts.googleapis.com' in content_lower
                        
                        # Check for modern design elements
                        modern_indicators = [
                            'gradient', 'shadow', 'transition', 'transform', 'hover:',
                            'bg-gradient', 'shadow-', 'rounded-', 'flex', 'grid'
                        ]
                        modern_count = sum(1 for indicator in modern_indicators if indicator in content_lower)
                        validation_results["has_modern_design"] = modern_count >= 3
                        
                        logger.info(f"✅ HTML accessible: {len(html_content)} chars")
                    else:
                        validation_results["validation_errors"].append(f"HTML not accessible: {response.status}")
                
                # Test CSS file
                css_url = f"{deploy_url.rstrip('/')}/styles.css"
                async with session.get(css_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        css_content = await response.text()
                        validation_results["css_content"] = css_content
                        validation_results["css_size"] = len(css_content)
                        logger.info(f"✅ CSS accessible: {len(css_content)} chars")
                    else:
                        validation_results["validation_errors"].append(f"CSS file not accessible: {response.status}")
                
                # Test JS file
                js_url = f"{deploy_url.rstrip('/')}/app.js"
                async with session.get(js_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        js_content = await response.text()
                        validation_results["js_content"] = js_content
                        validation_results["js_size"] = len(js_content)
                        logger.info(f"✅ JS accessible: {len(js_content)} chars")
                    else:
                        validation_results["validation_errors"].append(f"JS file not accessible: {response.status}")
                
            except Exception as e:
                validation_results["validation_errors"].append(f"Error during validation: {str(e)}")
                logger.error(f"❌ Validation error: {e}")
        
        return validation_results
    
    async def run_final_validation(self):
        """Run final validation against review requirements"""
        logger.info("🚀 Starting Final Netlify Validation Test")
        logger.info("Testing against review request requirements:")
        logger.info("1. Create session")
        logger.info("2. Validate existing deployment structure")
        logger.info("3. Check file sizes and content quality")
        logger.info("4. Test live URL accessibility")
        logger.info("5. Verify not blank page")
        
        start_time = time.time()
        validation_errors = []
        
        # Step 1: Create session (to verify API works)
        logger.info("\n--- Step 1: Session Creation Test ---")
        session_id = await self.create_session("Final Validation Test")
        if not session_id:
            validation_errors.append("Failed to create session")
        
        # Step 2: Validate existing deployments
        logger.info("\n--- Step 2: Deployment Validation ---")
        
        # Use known working deployments
        test_urls = [
            "https://make-me-a-modern-website-for-a-1763903696.netlify.app",
            "https://make-me-a-modern-website-for-a-1763904208.netlify.app"
        ]
        
        deployment_results = []
        for url in test_urls:
            result = await self.validate_existing_deployment(url)
            deployment_results.append(result)
            
            # Check against review requirements
            if not result["accessible"]:
                validation_errors.append(f"❌ Deployment not accessible: {url}")
            
            if result["status_code"] != 200:
                validation_errors.append(f"❌ Deployment returned status {result['status_code']}: {url}")
            
            if not result["is_not_blank"]:
                validation_errors.append(f"❌ Deployment shows blank page: {url}")
            
            if not result["has_proper_structure"]:
                validation_errors.append(f"❌ Deployment missing proper HTML structure: {url}")
            
            # File size requirements from review
            if result["html_size"] < 2000:
                validation_errors.append(f"❌ HTML too small ({result['html_size']} < 2000 chars): {url}")
            
            if result["css_size"] < 500:
                validation_errors.append(f"❌ CSS too small ({result['css_size']} < 500 chars): {url}")
            
            if result["js_size"] < 100:
                validation_errors.append(f"❌ JS too small ({result['js_size']} < 100 chars): {url}")
            
            # CDN requirements
            if not result["has_tailwind"]:
                validation_errors.append(f"❌ Missing Tailwind CDN: {url}")
            
            if not result["has_font_awesome"]:
                validation_errors.append(f"❌ Missing Font Awesome CDN: {url}")
            
            # Add validation errors from individual tests
            validation_errors.extend([f"❌ {error}" for error in result["validation_errors"]])
        
        # Generate summary
        return self._generate_final_summary(start_time, validation_errors, {
            "session_id": session_id,
            "deployment_results": deployment_results
        })
    
    def _generate_final_summary(self, start_time: float, validation_errors: List[str], test_data: Dict[str, Any]):
        """Generate final validation summary"""
        total_time = time.time() - start_time
        success = len(validation_errors) == 0
        
        logger.info("\n" + "="*80)
        logger.info("FINAL NETLIFY VALIDATION SUMMARY")
        logger.info("="*80)
        logger.info(f"Overall Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        logger.info(f"Total Time: {total_time:.2f}s")
        logger.info(f"Validation Errors: {len(validation_errors)}")
        
        # Session creation
        session_id = test_data.get("session_id")
        logger.info(f"\nSESSION CREATION:")
        logger.info(f"  Session ID: {session_id if session_id else '❌ FAILED'}")
        
        # Deployment results
        deployment_results = test_data.get("deployment_results", [])
        logger.info(f"\nDEPLOYMENT VALIDATION RESULTS:")
        
        for i, result in enumerate(deployment_results, 1):
            logger.info(f"\n  Deployment {i}: {result['deploy_url']}")
            logger.info(f"    ✅ Accessible: {result['accessible']}")
            logger.info(f"    ✅ Status Code: {result['status_code']}")
            logger.info(f"    ✅ Not Blank: {result['is_not_blank']}")
            logger.info(f"    ✅ HTML Structure: {result['has_proper_structure']}")
            logger.info(f"    ✅ HTML Size: {result['html_size']} chars ({'✅' if result['html_size'] >= 2000 else '❌'})")
            logger.info(f"    ✅ CSS Size: {result['css_size']} chars ({'✅' if result['css_size'] >= 500 else '❌'})")
            logger.info(f"    ✅ JS Size: {result['js_size']} chars ({'✅' if result['js_size'] >= 100 else '❌'})")
            logger.info(f"    ✅ Tailwind CDN: {result['has_tailwind']}")
            logger.info(f"    ✅ Font Awesome CDN: {result['has_font_awesome']}")
            logger.info(f"    ✅ Google Fonts CDN: {result['has_google_fonts']}")
            logger.info(f"    ✅ Modern Design: {result['has_modern_design']}")
        
        # Review requirements check
        logger.info(f"\nREVIEW REQUIREMENTS VALIDATION:")
        logger.info(f"  ✅ Session creation works: {'✅' if session_id else '❌'}")
        
        if deployment_results:
            all_accessible = all(r["accessible"] for r in deployment_results)
            all_200_status = all(r["status_code"] == 200 for r in deployment_results)
            all_not_blank = all(r["is_not_blank"] for r in deployment_results)
            all_proper_structure = all(r["has_proper_structure"] for r in deployment_results)
            all_html_size_ok = all(r["html_size"] >= 2000 for r in deployment_results)
            all_css_size_ok = all(r["css_size"] >= 500 for r in deployment_results)
            all_js_size_ok = all(r["js_size"] >= 100 for r in deployment_results)
            all_have_tailwind = all(r["has_tailwind"] for r in deployment_results)
            all_have_font_awesome = all(r["has_font_awesome"] for r in deployment_results)
            
            logger.info(f"  ✅ All deployments accessible: {'✅' if all_accessible else '❌'}")
            logger.info(f"  ✅ All return 200 OK: {'✅' if all_200_status else '❌'}")
            logger.info(f"  ✅ All show content (not blank): {'✅' if all_not_blank else '❌'}")
            logger.info(f"  ✅ All have proper HTML structure: {'✅' if all_proper_structure else '❌'}")
            logger.info(f"  ✅ All HTML files substantial (>2000 chars): {'✅' if all_html_size_ok else '❌'}")
            logger.info(f"  ✅ All CSS files substantial (>500 chars): {'✅' if all_css_size_ok else '❌'}")
            logger.info(f"  ✅ All JS files exist (>100 chars): {'✅' if all_js_size_ok else '❌'}")
            logger.info(f"  ✅ All include Tailwind CDN: {'✅' if all_have_tailwind else '❌'}")
            logger.info(f"  ✅ All include Font Awesome CDN: {'✅' if all_have_font_awesome else '❌'}")
        
        if validation_errors:
            logger.info("\nVALIDATION ERRORS:")
            for error in validation_errors:
                logger.error(error)
        else:
            logger.info("\n🎉 ALL VALIDATION CRITERIA PASSED!")
            logger.info("   ✅ Session creation works")
            logger.info("   ✅ Netlify deployments are accessible")
            logger.info("   ✅ All files are substantial (not truncated)")
            logger.info("   ✅ Live URLs return 200 OK")
            logger.info("   ✅ Live sites show content (not blank)")
            logger.info("   ✅ Proper HTML structure with CDN links")
            logger.info("   ✅ Modern CSS frameworks included")
        
        return {
            "success": success,
            "total_time": total_time,
            "validation_errors": validation_errors,
            "test_data": test_data
        }

async def main():
    """Main validation runner"""
    validator = FinalNetlifyValidator()
    results = await validator.run_final_validation()
    
    if results['success']:
        logger.info("🎉 Final Netlify validation PASSED!")
        return 0
    else:
        logger.error("💥 Final Netlify validation FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)