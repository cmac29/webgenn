#!/usr/bin/env python3
"""
Simple File-Based Preview System Test
"""

import asyncio
import aiohttp
import json
import time
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_file_preview_system():
    """Test the file-based preview system"""
    
    # Configuration
    base_url = "https://webgen-ai-11.preview.emergentagent.com/api"
    test_session_id = "test-file-preview-simple"
    project_dir = Path(f"/app/backend/generated_projects/{test_session_id}")
    
    logger.info("🚀 Testing File-Based Preview System")
    logger.info(f"Session ID: {test_session_id}")
    
    # Clean up existing project
    if project_dir.exists():
        import shutil
        shutil.rmtree(project_dir)
        logger.info("🧹 Cleaned up existing test project")
    
    results = {
        "step1_generation": False,
        "step2_file_structure": False,
        "step3_html_linking": False,
        "step4_preview_endpoints": False,
        "step5_validation": False
    }
    
    # Step 1: Generate Website
    logger.info("\n📝 STEP 1: Generate Simple Website")
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "session_id": test_session_id,
                "prompt": "Create a simple landing page with a header, hero section, and footer",
                "model": "claude-sonnet-4",
                "framework": "html"
            }
            
            async with session.post(
                f"{base_url}/generate/website",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results["step1_generation"] = True
                    preview_url = data.get('preview_url')
                    logger.info(f"✅ Website generated successfully")
                    logger.info(f"   Preview URL: {preview_url}")
                else:
                    logger.error(f"❌ Generation failed: {response.status}")
        except Exception as e:
            logger.error(f"❌ Generation error: {e}")
    
    # Step 2: Verify File Structure
    logger.info("\n📁 STEP 2: Verify File Structure")
    expected_files = {
        "index.html": project_dir / "index.html",
        "styles.css": project_dir / "static" / "styles.css",
        "app.js": project_dir / "static" / "app.js"
    }
    
    all_files_exist = True
    for file_name, file_path in expected_files.items():
        if file_path.exists():
            size = file_path.stat().st_size
            logger.info(f"✅ Found {file_name}: {size} bytes")
        else:
            logger.error(f"❌ Missing {file_name}")
            all_files_exist = False
    
    results["step2_file_structure"] = all_files_exist
    
    # Step 3: Verify HTML Linking
    logger.info("\n🔗 STEP 3: Verify HTML Linking")
    html_path = project_dir / "index.html"
    if html_path.exists():
        html_content = html_path.read_text()
        css_link = '<link rel="stylesheet" href="static/styles.css">' in html_content
        js_script = '<script src="static/app.js"></script>' in html_content
        
        if css_link and js_script:
            results["step3_html_linking"] = True
            logger.info("✅ HTML contains proper CSS and JS links")
        else:
            logger.error(f"❌ HTML linking issues - CSS: {css_link}, JS: {js_script}")
    else:
        logger.error("❌ HTML file not found")
    
    # Step 4: Test Preview Endpoints
    logger.info("\n🌐 STEP 4: Test Preview Endpoints")
    endpoints = {
        "html": f"{base_url}/preview/{test_session_id}/",
        "css": f"{base_url}/preview/{test_session_id}/static/styles.css",
        "js": f"{base_url}/preview/{test_session_id}/static/app.js"
    }
    
    all_endpoints_ok = True
    async with aiohttp.ClientSession() as session:
        for name, url in endpoints.items():
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        logger.info(f"✅ {name.upper()} endpoint: 200 OK")
                    else:
                        logger.error(f"❌ {name.upper()} endpoint: {response.status}")
                        all_endpoints_ok = False
            except Exception as e:
                logger.error(f"❌ {name.upper()} endpoint error: {e}")
                all_endpoints_ok = False
    
    results["step4_preview_endpoints"] = all_endpoints_ok
    
    # Step 5: Final Validation
    logger.info("\n✅ STEP 5: Final Validation")
    validation_criteria = [
        ("Website generation completes", results["step1_generation"]),
        ("Files created on disk", results["step2_file_structure"]),
        ("HTML contains proper links", results["step3_html_linking"]),
        ("Preview endpoints return 200", results["step4_preview_endpoints"])
    ]
    
    all_passed = True
    for criterion, passed in validation_criteria:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {criterion}")
        if not passed:
            all_passed = False
    
    results["step5_validation"] = all_passed
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("FINAL SUMMARY")
    logger.info("="*60)
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    logger.info(f"Tests Passed: {passed_count}/{total_count}")
    
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED - File-based preview system is working!")
        return 0
    else:
        logger.error("💥 SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_file_preview_system())
    exit(exit_code)