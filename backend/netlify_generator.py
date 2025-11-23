"""
Netlify Code Generation Service
Generates deployment-ready, serverless code for Netlify platform
"""
import os
import logging
import json
import re
from typing import Dict, Any, List, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import HTTPException
from design_knowledge_base import (
    FRAMEWORKS, 
    DESIGN_PRINCIPLES, 
    COMPONENT_PATTERNS, 
    ANIMATION_PATTERNS,
    WEBSITE_PATTERNS
)

logger = logging.getLogger(__name__)

class NetlifyGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def _get_model_config(self, model: str) -> tuple:
        """Map model ID to provider and model name"""
        model_map = {
            "claude-sonnet-4": ("anthropic", "claude-4-sonnet-20250514"),
            "gpt-5": ("openai", "gpt-5"),
            "gpt-5-mini": ("openai", "gpt-5-mini"),
            "gemini-2.5-pro": ("gemini", "gemini-2.5-pro")
        }
        return model_map.get(model, ("openai", "gpt-5"))
    
    async def generate_netlify_project(self, prompt: str, model: str = "gpt-5", current_project: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate a complete Netlify-compatible project
        
        Returns:
            Dict with structure:
            {
                "files": {
                    "index.html": "content",
                    "netlify.toml": "content",
                    "netlify/functions/api.js": "content",
                    ...
                },
                "deploy_config": {
                    "build_command": "npm run build",
                    "publish_dir": "dist",
                    "functions_dir": "netlify/functions"
                }
            }
        """
        provider, model_name = self._get_model_config(model)
        session_id = f"netlify_{os.urandom(8).hex()}"
        
        logger.info("🚀 NETLIFY PROJECT GENERATION")
        logger.info(f"   Model: {provider}/{model_name}")
        logger.info(f"   Prompt: {prompt}")
        
        # Determine if this is editing or new generation
        is_editing = current_project is not None and len(current_project.get("files", {})) > 0
        
        if is_editing:
            logger.info("📝 EDIT MODE: Modifying existing Netlify project")
            return await self._edit_netlify_project(prompt, current_project, provider, model_name, session_id)
        else:
            logger.info("🆕 NEW PROJECT: Creating from scratch")
            return await self._create_netlify_project(prompt, provider, model_name, session_id)
    
    async def _create_netlify_project(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, Any]:
        """Create a new Netlify project from scratch"""
        
        # Analyze user intent with detailed requirements extraction
        analysis = await self._analyze_project_requirements(prompt, provider, model, session_id)
        logger.info(f"📋 Project analysis: {json.dumps(analysis, indent=2)}")
        
        # Extract explicit requirements from prompt
        requirements = self._extract_requirements(prompt)
        logger.info(f"📝 Extracted requirements: {requirements}")
        
        # Generate comprehensive design knowledge for AI
        frameworks_info = self._format_frameworks_knowledge()
        design_info = self._format_design_knowledge()
        component_info = self._format_component_patterns()
        
        # Generate the system prompt for Netlify-compatible code with requirement completion
        requirements_json = json.dumps(requirements, indent=2)
        checklist_text = self._generate_requirement_checklist(requirements)
        
        system_prompt = """You are an ELITE full-stack developer with COMPREHENSIVE DESIGN KNOWLEDGE specializing in Netlify deployments.

🎯 MISSION: Generate production-ready, VISUALLY STUNNING, Netlify-compatible code that deploys instantly with Deploy Preview URLs.

⚠️ CRITICAL: You MUST implement EVERY SINGLE feature, section, and element explicitly requested by the user. Missing ANY requirement is UNACCEPTABLE.

🔍 REQUIREMENTS TRACKING:
The user has requested these specific items - YOU MUST INCLUDE ALL OF THEM:
""" + requirements_json + """

Before you finish, verify you've implemented EVERY item in the requirements list above.

═══════════════════════════════════════════════════════════════
CRITICAL NETLIFY REQUIREMENTS
═══════════════════════════════════════════════════════════════

1. **SERVERLESS ARCHITECTURE ONLY**
   - NO persistent servers (No Express.js, Flask, FastAPI)
   - ALL backend logic MUST be Netlify Functions
   - Functions go in `netlify/functions/` directory
   - Accessible via `/.netlify/functions/[function-name]`

2. **NETLIFY FUNCTIONS FORMAT** - Use exports.handler pattern

3. **BUILD CONFIGURATION**
   - Must include `netlify.toml` in project root
   - Standard build command: `npm run build` or static
   - Publish directory: `dist`, `build`, `out`, or `.` (for static sites)

4. **DATABASE INTEGRATION**
   - Use API-based databases: Supabase, FaunaDB, Firebase
   - Environment variables via process.env.VARIABLE_NAME
   - Include placeholder keys

5. **FRONTEND REQUIREMENTS - CRITICAL VISUAL DESIGN**
   - MUST use Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
   - OR use modern CSS with gradients, shadows, animations
   - Modern, responsive, pixel-perfect design
   - API calls to /.netlify/functions/[function-name]
   - No hardcoded backend URLs
   - Professional color schemes, typography, spacing
   - Hover effects, transitions, animations
   - Modern fonts from Google Fonts
   - Font Awesome icons (NOT emojis): <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

""" + frameworks_info + """

""" + design_info + """

""" + component_info + """

═══════════════════════════════════════════════════════════════
🎨 VISUAL DESIGN REQUIREMENTS - MANDATORY
═══════════════════════════════════════════════════════════════

1. **USE MODERN CSS FRAMEWORKS**:
   - Tailwind CSS (preferred): <script src="https://cdn.tailwindcss.com"></script>
   - OR Bootstrap 5: <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
   - OR modern custom CSS with gradients, shadows, animations

2. **PROFESSIONAL COLOR SCHEMES**:
   - Use color palettes from knowledge base above
   - Modern gradients (linear-gradient, radial-gradient)
   - Proper contrast ratios
   - Accent colors for CTAs
   - Dark mode friendly options

3. **TYPOGRAPHY**:
   - Google Fonts: <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap">
   - Font pairings from knowledge base
   - Proper font sizes and line heights
   - Clear hierarchy

4. **SPACING & LAYOUT**:
   - Generous whitespace
   - 8px grid system
   - Section padding: 80-120px vertical
   - Card padding: 24-40px
   - Use CSS Grid and Flexbox

5. **COMPONENTS WITH STYLE**:
   - Elevated cards with shadows
   - Gradient buttons with hover effects
   - Smooth transitions (0.3s ease)
   - Rounded corners (8-16px)
   - Professional icons from Font Awesome

6. **ANIMATIONS**:
   - Fade-in on scroll
   - Hover lift effects
   - Smooth scrolling
   - Micro-interactions
   - Loading states

7. **RESPONSIVE DESIGN**:
   - Mobile-first approach
   - Breakpoints: 640px, 768px, 1024px, 1280px
   - Flexible grids
   - Adaptive typography

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT REQUIREMENTS - CRITICAL
═══════════════════════════════════════════════════════════════

YOU MUST OUTPUT VALID JSON. The system has robust parsing to handle your response.

OUTPUT FORMAT:
{
  "files": {
    "index.html": "your complete HTML code here with CDN links and beautiful design",
    "styles.css": "your complete CSS code here - MINIMUM 500 lines with comprehensive styling",
    "app.js": "your complete JavaScript code here with interactivity",
    "netlify.toml": "[build]\\n  publish = \".\"\\n  functions = \"netlify/functions\""
  },
  "deploy_config": {
    "build_command": "",
    "publish_dir": ".",
    "functions_dir": "netlify/functions"
  }
}

IMPORTANT:
- Escape quotes in your code as \\"
- Escape newlines as \\n  
- Escape backslashes as \\\\
- Start response with {
- End response with }
- No markdown code blocks

The system can also extract files even if JSON has minor issues, so focus on generating COMPLETE, BEAUTIFUL code with ALL requested features.

═══════════════════════════════════════════════════════════════
"""
        
        # Build user prompt based on analysis
        needs_backend = analysis.get("needs_backend", False)
        needs_database = analysis.get("needs_database", False)
        framework = analysis.get("framework", "vanilla")
        
        requirements_json = json.dumps(requirements, indent=2)
        checklist = self._generate_requirement_checklist(requirements)
        features_str = ', '.join(analysis.get('features', []))
        
        user_prompt = """Generate a complete Netlify-deployable project for:

""" + f'"{prompt}"' + """

PROJECT SPECIFICATIONS:
- Type: """ + analysis.get('project_type', 'web app') + """
- Framework: """ + framework + """
- Backend Required: """ + str(needs_backend) + """
- Database Required: """ + str(needs_database) + """
- Features: """ + features_str + """

🚨 CRITICAL COMPLETENESS REQUIREMENTS:
You MUST include EVERY item mentioned in the prompt above. Read it carefully:

USER REQUESTED THESE SPECIFIC ITEMS:
""" + requirements_json + """

VERIFICATION CHECKLIST (Complete ALL items):
""" + checklist + """

GENERATE:
1. Frontend files (HTML/CSS/JS or React)
2. Netlify Functions (if backend needed)
3. netlify.toml configuration
4. package.json (if using npm)
5. README.md with setup instructions

IMPORTANT RULES:
- Use Netlify Functions for ALL backend logic
- API endpoints accessible via `/.netlify/functions/[name]`
- Include environment variable placeholders
- Make it production-ready and VISUALLY STUNNING
- MUST use modern CSS frameworks (Tailwind, Bootstrap) OR comprehensive custom CSS
- Use gradients, shadows, animations, hover effects
- Professional color schemes and typography
- Font Awesome icons (NOT emojis)
- Generous spacing and proper layout
- Ensure mobile responsiveness with media queries

🎨 VISUAL DESIGN CHECKLIST (ALL MANDATORY):
✅ Tailwind CSS OR Bootstrap CDN link in <head>
✅ Font Awesome CDN link for professional icons
✅ Google Fonts for modern typography
✅ Proper color palette (not just black text on white)
✅ Gradients and shadows for depth
✅ Hover effects on interactive elements
✅ Smooth transitions and animations
✅ Responsive breakpoints
✅ Professional spacing and layout
✅ Modern component designs (cards, buttons, forms)

⚠️ BEFORE SUBMITTING YOUR CODE:
Go through the verification checklist above and confirm EVERY item is present in your code.
If ANY item is missing (especially design elements), ADD IT NOW before responding.

🚨 OUTPUT FORMAT - EXTREMELY IMPORTANT:
Respond with ONLY valid JSON. NO explanations before or after.

Structure:
{
  "files": {
    "index.html": "your complete HTML with EMBEDDED <style> and <script> tags",
    "styles.css": "OPTIONAL: duplicate of the embedded CSS",
    "app.js": "OPTIONAL: duplicate of the embedded JavaScript",
    "netlify.toml": "[build]\\n  publish = \\".\\""
  },
  "deploy_config": {
    "build_command": "",
    "publish_dir": ".",
    "functions_dir": "netlify/functions"
  }
}

🚨 CRITICAL FILE STRUCTURE FOR NETLIFY:
Your HTML MUST have ALL styles and scripts EMBEDDED inside it:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Page Title</title>
    <!-- CDN links -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    
    <!-- EMBEDDED STYLES - MANDATORY -->
    <style>
        /* ALL your CSS code here */
        body { margin: 0; }
        /* ... all styles ... */
    </style>
</head>
<body>
    <!-- HTML content -->
    
    <!-- EMBEDDED JAVASCRIPT - MANDATORY -->
    <script>
        // ALL your JavaScript code here
        console.log('App loaded');
        // ... all JavaScript ...
    </script>
</body>
</html>
```

DO NOT reference external files like:
❌ <link rel="stylesheet" href="styles.css">
❌ <link rel="stylesheet" href="static/styles.css">
❌ <script src="app.js"></script>

The system will extract embedded styles/scripts into separate files automatically.

ESCAPING RULES:
- Replace " with \\"
- Replace newline with \\n
- Replace \\ with \\\\

The system has robust parsing and can extract files even from imperfect JSON.
Focus on generating COMPLETE, BEAUTIFUL code with ALL user requirements and EMBEDDED styles/scripts.

═══════════════════════════════════════════════════════════════
🚨 REQUIREMENT COMPLETION CHECKLIST - MANDATORY
═══════════════════════════════════════════════════════════════

Before submitting your code, verify EACH requirement is implemented:

""" + checklist_text + """

YOU MUST CHECK OFF EVERY ITEM. If any item is NOT implemented, add it now before responding.

REMEMBER: Beautiful design is great, but COMPLETENESS is mandatory. Every feature, section, element, and detail the user requested MUST be present in your code."""

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_prompt
            )
            chat.with_model(provider, model)
            
            response = await chat.send_message(UserMessage(text=user_prompt))
            logger.info(f"✅ AI Response received: {len(response)} characters")
            
            # Parse the JSON response
            project_data = self._parse_project_response(response)
            
            if not project_data.get("files"):
                logger.error("❌ CRITICAL: No files parsed from AI response")
                logger.error(f"❌ Response length: {len(response)}")
                logger.error(f"❌ Response starts: {response[:1000]}")
                
                # Try alternative text extraction as last resort
                logger.warning("Attempting alternative text extraction...")
                project_data = self._extract_files_from_text(response)
                
                if not project_data.get("files"):
                    logger.error("❌ PARSING COMPLETELY FAILED")
                    logger.error("This should NOT happen - AI should return valid JSON")
                    
                    # Save the failed response for debugging
                    with open("/tmp/failed_ai_response.txt", "w") as f:
                        f.write(response)
                    logger.error("Failed response saved to /tmp/failed_ai_response.txt")
                    
                    raise Exception("AI response parsing failed - check logs and /tmp/failed_ai_response.txt")
                else:
                    logger.warning(f"⚠️ Extracted {len(project_data['files'])} files from text (not JSON)")
            else:
                logger.info(f"✅ Successfully parsed {len(project_data['files'])} files from JSON response")
            
            # Validate Netlify requirements
            self._validate_netlify_project(project_data)
            
            # CRITICAL: Validate that all user requirements are met
            html_content = project_data.get("files", {}).get("index.html", "")
            validation = self._validate_requirements(html_content, requirements)
            
            logger.info("📊 Requirements validation:")
            logger.info(f"   Completeness: {validation['completeness_score']:.1f}%")
            logger.info(f"   Found: {len(validation['found_requirements'])} requirements")
            logger.info(f"   Missing: {len(validation['missing_requirements'])} requirements")
            
            if validation["missing_requirements"]:
                logger.warning("⚠️ Missing requirements detected:")
                for missing in validation["missing_requirements"]:
                    logger.warning(f"   - {missing}")
                
                # If more than 30% requirements missing, retry with enhanced prompt
                if validation["completeness_score"] < 70:
                    logger.error(f"❌ Completeness score too low ({validation['completeness_score']:.1f}%)")
                    logger.info("🔄 Retrying with enhanced prompt to include missing requirements...")
                    
                    # Retry with explicit missing requirements
                    retry_result = await self._retry_with_missing_requirements(
                        prompt, requirements, validation["missing_requirements"],
                        provider, model, session_id
                    )
                    
                    if retry_result:
                        return retry_result
            
            logger.info(f"✅ Netlify project ready with {len(project_data['files'])} files")
            return project_data
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Budget errors - raise
            if "budget" in error_msg or "exceeded" in error_msg:
                logger.error(f"❌ BUDGET ERROR: {str(e)}")
                raise HTTPException(status_code=402, detail=f"API budget exceeded: {str(e)}")
            
            # Parsing errors - DO NOT FALLBACK, raise the error
            if "parsing failed" in error_msg or "ai response parsing" in error_msg:
                logger.error(f"❌ PARSING ERROR: {str(e)}")
                logger.error("Check /tmp/failed_ai_response.txt for the response")
                raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {str(e)}")
            
            # Other genuine errors - also raise
            logger.error(f"❌ Generation failed with error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    
    async def _edit_netlify_project(self, prompt: str, current_project: Dict, provider: str, model: str, session_id: str) -> Dict[str, Any]:
        """Edit an existing Netlify project"""
        
        current_files = current_project.get("files", {})
        logger.info(f"Editing project with {len(current_files)} existing files")
        
        # Extract what user wants to change/add
        edit_requirements = self._extract_requirements(prompt)
        logger.info(f"📝 Edit requirements: {edit_requirements}")
        
        edit_requirements_json = json.dumps(edit_requirements, indent=2)
        edit_checklist = self._generate_requirement_checklist(edit_requirements)
        
        system_prompt = f"""You are an expert full-stack developer editing a Netlify-deployed project.

🔄 EDITING MODE - PRESERVE EXISTING STRUCTURE + ADD NEW REQUIREMENTS

USER WANTS TO MAKE THESE CHANGES:
{edit_requirements_json}

CRITICAL RULES:
1. You are EDITING existing code, NOT creating from scratch
2. PRESERVE all existing files unless explicitly asked to remove them
3. ADD/MODIFY the specific items user requested
4. Make SURGICAL changes - only modify what's requested
5. Maintain Netlify Functions format and structure
6. Keep netlify.toml configuration unless changes are needed
7. Return the COMPLETE project with modifications

⚠️ VERIFICATION CHECKLIST FOR EDITS:
{edit_checklist}

EVERY item above MUST be present in your edited code. Check before submitting.

OUTPUT FORMAT: JSON with same structure as creation, but with edited files.
"""
        
        # Build context with current files
        files_context = "\n".join([
            f"=== {path} ({len(content)} chars) ===\n{content[:500]}..." 
            for path, content in list(current_files.items())[:10]
        ])
        
        user_prompt = f"""Edit this Netlify project:

USER'S EDIT REQUEST:
{prompt}

CURRENT PROJECT FILES:
{files_context}

INSTRUCTIONS:
1. Analyze what the user wants to change
2. Modify ONLY the affected files
3. Preserve all other files exactly as they are
4. Return the complete project JSON with edits applied

Ensure the edited project remains Netlify-compatible!"""

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_prompt
            )
            chat.with_model(provider, model)
            
            response = await chat.send_message(UserMessage(text=user_prompt))
            logger.info(f"✅ Edit response received: {len(response)} characters")
            
            # Parse edited project
            edited_project = self._parse_project_response(response)
            
            if not edited_project.get("files"):
                logger.warning("Could not parse edited project from response")
                logger.info("Attempting alternative extraction...")
                edited_project = self._extract_files_from_text(response)
                
                if not edited_project.get("files"):
                    logger.error("❌ Edit failed - could not extract files")
                    logger.warning("Returning original project unchanged")
                    return current_project
                else:
                    logger.info(f"✅ Extracted {len(edited_project['files'])} files from text")
            
            logger.info(f"✅ Edit complete: {len(edited_project['files'])} files")
            return edited_project
            
        except Exception as e:
            error_msg = str(e).lower()
            if "budget" in error_msg or "exceeded" in error_msg:
                logger.error(f"❌ BUDGET ERROR during edit: {str(e)}")
                raise HTTPException(status_code=402, detail=f"API budget exceeded: {str(e)}")
            
            logger.error(f"❌ Edit failed: {str(e)}")
            logger.warning("Returning original project unchanged")
            return current_project
    
    async def _retry_with_missing_requirements(
        self, 
        original_prompt: str,
        requirements: Dict[str, List[str]],
        missing_requirements: List[str],
        provider: str,
        model: str,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retry generation with explicit focus on missing requirements
        """
        logger.info("🔄 RETRY: Adding missing requirements to generation")
        
        missing_list = "\n".join([f"- {req}" for req in missing_requirements])
        
        enhanced_prompt = f"""CRITICAL RETRY - MISSING REQUIREMENTS DETECTED

Original request: {original_prompt}

YOU FAILED TO INCLUDE THESE REQUIRED ITEMS:
{missing_list}

Generate a COMPLETE project that includes:
1. Everything from the original request
2. SPECIFICALLY add all the missing items listed above

This is your LAST CHANCE to get it right. Include EVERY requirement."""

        retry_system = """You are an expert developer who NEVER misses requirements.

Your previous attempt was INCOMPLETE. You MUST now generate code that includes EVERY SINGLE requirement.

Focus especially on the missing items, but don't remove anything you already had."""

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"{session_id}_retry",
                system_message=retry_system
            )
            chat.with_model(provider, model)
            
            response = await chat.send_message(UserMessage(text=enhanced_prompt))
            logger.info(f"✅ Retry response received: {len(response)} characters")
            
            project_data = self._parse_project_response(response)
            
            if project_data.get("files"):
                # Validate retry attempt
                html_content = project_data.get("files", {}).get("index.html", "")
                retry_validation = self._validate_requirements(html_content, requirements)
                
                logger.info(f"📊 Retry validation: {retry_validation['completeness_score']:.1f}%")
                
                if retry_validation["completeness_score"] > 70:
                    logger.info("✅ Retry successful! Completeness improved.")
                    return project_data
                else:
                    logger.warning("⚠️ Retry still incomplete. Proceeding with best effort.")
                    return project_data
            
        except Exception as e:
            logger.error(f"Retry failed: {str(e)}")
        
        return None
    
    async def _analyze_project_requirements(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, Any]:
        """Analyze what the user wants to build"""
        
        analysis_prompt = f"""Analyze this project request and extract requirements:

"{prompt}"

Respond with JSON:
{{
  "project_type": "landing_page|web_app|dashboard|e_commerce|blog|portfolio",
  "framework": "react|nextjs|vanilla",
  "needs_backend": true|false,
  "needs_database": true|false,
  "features": ["contact_form", "user_auth", "api_integration", etc],
  "database_type": "supabase|faunadb|firebase|none"
}}"""

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"{session_id}_analysis",
                system_message="You are a project requirements analyzer. Respond ONLY with valid JSON."
            )
            chat.with_model(provider, model)
            
            response = await chat.send_message(UserMessage(text=analysis_prompt))
            
            # Extract JSON from response
            json_match = response[response.find("{"):response.rfind("}")+1]
            return json.loads(json_match)
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            # Return default analysis
            return {
                "project_type": "web_app",
                "framework": "vanilla",
                "needs_backend": False,
                "needs_database": False,
                "features": [],
                "database_type": "none"
            }
    
    def _parse_project_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response to extract project structure"""
        try:
            # Log first 500 chars of response for debugging
            logger.info(f"Response preview: {response[:500]}")
            
            # Strip any leading/trailing whitespace
            response = response.strip()
            
            # SMART APPROACH: Try multiple parsing strategies
            
            # Strategy 1: Try standard JSON parsing
            if response.startswith('{'):
                logger.info("✅ Response starts with JSON object")
                
                try:
                    project_data = json.loads(response)
                    
                    if "files" in project_data and isinstance(project_data["files"], dict):
                        logger.info(f"✅ Standard JSON parse successful: {len(project_data['files'])} files")
                        return self._process_files(project_data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Standard JSON parse failed: {str(e)}")
                    logger.info("Trying alternative extraction methods...")
            
            # Strategy 2: Extract using regex for file blocks
            logger.info("Attempting regex-based file extraction...")
            files = self._extract_files_with_regex(response)
            
            if files:
                logger.info(f"✅ Regex extraction successful: {len(files)} files")
                return {
                    "files": files,
                    "deploy_config": {
                        "build_command": "",
                        "publish_dir": ".",
                        "functions_dir": "netlify/functions",
                        "environment_variables": {}
                    }
                }
            
            # Strategy 3: Try the old text extraction
            logger.info("Attempting text-based extraction...")
            return self._extract_files_from_text(response)
            
            # Fallback: Try to find JSON block within response
            json_start = response.find('{"files"')
            if json_start < 0:
                json_start = response.find('{')
            
            if json_start < 0:
                logger.error("No JSON block found in response")
                logger.info(f"Response length: {len(response)}, starts with: {response[:200]}")
                return {}
            
            json_end = response.rfind("}") + 1
            
            if json_end <= json_start:
                logger.error("Invalid JSON boundaries")
                return {}
            
            json_str = response[json_start:json_end]
            logger.info(f"Attempting to parse JSON substring of length: {len(json_str)}")
            
            # Try parsing
            project_data = json.loads(json_str)
            
            # Validate structure
            if "files" in project_data and isinstance(project_data["files"], dict):
                logger.info(f"✅ Valid project structure with {len(project_data['files'])} files")
                return project_data
            else:
                logger.warning("JSON parsed but missing 'files' key or invalid structure")
                logger.info(f"Keys found: {list(project_data.keys())}")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            logger.error(f"Error at position {e.pos}")
            if 'json_str' in locals():
                logger.error(f"Context: ...{json_str[max(0, e.pos-50):min(len(json_str), e.pos+50)]}...")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {str(e)}")
            return {}
    
    def _extract_requirements(self, prompt: str) -> Dict[str, List[str]]:
        """
        Extract explicit requirements from user prompt
        Returns categorized list of what user asked for
        """
        requirements = {
            "sections": [],
            "features": [],
            "elements": [],
            "styling": [],
            "content": [],
            "functionality": []
        }
        
        prompt_lower = prompt.lower()
        
        # Common section keywords
        section_keywords = [
            "hero", "header", "footer", "navbar", "navigation", "menu",
            "about", "features", "pricing", "testimonials", "gallery",
            "contact", "form", "blog", "portfolio", "services", "team",
            "faq", "banner", "sidebar", "carousel", "slider"
        ]
        
        # Feature keywords
        feature_keywords = [
            "search", "filter", "authentication", "login", "signup",
            "cart", "checkout", "payment", "subscribe", "newsletter",
            "social", "share", "comment", "rating", "review"
        ]
        
        # Element keywords
        element_keywords = [
            "button", "link", "image", "video", "icon", "card",
            "modal", "popup", "dropdown", "tooltip", "badge",
            "alert", "notification", "progress", "spinner"
        ]
        
        # Extract sections
        for keyword in section_keywords:
            if keyword in prompt_lower:
                requirements["sections"].append(keyword)
        
        # Extract features
        for keyword in feature_keywords:
            if keyword in prompt_lower:
                requirements["features"].append(keyword)
        
        # Extract elements
        for keyword in element_keywords:
            if keyword in prompt_lower:
                requirements["elements"].append(keyword)
        
        # Look for numbered lists or bullet points
        import re
        
        # Find numbered requirements (1. 2. 3.)
        numbered = re.findall(r'\d+\.\s*([^\n]+)', prompt)
        if numbered:
            requirements["content"].extend(numbered)
        
        # Find bullet points (- or *)
        bullets = re.findall(r'[-*]\s*([^\n]+)', prompt)
        if bullets:
            requirements["content"].extend(bullets)
        
        # Extract specific counts (e.g., "3 cards", "5 testimonials")
        counts = re.findall(r'(\d+)\s+([a-zA-Z]+)', prompt)
        for count, item in counts:
            requirements["content"].append(f"{count} {item}")
        
        # Extract quoted text (specific content requested)
        quoted = re.findall(r'["\']([^"\']+)["\']', prompt)
        if quoted:
            requirements["content"].extend(quoted)
        
        # If no specific requirements found, parse the whole prompt
        if not any(requirements.values()):
            # Split by common separators
            parts = re.split(r'[,;]|\s+with\s+|\s+and\s+|\s+including\s+', prompt)
            requirements["content"] = [p.strip() for p in parts if len(p.strip()) > 3]
        
        return requirements
    
    def _generate_requirement_checklist(self, requirements: Dict[str, List[str]]) -> str:
        """Generate a checklist string from requirements"""
        checklist = []
        
        if requirements["sections"]:
            checklist.append("SECTIONS TO INCLUDE:")
            for section in requirements["sections"]:
                checklist.append(f"  ☐ {section.title()} section")
        
        if requirements["features"]:
            checklist.append("\nFEATURES TO IMPLEMENT:")
            for feature in requirements["features"]:
                checklist.append(f"  ☐ {feature.title()} functionality")
        
        if requirements["elements"]:
            checklist.append("\nELEMENTS TO ADD:")
            for element in requirements["elements"]:
                checklist.append(f"  ☐ {element.title()} elements")
        
        if requirements["content"]:
            checklist.append("\nSPECIFIC CONTENT REQUESTED:")
            for content in requirements["content"]:
                checklist.append(f"  ☐ {content}")
        
        if not checklist:
            checklist.append("☐ Implement all features described in the prompt")
        
        return "\n".join(checklist)
    
    def _validate_requirements(self, generated_html: str, requirements: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Validate that generated HTML contains all requested requirements
        Returns validation report
        """
        html_lower = generated_html.lower()
        
        validation_report = {
            "all_requirements_met": True,
            "missing_requirements": [],
            "found_requirements": [],
            "completeness_score": 0.0
        }
        
        total_requirements = 0
        found_requirements = 0
        
        # Check sections
        for section in requirements.get("sections", []):
            total_requirements += 1
            # Look for section in HTML (as class, id, or text)
            if section.lower() in html_lower:
                found_requirements += 1
                validation_report["found_requirements"].append(f"Section: {section}")
            else:
                validation_report["missing_requirements"].append(f"Section: {section}")
        
        # Check features
        for feature in requirements.get("features", []):
            total_requirements += 1
            if feature.lower() in html_lower:
                found_requirements += 1
                validation_report["found_requirements"].append(f"Feature: {feature}")
            else:
                validation_report["missing_requirements"].append(f"Feature: {feature}")
        
        # Check elements
        for element in requirements.get("elements", []):
            total_requirements += 1
            if element.lower() in html_lower:
                found_requirements += 1
                validation_report["found_requirements"].append(f"Element: {element}")
            else:
                validation_report["missing_requirements"].append(f"Element: {element}")
        
        # Check specific content
        for content in requirements.get("content", []):
            total_requirements += 1
            # More lenient check for content - look for key words
            content_words = content.lower().split()
            if any(word in html_lower for word in content_words if len(word) > 3):
                found_requirements += 1
                validation_report["found_requirements"].append(f"Content: {content}")
            else:
                validation_report["missing_requirements"].append(f"Content: {content}")
        
        # Calculate completeness
        if total_requirements > 0:
            validation_report["completeness_score"] = (found_requirements / total_requirements) * 100
        else:
            validation_report["completeness_score"] = 100.0
        
        validation_report["all_requirements_met"] = len(validation_report["missing_requirements"]) == 0
        
        return validation_report
    
    def _process_files(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process files - decode base64 if needed"""
        if "files" not in project_data:
            return project_data
        
        decoded_files = {}
        for filepath, content in project_data["files"].items():
            if isinstance(content, str):
                # Try to decode from base64
                try:
                    import base64
                    decoded_content = base64.b64decode(content).decode('utf-8')
                    decoded_files[filepath] = decoded_content
                    logger.info(f"✅ Decoded {filepath} from base64")
                except Exception:
                    # Not base64, use as-is
                    decoded_files[filepath] = content
            else:
                decoded_files[filepath] = content
        
        project_data["files"] = decoded_files
        return project_data
    
    def _extract_files_with_regex(self, response: str) -> Dict[str, str]:
        """
        Extract files using regex patterns when JSON parsing fails
        Handles BOTH escaped JSON strings AND raw unescaped content
        """
        files = {}
        
        try:
            import re
            
            # Strategy 1: Try to extract from properly escaped JSON
            # Pattern: "filename.ext": "escaped content"
            pattern = r'"([^"]+\.(html|css|js|toml|md|txt))"\s*:\s*"'
            matches = list(re.finditer(pattern, response, re.IGNORECASE))
            
            logger.info(f"Found {len(matches)} file pattern matches")
            
            for match in matches:
                filename = match.group(1)
                start_pos = match.end()  # Position after the opening quote of content
                
                # Find the closing quote (accounting for escaped quotes)
                content_end = self._find_closing_quote(response, start_pos)
                
                if content_end > start_pos:
                    raw_content = response[start_pos:content_end]
                    
                    # Unescape the content
                    unescaped_content = raw_content.replace('\\n', '\n')
                    unescaped_content = unescaped_content.replace('\\"', '"')
                    unescaped_content = unescaped_content.replace('\\\\', '\\')
                    unescaped_content = unescaped_content.replace('\\t', '\t')
                    
                    files[filename] = unescaped_content
                    logger.info(f"✅ Extracted {filename} ({len(unescaped_content)} chars)")
            
            # Strategy 2: If that didn't work, try extracting raw content
            # The AI might be outputting: "index.html": <!DOCTYPE html>...
            # Instead of: "index.html": "<!DOCTYPE html>..."
            if not files:
                logger.info("Strategy 1 failed, trying raw content extraction...")
                files = self._extract_raw_content(response)
            
            # Strategy 3: If we have HTML but no separate CSS/JS, extract embedded content
            if files and 'index.html' in files and ('styles.css' not in files or 'app.js' not in files):
                logger.info("Found HTML-only, extracting embedded CSS and JS...")
                files = self._extract_embedded_content(files)
            
        except Exception as e:
            logger.error(f"Regex extraction error: {str(e)}")
        
        return files
    
    def _extract_raw_content(self, response: str) -> Dict[str, str]:
        """
        Extract files when AI outputs raw content without proper JSON escaping
        Example: "index.html": <!DOCTYPE html>... instead of "index.html": "<!DOCTYPE..."
        """
        files = {}
        
        try:
            import re
            
            # Look for: "filename.ext": followed by content (not in quotes)
            # We need to find where the file starts and where it ends
            
            # Pattern to find file declarations
            pattern = r'"(index\.html|styles\.css|app\.js|script\.js|netlify\.toml|README\.md)"\s*:\s*'
            matches = list(re.finditer(pattern, response, re.IGNORECASE))
            
            logger.info(f"Found {len(matches)} raw content patterns")
            
            for i, match in enumerate(matches):
                filename = match.group(1)
                content_start = match.end()
                
                # Find where this file's content ends
                # It ends at the next file declaration or at a closing brace
                if i < len(matches) - 1:
                    content_end = matches[i + 1].start()
                else:
                    # Last file - find the closing of the files object
                    # Look for }, or }\n}
                    closing_pattern = r',?\s*\}[\s\n]*\}?'
                    closing_match = re.search(closing_pattern, response[content_start:])
                    if closing_match:
                        content_end = content_start + closing_match.start()
                    else:
                        content_end = len(response)
                
                # Extract the content
                raw_content = response[content_start:content_end].strip()
                
                # Remove trailing commas and quotes
                raw_content = raw_content.rstrip(',').strip()
                if raw_content.startswith('"') and raw_content.endswith('"'):
                    raw_content = raw_content[1:-1]
                
                # Unescape if needed
                if '\\n' in raw_content or '\\"' in raw_content:
                    raw_content = raw_content.replace('\\n', '\n')
                    raw_content = raw_content.replace('\\"', '"')
                    raw_content = raw_content.replace('\\\\', '\\')
                
                if raw_content and len(raw_content) > 50:  # Minimum content length
                    files[filename] = raw_content
                    logger.info(f"✅ Extracted {filename} ({len(raw_content)} chars) via raw extraction")
            
        except Exception as e:
            logger.error(f"Raw content extraction error: {str(e)}")
        
        return files
    
    def _extract_embedded_content(self, files: Dict[str, str]) -> Dict[str, str]:
        """
        Extract embedded <style> and <script> tags from HTML and create separate files
        """
        if 'index.html' not in files:
            return files
        
        html = files['index.html']
        extracted_files = files.copy()
        
        try:
            import re
            
            # Extract CSS from <style> tags
            if 'styles.css' not in files:
                style_pattern = r'<style[^>]*>(.*?)</style>'
                style_matches = re.findall(style_pattern, html, re.DOTALL | re.IGNORECASE)
                
                if style_matches:
                    css_content = '\n\n'.join(style_matches)
                    extracted_files['styles.css'] = css_content
                    logger.info(f"✅ Extracted CSS from <style> tags ({len(css_content)} chars)")
                    
                    # Remove <style> tags from HTML and add <link>
                    html = re.sub(style_pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
                    
                    # Add link to external CSS if not present
                    if 'href="styles.css"' not in html and "href='styles.css'" not in html:
                        # Insert after <head> tag
                        html = html.replace('</head>', '    <link rel="stylesheet" href="styles.css">\n</head>')
            
            # Extract JavaScript from <script> tags (excluding external scripts)
            if 'app.js' not in files and 'script.js' not in files:
                # Match script tags that don't have src attribute
                script_pattern = r'<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>'
                script_matches = re.findall(script_pattern, html, re.DOTALL | re.IGNORECASE)
                
                if script_matches:
                    js_content = '\n\n'.join(script_matches)
                    extracted_files['app.js'] = js_content
                    logger.info(f"✅ Extracted JavaScript from <script> tags ({len(js_content)} chars)")
                    
                    # Remove inline scripts from HTML and add external script
                    html = re.sub(script_pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
                    
                    # Add script tag before </body> if not present
                    if 'src="app.js"' not in html and "src='app.js'" not in html:
                        html = html.replace('</body>', '    <script src="app.js"></script>\n</body>')
            
            # Update HTML in files
            extracted_files['index.html'] = html
            
        except Exception as e:
            logger.error(f"Error extracting embedded content: {str(e)}")
        
        return extracted_files
    
    def _find_closing_quote(self, text: str, start_pos: int) -> int:
        """Find the closing quote position, handling escaped quotes"""
        i = start_pos
        while i < len(text):
            if text[i] == '"':
                # Check if it's escaped
                num_backslashes = 0
                j = i - 1
                while j >= start_pos and text[j] == '\\':
                    num_backslashes += 1
                    j -= 1
                
                # If even number of backslashes (or zero), this quote is not escaped
                if num_backslashes % 2 == 0:
                    return i
            i += 1
        
        return -1
    
    def _extract_files_from_text(self, response: str) -> Dict[str, Any]:
        """
        Extract files from text response when JSON parsing fails
        Looks for code blocks and file markers
        """
        files = {}
        
        # Try to find file markers like "index.html:", "styles.css:", etc.
        file_pattern = r'([a-zA-Z0-9_\-/\.]+\.(html|css|js|toml|json|md)):\s*```([a-z]*)\n(.*?)```'
        matches = re.finditer(file_pattern, response, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            filename = match.group(1)
            content = match.group(4).strip()
            files[filename] = content
            logger.info(f"Extracted file: {filename} ({len(content)} chars)")
        
        if files:
            return {
                "files": files,
                "deploy_config": {
                    "build_command": "",
                    "publish_dir": ".",
                    "functions_dir": "netlify/functions",
                    "environment_variables": {}
                }
            }
        
        return {}
    
    def _validate_netlify_project(self, project: Dict[str, Any]) -> bool:
        """Validate that project meets Netlify requirements"""
        files = project.get("files", {})
        
        # Check for netlify.toml
        if "netlify.toml" not in files:
            logger.warning("Missing netlify.toml - adding default")
            files["netlify.toml"] = self._generate_default_netlify_toml()
        
        # Check for package.json if using Node/React
        has_js_files = any(f.endswith('.jsx') or f.endswith('.tsx') for f in files.keys())
        if has_js_files and "package.json" not in files:
            logger.warning("Missing package.json - adding default")
            files["package.json"] = self._generate_default_package_json()
        
        return True
    
    def _generate_default_netlify_toml(self) -> str:
        """Generate a default netlify.toml configuration"""
        return """[build]
  publish = "."
  functions = "netlify/functions"

[[redirects]]
  from = "/api/*"
  to = "/.netlify/functions/:splat"
  status = 200
"""
    
    def _generate_default_package_json(self) -> str:
        """Generate a default package.json"""
        return json.dumps({
            "name": "netlify-project",
            "version": "1.0.0",
            "scripts": {
                "build": "echo 'No build step required for static site'"
            },
            "dependencies": {}
        }, indent=2)
    
    def _generate_fallback_project(self, prompt: str, analysis: Dict) -> Dict[str, Any]:
        """Generate a simple fallback project if AI generation fails"""
        logger.warning("Using fallback project generation")
        
        project_name = analysis.get("project_type", "web-app").replace("_", "-")
        
        return {
            "files": {
                "index.html": self._get_fallback_html(prompt),
                "styles.css": self._get_fallback_css(),
                "app.js": self._get_fallback_js(),
                "netlify.toml": self._generate_default_netlify_toml(),
                "README.md": f"# {project_name.title()}\n\nGenerated by Code Weaver for Netlify deployment.\n\n## Deploy\n\nDeploy to Netlify for instant live preview!"
            },
            "deploy_config": {
                "build_command": "",
                "publish_dir": ".",
                "functions_dir": "netlify/functions",
                "environment_variables": {}
            }
        }
    
    
    def _format_frameworks_knowledge(self) -> str:
        """Format comprehensive framework knowledge for AI"""
        output = ["═══════════════════════════════════════════════════════════════"]
        output.append("📚 COMPREHENSIVE FRAMEWORK & LIBRARY ACCESS")
        output.append("═══════════════════════════════════════════════════════════════\n")
        
        # CSS Frameworks
        output.append("**CSS FRAMEWORKS:**")
        for name, info in FRAMEWORKS['css_frameworks'].items():
            output.append(f"- {name.upper()}: {info['cdn'][0] if isinstance(info['cdn'], list) else info['cdn']}")
            output.append(f"  Usage: {info['usage']}")
        
        # Animation Libraries
        output.append("\n**ANIMATION LIBRARIES:**")
        for name, info in FRAMEWORKS['animation_libraries'].items():
            output.append(f"- {name.upper()}: {info['cdn'][0] if isinstance(info['cdn'], list) else info['cdn']}")
            output.append(f"  Usage: {info['usage']}")
        
        output.append("\n**3D & GRAPHICS:**")
        for name, info in FRAMEWORKS['3d_graphics'].items():
            output.append(f"- {name.upper()}: {info['cdn'][0]}")
            output.append(f"  Usage: {info['usage']}")
        
        output.append("\n**CHARTS & DATA VIZ:**")
        for name, info in FRAMEWORKS['charts_data_viz'].items():
            output.append(f"- {name.upper()}: {info['cdn'][0]}")
            output.append(f"  When: {info['when']}")
        
        output.append("\n**INTERACTIONS:**")
        for name, info in FRAMEWORKS['interaction_libraries'].items():
            output.append(f"- {name.upper()}: {', '.join(info['cdn']) if isinstance(info['cdn'], list) else info['cdn']}")
            output.append(f"  Usage: {info['usage']}")
        
        output.append("\n**FORMS & VALIDATION:**")
        for name, info in FRAMEWORKS['forms_validation'].items():
            output.append(f"- {name.upper()}: {info['cdn'][0]}")
        
        output.append("\n**NOTIFICATIONS:**")
        for name, info in FRAMEWORKS['notifications_modals'].items():
            output.append(f"- {name.upper()}: {info['cdn'][0]}")
            output.append(f"  Usage: {info['usage']}")
        
        return "\n".join(output)

    def _format_design_knowledge(self) -> str:
        """Format design principles and best practices"""
        output = ["\n═══════════════════════════════════════════════════════════════"]
        output.append("🎨 DESIGN KNOWLEDGE BASE")
        output.append("═══════════════════════════════════════════════════════════════\n")
        
        # Color Theory
        output.append("**COLOR THEORY:**")
        output.append("Popular Palettes:")
        for style, colors in DESIGN_PRINCIPLES['color_theory']['popular_palettes'].items():
            output.append(f"- {style.title()}: {', '.join(colors)}")
        
        output.append("\nColor Best Practices:")
        for practice in DESIGN_PRINCIPLES['color_theory']['best_practices']:
            output.append(f"• {practice}")
        
        # Typography
        output.append("\n**TYPOGRAPHY:**")
        output.append("Font Pairings:")
        for style, pairing in DESIGN_PRINCIPLES['typography']['font_pairings'].items():
            output.append(f"- {style.title()}: {pairing}")
        
        output.append("\nTypography Best Practices:")
        for practice in DESIGN_PRINCIPLES['typography']['best_practices']:
            output.append(f"• {practice}")
        
        # Spacing
        output.append("\n**SPACING & LAYOUT:**")
        output.append("Spacing Scale:")
        for size, value in DESIGN_PRINCIPLES['spacing_layout']['spacing_scale'].items():
            output.append(f"- {size}: {value}")
        
        output.append("\nLayout Best Practices:")
        for practice in DESIGN_PRINCIPLES['spacing_layout']['best_practices']:
            output.append(f"• {practice}")
        
        return "\n".join(output)

    def _format_component_patterns(self) -> str:
        """Format component design patterns"""
        output = ["\n═══════════════════════════════════════════════════════════════"]
        output.append("🧩 COMPONENT DESIGN PATTERNS")
        output.append("═══════════════════════════════════════════════════════════════\n")
        
        # Buttons
        output.append("**BUTTON PATTERNS:**")
        output.append("Primary Button CSS:")
        output.append(COMPONENT_PATTERNS['buttons']['primary_button']['css'])
        
        # Cards
        output.append("\n**CARD PATTERNS:**")
        output.append("Elevated Card CSS:")
        output.append(COMPONENT_PATTERNS['cards']['elevated_card']['css'])
        
        output.append("\nGlass Morphism Card CSS:")
        output.append(COMPONENT_PATTERNS['cards']['glass_card']['css'])
        
        # Forms
        output.append("\n**FORM PATTERNS:**")
        output.append("Modern Input CSS:")
        output.append(COMPONENT_PATTERNS['forms']['modern_input']['css'])
        
        # Website Patterns
        output.append("\n**WEBSITE TYPE PATTERNS:**")
        for web_type, info in WEBSITE_PATTERNS.items():
            output.append(f"\n{web_type.upper().replace('_', ' ')}:")
            output.append(f"Structure: {' → '.join(info['structure'])}")
            output.append(f"Color Scheme: {info['color_scheme']}")
            output.append("Design Tips:")
            for tip in info['design_tips']:
                output.append(f"• {tip}")
        
        return "\n".join(output)

    def _get_fallback_html(self, prompt: str) -> str:
        """Generate fallback HTML"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Weaver Project</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>Welcome to Your Project</h1>
            <p class="subtitle">{prompt}</p>
        </header>
        
        <main class="content">
            <div class="card">
                <h2>🚀 Deployed on Netlify</h2>
                <p>This project is ready for instant deployment with Netlify Deploy Previews.</p>
            </div>
            
            <div class="card">
                <h2>✨ Features</h2>
                <ul>
                    <li>Serverless Functions Ready</li>
                    <li>Responsive Design</li>
                    <li>Modern UI</li>
                </ul>
            </div>
        </main>
        
        <footer class="footer">
            <p>Generated by Code Weaver | Powered by Netlify</p>
        </footer>
    </div>
    
    <script src="app.js"></script>
</body>
</html>"""
    
    def _get_fallback_css(self) -> str:
        """Generate fallback CSS"""
        return """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}

.container {
    max-width: 800px;
    width: 100%;
}

.header {
    text-align: center;
    color: white;
    margin-bottom: 40px;
}

.header h1 {
    font-size: 3rem;
    margin-bottom: 10px;
    animation: fadeInDown 0.8s ease;
}

.subtitle {
    font-size: 1.2rem;
    opacity: 0.9;
}

.content {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 40px;
}

.card {
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    animation: fadeInUp 0.8s ease;
}

.card h2 {
    font-size: 1.5rem;
    margin-bottom: 15px;
    color: #333;
}

.card p {
    color: #666;
    line-height: 1.6;
}

.card ul {
    list-style: none;
    padding: 0;
}

.card li {
    padding: 10px 0;
    color: #555;
    border-bottom: 1px solid #eee;
}

.card li:last-child {
    border-bottom: none;
}

.footer {
    text-align: center;
    color: white;
    opacity: 0.8;
}

@keyframes fadeInDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@media (max-width: 768px) {
    .header h1 {
        font-size: 2rem;
    }
    
    .content {
        grid-template-columns: 1fr;
    }
}"""
    
    def _get_fallback_js(self) -> str:
        """Generate fallback JavaScript"""
        return """// Code Weaver - Netlify Project
console.log('🚀 Netlify project loaded successfully!');

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Log deployment info
console.log('Deployed on Netlify with instant Deploy Previews');
console.log('Environment:', window.location.hostname);
"""
