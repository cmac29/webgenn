#!/usr/bin/env python3
"""
File-Based Preview System Test Suite
Tests the new professional file-based architecture for Code Weaver
"""

import asyncio
import aiohttp
import json
import time
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FilePreviewTester:
    def __init__(self):
        # Get backend URL from frontend .env
        self.base_url = self._get_backend_url()
        self.test_session_id = "test-file-preview-123"
        self.project_dir = Path(f"/app/backend/generated_projects/{self.test_session_id}")
        
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
    
    async def step1_generate_simple_website(self) -> Dict[str, Any]:
        """Step 1: Generate a Simple Website"""
        logger.info("\n" + "="*60)
        logger.info("STEP 1: GENERATE SIMPLE WEBSITE")
        logger.info("="*60)
        
        async with aiohttp.ClientSession() as session:
            try:
                payload = {
                    "session_id": self.test_session_id,
                    "prompt": "Create a simple landing page with a header, hero section, and footer",
                    "model": "claude-sonnet-4",
                    "framework": "html"
                }
                
                logger.info(f"🚀 Generating website with session_id: {self.test_session_id}")
                logger.info(f"   Prompt: {payload['prompt']}")
                logger.info(f"   Model: {payload['model']}")
                logger.info(f"   Framework: {payload['framework']}")
                
                start_time = time.time()
                
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
                            "status_code": response.status,
                            "generation_time": generation_time,
                            "website_id": data.get('website_id'),
                            "preview_url": data.get('preview_url'),
                            "html_content": data.get('html_content', ''),
                            "css_content": data.get('css_content', ''),
                            "js_content": data.get('js_content', ''),
                            "framework": data.get('framework'),
                            "files_count": len(data.get('files', []))
                        }
                        
                        logger.info(f"✅ Website generated successfully in {generation_time:.2f}s")
                        logger.info(f"   Website ID: {result['website_id']}")
                        logger.info(f"   Preview URL: {result['preview_url']}")
                        logger.info(f"   HTML length: {len(result['html_content'])} chars")
                        logger.info(f"   CSS length: {len(result['css_content'])} chars")
                        logger.info(f"   JS length: {len(result['js_content'])} chars")
                        logger.info(f"   Files count: {result['files_count']}")
                        
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Website generation failed: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "status_code": response.status,
                            "error": error_text,
                            "generation_time": generation_time
                        }
                        
            except Exception as e:
                logger.error(f"❌ Website generation error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
    
    def step2_verify_file_structure(self) -> Dict[str, Any]:
        """Step 2: Verify File Structure"""
        logger.info("\n" + "="*60)
        logger.info("STEP 2: VERIFY FILE STRUCTURE")
        logger.info("="*60)
        
        expected_files = {
            "index.html": self.project_dir / "index.html",
            "styles.css": self.project_dir / "static" / "styles.css",
            "app.js": self.project_dir / "static" / "app.js"
        }
        
        optional_files = {
            "server.py": self.project_dir / "backend" / "server.py",
            "requirements.txt": self.project_dir / "backend" / "requirements.txt"
        }
        
        result = {
            "success": True,
            "project_dir_exists": self.project_dir.exists(),
            "static_dir_exists": (self.project_dir / "static").exists(),
            "backend_dir_exists": (self.project_dir / "backend").exists(),
            "files_found": {},
            "files_missing": [],
            "file_sizes": {},
            "errors": []
        }
        
        logger.info(f"Checking project directory: {self.project_dir}")
        
        if not result["project_dir_exists"]:
            result["success"] = False
            result["errors"].append(f"Project directory does not exist: {self.project_dir}")
            logger.error(f"❌ Project directory not found: {self.project_dir}")
            return result
        
        # List actual directory contents
        try:
            logger.info("📁 Directory structure:")
            for root, dirs, files in os.walk(self.project_dir):
                level = root.replace(str(self.project_dir), '').count(os.sep)
                indent = ' ' * 2 * level
                logger.info(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    file_path = Path(root) / file
                    size = file_path.stat().st_size if file_path.exists() else 0
                    logger.info(f"{subindent}{file} ({size} bytes)")
        except Exception as e:
            logger.warning(f"Could not list directory contents: {e}")
        
        # Check expected files
        for file_name, file_path in expected_files.items():
            if file_path.exists():
                size = file_path.stat().st_size
                result["files_found"][file_name] = str(file_path)
                result["file_sizes"][file_name] = size
                logger.info(f"✅ Found {file_name}: {file_path} ({size} bytes)")
            else:
                result["files_missing"].append(file_name)
                result["success"] = False
                logger.error(f"❌ Missing {file_name}: {file_path}")
        
        # Check optional files
        for file_name, file_path in optional_files.items():
            if file_path.exists():
                size = file_path.stat().st_size
                result["files_found"][file_name] = str(file_path)
                result["file_sizes"][file_name] = size
                logger.info(f"✅ Found optional {file_name}: {file_path} ({size} bytes)")
            else:
                logger.info(f"ℹ️  Optional file not found: {file_name}")
        
        # Validate file sizes
        if "index.html" in result["files_found"] and result["file_sizes"]["index.html"] < 100:
            result["errors"].append(f"index.html is too small: {result['file_sizes']['index.html']} bytes")
            result["success"] = False
        
        if "styles.css" in result["files_found"] and result["file_sizes"]["styles.css"] < 10:
            result["errors"].append(f"styles.css is too small: {result['file_sizes']['styles.css']} bytes")
            result["success"] = False
        
        if result["success"]:
            logger.info("✅ File structure verification PASSED")
        else:
            logger.error("❌ File structure verification FAILED")
            for error in result["errors"]:
                logger.error(f"   - {error}")
        
        return result
    
    def step3_verify_html_linking(self) -> Dict[str, Any]:
        """Step 3: Verify HTML Linking"""
        logger.info("\n" + "="*60)
        logger.info("STEP 3: VERIFY HTML LINKING")
        logger.info("="*60)
        
        html_path = self.project_dir / "index.html"
        
        result = {
            "success": True,
            "html_exists": html_path.exists(),
            "css_link_found": False,
            "js_script_found": False,
            "css_link_correct": False,
            "js_script_correct": False,
            "html_content": "",
            "errors": []
        }
        
        if not result["html_exists"]:
            result["success"] = False
            result["errors"].append("index.html file not found")
            logger.error("❌ index.html file not found")
            return result
        
        try:
            # Read HTML content
            html_content = html_path.read_text(encoding='utf-8')
            result["html_content"] = html_content
            
            logger.info(f"📄 Reading HTML file: {html_path}")
            logger.info(f"   HTML length: {len(html_content)} characters")
            
            # Check for CSS link
            css_patterns = [
                '<link rel="stylesheet" href="static/styles.css">',
                '<link rel="stylesheet" href="static/styles.css"/>',
                'href="static/styles.css"'
            ]
            
            for pattern in css_patterns:
                if pattern in html_content:
                    result["css_link_found"] = True
                    if 'rel="stylesheet"' in pattern and 'static/styles.css' in pattern:
                        result["css_link_correct"] = True
                    break
            
            # Check for JS script
            js_patterns = [
                '<script src="static/app.js"></script>',
                'src="static/app.js"'
            ]
            
            for pattern in js_patterns:
                if pattern in html_content:
                    result["js_script_found"] = True
                    if 'static/app.js' in pattern:
                        result["js_script_correct"] = True
                    break
            
            # Log findings
            if result["css_link_found"]:
                logger.info("✅ CSS link found in HTML")
                if result["css_link_correct"]:
                    logger.info("✅ CSS link is correctly formatted")
                else:
                    logger.warning("⚠️  CSS link found but may not be correctly formatted")
            else:
                result["success"] = False
                result["errors"].append("CSS link not found in HTML")
                logger.error("❌ CSS link not found in HTML")
            
            if result["js_script_found"]:
                logger.info("✅ JS script tag found in HTML")
                if result["js_script_correct"]:
                    logger.info("✅ JS script tag is correctly formatted")
                else:
                    logger.warning("⚠️  JS script tag found but may not be correctly formatted")
            else:
                result["success"] = False
                result["errors"].append("JS script tag not found in HTML")
                logger.error("❌ JS script tag not found in HTML")
            
            # Show relevant HTML snippets
            logger.info("🔍 HTML head section:")
            head_start = html_content.find('<head>')
            head_end = html_content.find('</head>')
            if head_start != -1 and head_end != -1:
                head_content = html_content[head_start:head_end + 7]
                for line in head_content.split('\n')[:10]:  # Show first 10 lines
                    if line.strip():
                        logger.info(f"   {line.strip()}")
            
            logger.info("🔍 HTML body end section:")
            body_end = html_content.rfind('</body>')
            if body_end != -1:
                body_section = html_content[max(0, body_end - 200):body_end + 7]
                for line in body_section.split('\n')[-5:]:  # Show last 5 lines
                    if line.strip():
                        logger.info(f"   {line.strip()}")
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(f"Error reading HTML file: {str(e)}")
            logger.error(f"❌ Error reading HTML file: {e}")
        
        if result["success"]:
            logger.info("✅ HTML linking verification PASSED")
        else:
            logger.error("❌ HTML linking verification FAILED")
            for error in result["errors"]:
                logger.error(f"   - {error}")
        
        return result
    
    async def step4_test_preview_endpoints(self) -> Dict[str, Any]:
        """Step 4: Test Preview Endpoints"""
        logger.info("\n" + "="*60)
        logger.info("STEP 4: TEST PREVIEW ENDPOINTS")
        logger.info("="*60)
        
        endpoints = {
            "html": f"{self.base_url}/preview/{self.test_session_id}/",
            "css": f"{self.base_url}/preview/{self.test_session_id}/static/styles.css",
            "js": f"{self.base_url}/preview/{self.test_session_id}/static/app.js"
        }
        
        result = {
            "success": True,
            "endpoints_tested": {},
            "errors": []
        }
        
        async with aiohttp.ClientSession() as session:
            for endpoint_name, url in endpoints.items():
                logger.info(f"🌐 Testing {endpoint_name.upper()} endpoint: {url}")
                
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        endpoint_result = {
                            "url": url,
                            "status_code": response.status,
                            "content_type": response.headers.get('content-type', ''),
                            "content_length": response.headers.get('content-length', '0'),
                            "success": response.status == 200
                        }
                        
                        if response.status == 200:
                            # Read a small portion of content for validation
                            content = await response.text()
                            endpoint_result["content_preview"] = content[:200] + "..." if len(content) > 200 else content
                            endpoint_result["actual_content_length"] = len(content)
                            
                            logger.info(f"✅ {endpoint_name.upper()} endpoint: {response.status} OK")
                            logger.info(f"   Content-Type: {endpoint_result['content_type']}")
                            logger.info(f"   Content-Length: {endpoint_result['actual_content_length']} bytes")
                            
                            # Validate content type
                            expected_content_types = {
                                "html": "text/html",
                                "css": "text/css",
                                "js": "application/javascript"
                            }
                            
                            expected_type = expected_content_types.get(endpoint_name)
                            if expected_type and expected_type not in endpoint_result["content_type"]:
                                logger.warning(f"⚠️  Unexpected content-type for {endpoint_name}: {endpoint_result['content_type']}")
                            
                        else:
                            error_text = await response.text()
                            endpoint_result["error"] = error_text
                            result["success"] = False
                            result["errors"].append(f"{endpoint_name.upper()} endpoint failed: {response.status} - {error_text}")
                            logger.error(f"❌ {endpoint_name.upper()} endpoint: {response.status} - {error_text}")
                        
                        result["endpoints_tested"][endpoint_name] = endpoint_result
                        
                except Exception as e:
                    endpoint_result = {
                        "url": url,
                        "success": False,
                        "error": str(e)
                    }
                    result["endpoints_tested"][endpoint_name] = endpoint_result
                    result["success"] = False
                    result["errors"].append(f"{endpoint_name.upper()} endpoint error: {str(e)}")
                    logger.error(f"❌ {endpoint_name.upper()} endpoint error: {e}")
        
        if result["success"]:
            logger.info("✅ Preview endpoints test PASSED")
        else:
            logger.error("❌ Preview endpoints test FAILED")
            for error in result["errors"]:
                logger.error(f"   - {error}")
        
        return result
    
    def step5_validation_criteria(self, step1_result: Dict, step2_result: Dict, step3_result: Dict, step4_result: Dict) -> Dict[str, Any]:
        """Step 5: Final Validation Criteria"""
        logger.info("\n" + "="*60)
        logger.info("STEP 5: VALIDATION CRITERIA")
        logger.info("="*60)
        
        criteria = {
            "website_generation_completes": step1_result.get("success", False),
            "files_created_on_disk": step2_result.get("success", False),
            "html_contains_proper_links": step3_result.get("success", False),
            "css_file_non_empty": step2_result.get("file_sizes", {}).get("styles.css", 0) > 10,
            "js_file_exists": "app.js" in step2_result.get("files_found", {}),
            "preview_endpoints_return_200": step4_result.get("success", False),
            "response_includes_preview_url": bool(step1_result.get("preview_url"))
        }
        
        result = {
            "success": all(criteria.values()),
            "criteria": criteria,
            "summary": {},
            "recommendations": []
        }
        
        # Log each criterion
        for criterion, passed in criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"{status} - {criterion.replace('_', ' ').title()}")
        
        # Generate summary
        passed_count = sum(criteria.values())
        total_count = len(criteria)
        result["summary"] = {
            "passed": passed_count,
            "total": total_count,
            "success_rate": passed_count / total_count if total_count > 0 else 0
        }
        
        # Generate recommendations
        if not criteria["website_generation_completes"]:
            result["recommendations"].append("Fix website generation API endpoint")
        
        if not criteria["files_created_on_disk"]:
            result["recommendations"].append("Fix file saving mechanism in ProjectManager")
        
        if not criteria["html_contains_proper_links"]:
            result["recommendations"].append("Fix HTML linking in _link_external_files method")
        
        if not criteria["css_file_non_empty"]:
            result["recommendations"].append("Ensure CSS content is properly generated and saved")
        
        if not criteria["preview_endpoints_return_200"]:
            result["recommendations"].append("Fix preview endpoint routing and file serving")
        
        if not criteria["response_includes_preview_url"]:
            result["recommendations"].append("Ensure preview_url is included in generation response")
        
        logger.info(f"\n📊 VALIDATION SUMMARY:")
        logger.info(f"   Passed: {passed_count}/{total_count} ({result['summary']['success_rate']:.1%})")
        
        if result["success"]:
            logger.info("🎉 ALL VALIDATION CRITERIA PASSED!")
        else:
            logger.error("💥 SOME VALIDATION CRITERIA FAILED")
            logger.info("📋 Recommendations:")
            for rec in result["recommendations"]:
                logger.info(f"   - {rec}")
        
        return result
    
    async def run_complete_test(self) -> Dict[str, Any]:
        """Run the complete file-based preview system test"""
        logger.info("🚀 Starting File-Based Preview System Test")
        logger.info(f"Backend URL: {self.base_url}")
        logger.info(f"Test Session ID: {self.test_session_id}")
        
        start_time = time.time()
        
        # Clean up any existing test project
        if self.project_dir.exists():
            import shutil
            shutil.rmtree(self.project_dir)
            logger.info(f"🧹 Cleaned up existing test project: {self.project_dir}")
        
        # Run all test steps
        step1_result = await self.step1_generate_simple_website()
        step2_result = self.step2_verify_file_structure()
        step3_result = self.step3_verify_html_linking()
        step4_result = await self.step4_test_preview_endpoints()
        step5_result = self.step5_validation_criteria(step1_result, step2_result, step3_result, step4_result)
        
        total_time = time.time() - start_time
        
        # Final summary
        logger.info("\n" + "="*60)
        logger.info("FINAL TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Test Time: {total_time:.2f}s")
        logger.info(f"Overall Success: {'✅ PASS' if step5_result['success'] else '❌ FAIL'}")
        
        return {
            "overall_success": step5_result["success"],
            "total_time": total_time,
            "step1_generate_website": step1_result,
            "step2_verify_file_structure": step2_result,
            "step3_verify_html_linking": step3_result,
            "step4_test_preview_endpoints": step4_result,
            "step5_validation_criteria": step5_result
        }

async def main():
    """Main test runner"""
    tester = FilePreviewTester()
    results = await tester.run_complete_test()
    
    # Return exit code based on results
    if results['overall_success']:
        logger.info("🎉 File-based preview system test PASSED!")
        return 0
    else:
        logger.error("💥 File-based preview system test FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)