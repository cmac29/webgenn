import os
import logging
import json
import re
from typing import Dict, Any, List, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage
from design_knowledge_base import (
    FRAMEWORKS, 
    DESIGN_PRINCIPLES, 
    COMPONENT_PATTERNS, 
    ANIMATION_PATTERNS,
    WEBSITE_PATTERNS
)

logger = logging.getLogger(__name__)

class AIService:
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

    async def generate_response(self, prompt: str, model: str, session_id: str, current_website: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate AI response for user prompt with website context"""
        provider, model_name = self._get_model_config(model)
        
        # Build context-aware system message
        system_message = """You are Code Weaver, an expert AI assistant that helps users create professional, production-ready web applications.

IMPORTANT RULES:
1. DO NOT output code blocks in your responses
2. DO NOT show HTML, CSS, JavaScript, or Python code to users
3. When users ask for website generation or modifications, explain what you'll implement
4. Keep responses conversational and helpful
5. If users ask questions about web development, answer them conversationally
6. Only provide brief explanations, not actual code

Your role is to discuss and plan websites, not to dump code in chat."""
        
        # If there's existing website code, add it to context
        context_info = ""
        if current_website:
            html_len = len(current_website.get('html_content', ''))
            css_len = len(current_website.get('css_content', ''))
            js_len = len(current_website.get('js_content', ''))
            backend_len = len(current_website.get('python_backend', ''))
            
            context_info = f"""

📋 CURRENT PROJECT STATUS:

You have an existing website project with:
- HTML: {html_len} characters
- CSS: {css_len} characters  
- JavaScript: {js_len} characters
- Backend: {backend_len} characters

When users ask to modify the website, acknowledge their request and explain what will be implemented. DO NOT show code. The actual implementation will happen automatically."""
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_message + context_info
            )
            chat.with_model(provider, model_name)
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            return {
                "content": response,
                "website_data": None,
                "image_urls": None
            }
        except Exception as e:
            logger.error(f"AI response generation failed: {str(e)}")
            return {
                "content": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                "website_data": None,
                "image_urls": None
            }

    async def generate_complete_project(self, prompt: str, model: str, framework: str, conversation_history: List[Dict], current_website: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate a complete, production-ready project with iterative editing support"""
        provider, model_name = self._get_model_config(model)
        session_id = f"project_{os.urandom(8).hex()}"
        
        logger.info(f"Starting complete project generation with {provider}/{model_name}")
        logger.info(f"User prompt: {prompt}")
        
        if current_website:
            logger.info(f"🔄 ITERATIVE EDITING MODE: Modifying existing website")
            logger.info(f"   Existing HTML: {len(current_website.get('html_content', ''))} chars")
            logger.info(f"   Existing CSS: {len(current_website.get('css_content', ''))} chars")
            logger.info(f"   Existing JS: {len(current_website.get('js_content', ''))} chars")
        else:
            logger.info(f"🆕 NEW PROJECT MODE: Creating from scratch")
        
        try:
            # First, analyze what the user is ACTUALLY asking for
            analysis = await self._analyze_user_intent(prompt, provider, model_name, session_id, current_website)
            logger.info(f"Intent analysis: {analysis}")
            
            # Generate frontend with context (pass existing website for iterative editing)
            frontend_result = await self._generate_contextual_frontend(prompt, analysis, provider, model_name, session_id, current_website)
            
            # Generate backend
            backend_result = await self._generate_backend(prompt, provider, model_name, session_id)
            
            # Generate documentation
            readme = await self._generate_readme(prompt, provider, model_name, session_id)
            
            # Compile all files
            files = []
            
            if frontend_result.get('html'):
                files.append({
                    "filename": "index.html",
                    "content": frontend_result['html'],
                    "file_type": "html",
                    "description": "Main HTML file with structure and content"
                })
            
            if frontend_result.get('css'):
                files.append({
                    "filename": "styles.css",
                    "content": frontend_result['css'],
                    "file_type": "css",
                    "description": "Stylesheet with modern, responsive design"
                })
            
            if frontend_result.get('js'):
                files.append({
                    "filename": "app.js",
                    "content": frontend_result['js'],
                    "file_type": "js",
                    "description": "JavaScript for interactivity and API calls"
                })
            
            if backend_result.get('python'):
                files.append({
                    "filename": "server.py",
                    "content": backend_result['python'],
                    "file_type": "python",
                    "description": "FastAPI backend with routes and business logic"
                })
            
            if backend_result.get('requirements'):
                files.append({
                    "filename": "requirements.txt",
                    "content": backend_result['requirements'],
                    "file_type": "txt",
                    "description": "Python dependencies"
                })
            
            if readme:
                files.append({
                    "filename": "README.md",
                    "content": readme,
                    "file_type": "md",
                    "description": "Project documentation"
                })
            
            package_json = self._generate_package_json(prompt)
            files.append({
                "filename": "package.json",
                "content": package_json,
                "file_type": "json",
                "description": "Frontend dependencies and scripts"
            })
            
            logger.info(f"Generated complete project with {len(files)} files")
            
            return {
                "html_content": frontend_result.get('html', ''),
                "css_content": frontend_result.get('css', ''),
                "js_content": frontend_result.get('js', ''),
                "python_backend": backend_result.get('python', ''),
                "requirements_txt": backend_result.get('requirements', ''),
                "package_json": package_json,
                "readme": readme,
                "structure": analysis,
                "files": files
            }
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Complete project generation failed: {error_str}", exc_info=True)
            
            # Check if it's an API error (not a code issue)
            if "BadGatewayError" in error_str or "502" in error_str or "503" in error_str or "timeout" in error_str.lower():
                logger.warning("API error detected - retrying generation once...")
                try:
                    # Retry once for API errors
                    analysis = await self._analyze_user_intent(prompt, provider, model_name, session_id, current_website)
                    frontend_result = await self._generate_contextual_frontend(prompt, analysis, provider, model_name, session_id, current_website)
                    backend_result = await self._generate_backend(prompt, provider, model_name, session_id)
                    readme = await self._generate_readme(prompt, provider, model_name, session_id)
                    
                    files = []
                    if frontend_result.get('html'):
                        files.append({"filename": "index.html", "content": frontend_result['html'], "file_type": "html", "description": "Main HTML file"})
                    if frontend_result.get('css'):
                        files.append({"filename": "styles.css", "content": frontend_result['css'], "file_type": "css", "description": "Stylesheet"})
                    if frontend_result.get('js'):
                        files.append({"filename": "app.js", "content": frontend_result['js'], "file_type": "js", "description": "JavaScript"})
                    
                    package_json = self._generate_package_json(prompt)
                    files.append({"filename": "package.json", "content": package_json, "file_type": "json", "description": "Package configuration"})
                    
                    logger.info("✅ Retry successful!")
                    
                    return {
                        "html_content": frontend_result.get('html', ''),
                        "css_content": frontend_result.get('css', ''),
                        "js_content": frontend_result.get('js', ''),
                        "python_backend": backend_result.get('python', ''),
                        "requirements_txt": backend_result.get('requirements', ''),
                        "package_json": package_json,
                        "readme": readme,
                        "structure": analysis,
                        "files": files
                    }
                except Exception as retry_error:
                    logger.error(f"Retry also failed: {str(retry_error)}")
            
            # Only use fallback as last resort
            logger.warning("Using fallback project template")
            return await self._generate_fallback_project(prompt)

    async def _analyze_user_intent(self, prompt: str, provider: str, model: str, session_id: str, current_website: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze what the user is ACTUALLY asking for"""
        
        # Build context message if there's an existing website
        context_info = ""
        if current_website:
            context_info = f"""

🔄 IMPORTANT: This is an ITERATIVE EDIT request. An existing website is already built.
The user wants to MODIFY or ADD TO the existing website, not create a new one from scratch.

Current website type: {current_website.get('structure', {}).get('app_type', 'unknown')}
Current features: {', '.join(current_website.get('structure', {}).get('primary_features', []))}

Analyze if the user is asking to:
- ADD new features to the existing website
- MODIFY existing features
- CHANGE the design/styling
- FIX or improve something"""
        
        system_msg = """You are an expert at understanding user intent for web applications.

Analyze the user's request and identify:
1. What TYPE of website/app they want (e.g., video platform, e-commerce, social media, dashboard, etc.)
2. What SPECIFIC FEATURES they need (e.g., video grid, shopping cart, user profiles, data visualization)
3. What VISUAL STYLE is appropriate (e.g., YouTube's dark theme with thumbnails, Amazon's product grid, Netflix's hero banner)
4. What COMPONENTS are needed (e.g., navigation bar, sidebar, video player, cards, forms)
""" + context_info + """

Return ONLY a JSON object with this structure:
{
  "app_type": "video_platform OR ecommerce OR social_media OR dashboard OR landing_page OR other",
  "reference_site": "youtube OR netflix OR amazon OR twitter OR stripe OR custom",
  "key_components": ["video_grid", "sidebar_nav", "search_bar", "video_player"],
  "visual_style": "dark_theme OR light_theme OR gradient OR minimal OR colorful",
  "layout_pattern": "grid OR feed OR hero_sections OR dashboard_cards OR single_page",
  "primary_features": ["video_playback", "comments", "recommendations", "subscriptions"]
}"""
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_analyzer",
            system_message=system_msg
        )
        chat.with_model(provider, model)
        
        analysis_prompt = f"""Analyze this website request:

"{prompt}"

Return ONLY the JSON analysis object."""
        
        user_message = UserMessage(text=analysis_prompt)
        response = await chat.send_message(user_message)
        
        try:
            # Extract JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            analysis = json.loads(json_str)
            return analysis
        except:
            # Fallback analysis
            return {
                "app_type": "landing_page",
                "reference_site": "custom",
                "key_components": ["header", "hero", "features", "footer"],
                "visual_style": "modern",
                "layout_pattern": "hero_sections",
                "primary_features": ["responsive_design"]
            }

    async def _generate_contextual_frontend(self, prompt: str, analysis: Dict, provider: str, model: str, session_id: str, current_website: Optional[Dict] = None) -> Dict[str, str]:
        """Generate frontend based on context analysis - Supports iterative editing"""
        
        logger.info("=" * 80)
        logger.info(f"FRONTEND GENERATION START")
        logger.info(f"User Prompt: {prompt}")
        logger.info(f"Analysis: {analysis}")
        logger.info(f"Has existing website: {current_website is not None}")
        logger.info("=" * 80)
        
        # Build context-specific instructions
        reference_examples = self._get_reference_examples(analysis.get('reference_site', 'custom'))
        component_templates = self._get_component_templates(analysis.get('key_components', []))
        
        # Build comprehensive knowledge base for AI
        frameworks_info = self._format_frameworks_knowledge()
        design_info = self._format_design_knowledge()
        component_info = self._format_component_patterns()
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_frontend",
            system_message=f"""You are an ELITE web developer with COMPREHENSIVE DESIGN KNOWLEDGE who creates PIXEL-PERFECT, VISUALLY STUNNING web applications.

{frameworks_info}

{design_info}

{component_info}

You have access to this complete knowledge base - USE IT to create professional, modern designs!

🚨 CRITICAL REQUIREMENT - EMBEDDED STYLES 🚨
The HTML will be displayed in an IFRAME using srcDoc. This means:
- ALL CSS MUST be in <style> tags inside <head>
- ALL JavaScript MUST be in <script> tags inside <body>
- NO external file references except CDN libraries
- EVERYTHING must be self-contained in ONE HTML file

📚 AVAILABLE LIBRARIES & APIs (Include via CDN in <head>):

**Icon Libraries** (Use for professional icons):
- Font Awesome 6.5: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  Usage: <i class="fas fa-heart"></i>, <i class="fab fa-youtube"></i>
- Material Icons: <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
  Usage: <span class="material-icons">home</span>

**UI Frameworks** (For rapid styling):
- Tailwind CSS: <script src="https://cdn.tailwindcss.com"></script>
- Bootstrap 5: <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

**Animation Libraries**:
- Animate.css: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css">
  Usage: class="animate__animated animate__fadeIn"
- AOS (Animate On Scroll): <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
  <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>

**Chart Libraries** (For dashboards):
- Chart.js: <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
- ApexCharts: <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>

**Interaction Libraries**:
- SortableJS (drag & drop): <script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>
- SwiperJS (carousels): <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css">
  <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>

**Utility Libraries**:
- Axios (HTTP requests): <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
- Day.js (dates): <script src="https://cdn.jsdelivr.net/npm/dayjs@1/dayjs.min.js"></script>
- Lodash (utilities): <script src="https://cdn.jsdelivr.net/npm/lodash@4.17.21/lodash.min.js"></script>

**Form Libraries**:
- Cleave.js (input formatting): <script src="https://cdn.jsdelivr.net/npm/cleave.js@1.6.0/dist/cleave.min.js"></script>

🎨 VISUAL DESIGN REQUIREMENTS:
1. MATCH the exact visual style requested (YouTube → dark theme with video grid, Netflix → hero with content rows)
2. Use PROFESSIONAL color schemes with modern palettes
3. Add proper spacing, padding, and margins (generous white space)
4. Include hover effects, transitions, and animations
5. Use modern fonts (Google Fonts: Inter, Roboto, Poppins, Space Grotesk)
6. Create depth with shadows, gradients, and layering
7. Use Font Awesome or Material Icons for ALL icons (no emojis in production)
8. Add micro-interactions (button ripples, card lifts, smooth transitions)
9. Implement glassmorphism effects where appropriate
10. Use CSS Grid and Flexbox for layouts

⚡ FUNCTIONAL REQUIREMENTS:
- Include ALL necessary components (nav, sidebar, cards, players, forms)
- Add working JavaScript for interactivity
- Use appropriate libraries for complex features (charts, carousels, animations)
- Make elements clickable with proper event handlers
- Add form validation where needed
- Implement smooth scrolling and page transitions
- Use local storage for state persistence
- Add loading states and skeleton screens

REFERENCE EXAMPLES:
{reference_examples}

COMPONENTS TO INCLUDE:
{component_templates}

OUTPUT FORMAT:
Generate THREE separate code blocks, but remember the HTML will contain EMBEDDED styles and scripts:

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        /* ALL your CSS here - complete and beautiful */
    </style>
</head>
<body>
    <!-- ALL your HTML structure here -->
    
    <script>
        // ALL your JavaScript here
    </script>
</body>
</html>
```

```css
/* Duplicate of the embedded CSS for reference */
```

```javascript
/* Duplicate of the embedded JS for reference */
```"""
        )
        chat.with_model(provider, model)
        
        # Build existing website context if available - SHOW FULL CODE FOR EDITING
        existing_code_context = ""
        if current_website:
            html_full = current_website.get('html_content', '')
            css_full = current_website.get('css_content', '')
            js_full = current_website.get('js_content', '')
            
            existing_code_context = f"""
═══════════════════════════════════════════════════════════════
🔄 ITERATIVE EDITING MODE - FULL EXISTING WEBSITE CODE
═══════════════════════════════════════════════════════════════

⚠️ CRITICAL: You are MODIFYING an EXISTING website, NOT creating from scratch!

This is the COMPLETE current code. The user wants to make changes to this existing website.

YOU MUST:
1. Read and understand the existing code structure
2. Make ONLY the specific changes the user requests
3. Keep EVERYTHING else exactly as it is
4. Don't redesign or rebuild - just EDIT what's requested
5. Maintain all existing IDs, classes, and functionality

COMPLETE CURRENT HTML:
```html
{html_full}
```

COMPLETE CURRENT CSS:
```css
{css_full}
```

COMPLETE CURRENT JAVASCRIPT:
```javascript
{js_full}
```

USER'S MODIFICATION REQUEST: {prompt}

🎯 YOUR TASK: 
1. Analyze what the user wants to change/add
2. Make surgical edits to the existing code
3. Return the COMPLETE modified code (not just the changes)
4. Preserve all existing features not mentioned in the request

EXAMPLE:
- User says "add a dark mode toggle" → Add toggle button + dark mode CSS, keep everything else
- User says "change header color to blue" → Change header color only, keep all other styles
- User says "add a contact form" → Insert contact form in appropriate location, keep existing sections

═══════════════════════════════════════════════════════════════
"""
        
        if current_website:
            # EDITING MODE - Different prompt structure
            frontend_prompt = f"""🔄 WEBSITE EDITING TASK 🔄

{existing_code_context}

⚠️ EDITING INSTRUCTIONS:
You have the COMPLETE existing website code above. The user wants to make changes.

USER'S REQUEST: {prompt}

🎯 WHAT TO DO:
1. Study the existing HTML, CSS, and JavaScript structure
2. Identify exactly what needs to change based on the user's request
3. Make those specific changes
4. Keep EVERYTHING else unchanged
5. Return the complete modified HTML, CSS, and JavaScript

🚫 DO NOT:
- Rebuild the website from scratch
- Remove existing features
- Change unrelated styling or functionality
- Redesign the entire layout

✅ DO:
- Make precise surgical edits
- Add new features if requested
- Modify specific elements if requested
- Maintain existing structure and design language
- Preserve all working functionality

Generate the complete modified code maintaining all existing features:"""
        else:
            # CREATION MODE - Original prompt structure  
            frontend_prompt = f"""🚀 CREATE A COMPLETELY UNIQUE {analysis.get("app_type", "website").upper()} 🚀

⚠️ CRITICAL: Generate NEW, ORIGINAL code based on this SPECIFIC request. DO NOT reuse templates!

USER REQUEST: {prompt}

APP TYPE: {analysis.get('app_type')}
REFERENCE STYLE: {analysis.get('reference_site')}
KEY COMPONENTS: {', '.join(analysis.get('key_components', []))}
VISUAL STYLE: {analysis.get('visual_style')}
LAYOUT: {analysis.get('layout_pattern')}

🎯 REQUIREMENT: Create a UNIQUE design that matches THIS SPECIFIC request.
- If they ask for a YouTube clone → create a video platform interface
- If they ask for a landing page → create a landing page
- If they ask for a dashboard → create a dashboard
- If they ask for e-commerce → create a shopping site
- If they ask for a blog → create a blog layout

DO NOT generate the same layout repeatedly. Each request is DIFFERENT!

═══════════════════════════════════════════════════════════════
📚 REQUIRED CDN LIBRARIES (Add to <head>):
═══════════════════════════════════════════════════════════════

<!-- Font Awesome Icons (REQUIRED - Use instead of emojis) -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

<!-- Material Icons (Alternative icon set) -->
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">

<!-- Animate.css (For smooth animations) -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css">

ICON EXAMPLES:
- Home: <i class="fas fa-home"></i>
- Search: <i class="fas fa-search"></i>  
- Video/Play: <i class="fas fa-play-circle"></i>
- User: <i class="fas fa-user-circle"></i>
- Menu: <i class="fas fa-bars"></i>
- Heart/Like: <i class="fas fa-heart"></i>
- Bell: <i class="fas fa-bell"></i>
- Settings: <i class="fas fa-cog"></i>
- Shopping Cart: <i class="fas fa-shopping-cart"></i>
- Star: <i class="fas fa-star"></i>

═══════════════════════════════════════════════════════════════

GENERATE THREE FILES (CSS and JS will be embedded in HTML):

1. **index.html** - Complete self-contained HTML with:
   - CDN library links in <head>
   - Embedded <style> with ALL CSS
   - Proper semantic structure
   - ALL components listed above
   - Font Awesome icons (NOT emojis)
   - Realistic placeholder content
   - Embedded <script> with ALL JavaScript

2. **styles.css** - Duplicate of embedded CSS:
   - Modern color palette
   - Proper layout (Grid/Flexbox)
   - Responsive design (@media queries)
   - All component styles
   - Hover effects and transitions
   - Animations
   - MINIMUM 600 lines

3. **app.js** - Duplicate of embedded JavaScript:
   - DOM manipulation
   - Event handlers
   - Interactive features
   - State management
   - Smooth animations
   - API integration ready

FORMAT:
```html
[COMPLETE HTML]
```

```css
[COMPLETE CSS - MINIMUM 600 LINES]
```

```javascript
[COMPLETE JAVASCRIPT]
```

MAKE IT LOOK AND FUNCTION LIKE THE REAL THING!"""
        
        user_message = UserMessage(text=frontend_prompt)
        response = await chat.send_message(user_message)
        
        logger.info(f"AI Response received: {len(response)} characters")
        logger.info(f"Response preview (first 500 chars): {response[:500]}")
        
        # Extract code with improved logic
        html = self._extract_code_block(response, "html") or ""
        css = self._extract_code_block(response, "css") or ""
        js = self._extract_code_block(response, "javascript") or self._extract_code_block(response, "js") or ""
        
        logger.info(f"Initial extraction: HTML={len(html)} chars, CSS={len(css)} chars, JS={len(js)} chars")
        
        # Fallback extraction - try multiple methods
        if not html:
            logger.info("Primary HTML extraction failed, trying direct extraction...")
            if "<!DOCTYPE" in response or "<html" in response:
                html = self._extract_html_direct(response)
                logger.info(f"Direct HTML extraction result: {len(html)} chars")
        
        # If we have HTML but no CSS/JS, try to extract them separately
        if html and not css:
            logger.info("Attempting to extract CSS from response...")
            css_match = re.search(r'```css\s*(.*?)\s*```', response, re.DOTALL)
            if css_match:
                css = css_match.group(1).strip()
                logger.info(f"Extracted CSS via regex: {len(css)} chars")
        
        if html and not js:
            logger.info("Attempting to extract JavaScript from response...")
            js_match = re.search(r'```(?:javascript|js)\s*(.*?)\s*```', response, re.DOTALL)
            if js_match:
                js = js_match.group(1).strip()
                logger.info(f"Extracted JS via regex: {len(js)} chars")
        
        # CRITICAL: For iframe preview, CSS and JS MUST be embedded in HTML
        # Remove any external file references and embed the content
        if html:
            # Check if HTML has embedded styles
            has_embedded_css = "<style>" in html
            has_embedded_js = "<script>" in html and "src=" not in html[:html.find("<script>") + 50] if "<script>" in html else False
            
            logger.info(f"Embedded check: CSS={has_embedded_css}, JS={has_embedded_js}")
            
            if not has_embedded_css and css:
                # Embed CSS into HTML
                logger.info("Embedding CSS into HTML for iframe preview")
                if "</head>" in html:
                    html = html.replace("</head>", f"    <style>\n{css}\n    </style>\n</head>")
                else:
                    html = html.replace("<head>", f"<head>\n    <style>\n{css}\n    </style>")
            
            if not has_embedded_js and js:
                # Embed JS into HTML
                logger.info("Embedding JS into HTML for iframe preview")
                if "</body>" in html:
                    html = html.replace("</body>", f"    <script>\n{js}\n    </script>\n</body>")
                else:
                    html += f"\n<script>\n{js}\n</script>"
            
            # Remove external file references
            html = re.sub(r'<link[^>]*href=["\']styles\.css["\'][^>]*>', '', html)
            html = re.sub(r'<script[^>]*src=["\']app\.js["\'][^>]*></script>', '', html)
        
        # More lenient validation - focus on structure rather than size
        has_doctype = "<!DOCTYPE" in html or "<html" in html
        has_head = "<head>" in html or "<head " in html
        has_body = "<body>" in html or "<body " in html
        has_styles = "<style>" in html or "style=" in html or len(css) > 0
        
        logger.info(f"Validation: doctype={has_doctype}, head={has_head}, body={has_body}, styles={has_styles}, html_length={len(html)}")
        
        # Only retry if we have a fundamentally broken HTML structure
        if not has_doctype or not has_body or len(html) < 200:
            logger.warning(f"HTML structure invalid (doctype={has_doctype}, body={has_body}, length={len(html)}), retrying generation...")
            
            # Retry with more explicit instructions
            retry_prompt = f"""GENERATE COMPLETE, SELF-CONTAINED HTML FOR:

{prompt}

REQUIREMENTS:
1. MUST be a complete HTML document starting with <!DOCTYPE html>
2. MUST include embedded <style> tags in <head> with comprehensive CSS
3. MUST include embedded <script> tags before </body> with working JavaScript
4. MUST match the request exactly (if they ask for YouTube, make a video platform)
5. Use Font Awesome icons: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

Generate ONLY the complete HTML code in a ```html code block."""

            retry_chat = LlmChat(
                api_key=self.api_key,
                session_id=f"{session_id}_retry",
                system_message="You are a professional web developer. Generate complete, working HTML with embedded CSS and JavaScript."
            )
            retry_chat.with_model(provider, model)
            
            retry_response = await retry_chat.send_message(UserMessage(text=retry_prompt))
            logger.info(f"Retry response received: {len(retry_response)} characters")
            
            # Extract again
            html = self._extract_code_block(retry_response, "html") or self._extract_html_direct(retry_response)
            logger.info(f"Retry extraction result: {len(html)} chars")
            
            # If still invalid, extract CSS/JS and embed
            if html and "<style>" not in html and css:
                logger.info("Embedding previously extracted CSS into retry HTML")
                if "</head>" in html:
                    html = html.replace("</head>", f"<style>\n{css}\n</style>\n</head>")
            
            if html and "<script>" not in html and js:
                logger.info("Embedding previously extracted JS into retry HTML")
                if "</body>" in html:
                    html = html.replace("</body>", f"<script>\n{js}\n</script>\n</body>")
        
        # ONLY use fallback if generation completely failed (very rare)
        if not html or len(html) < 100:
            logger.error(f"CRITICAL: Generation completely failed (HTML length: {len(html)}). Using dynamic fallback.")
            fallback_result = await self._generate_fallback_frontend(prompt, analysis)
            html = fallback_result.get('html', '')
            css = fallback_result.get('css', '')
            js = fallback_result.get('js', '')
            logger.info(f"Fallback template applied: HTML={len(html)}, CSS={len(css)}, JS={len(js)}")
        else:
            logger.info("✅ Generation successful - using AI-generated code")
        
        if len(css) < 300 and "<style>" not in html:
            logger.warning(f"CSS too short ({len(css)} chars), enhancing")
            css = self._enhance_css_for_app_type(css, analysis)
        
        logger.info(f"FINAL OUTPUT: HTML={len(html)}, CSS={len(css)}, JS={len(js)}")
        logger.info("=" * 80)
        
        return {"html": html, "css": css, "js": js}

    def _get_reference_examples(self, reference_site: str) -> str:
        """Get specific examples for reference sites"""
        examples = {
            "youtube": """YOUTUBE STYLE:
- Dark theme (#0f0f0f background, #212121 for cards)
- Top navigation bar with logo, search bar, icons
- Left sidebar with menu items
- Main content: Grid of video cards (3-4 columns)
- Each card: Thumbnail image, title, channel name, views, date
- Video player page: Large player, title, channel info, description
- Use Material Icons or emoji for icons""",
            "netflix": """NETFLIX STYLE:
- Dark background (#141414)
- Large hero banner with featured content
- Horizontal scrolling rows of content cards
- Hover effects with scale and info reveal
- Navigation bar with transparent/blur effect
- Red accent color (#E50914)""",
            "twitter": """TWITTER STYLE:
- Three column layout: sidebar, feed, trending
- Blue accent (#1DA1F2)
- Tweet cards with avatar, username, text, actions
- Rounded profile images
- Light theme with white cards""",
            "amazon": """AMAZON STYLE:
- Product grid layout
- Search bar prominent in header
- Product cards: image, title, price, rating
- Orange accent (#FF9900)
- Left sidebar with filters/categories"""
        }
        return examples.get(reference_site, "Modern, professional design with appropriate layout for the app type.")

    def _get_component_templates(self, components: List[str]) -> str:
        """Get templates for specific components"""
        templates = []
        
        if "video_grid" in components:
            templates.append("Video Grid: 3-4 columns of video cards with thumbnail, title, channel, views")
        if "sidebar_nav" in components:
            templates.append("Sidebar Navigation: Vertical menu with icons and labels")
        if "search_bar" in components:
            templates.append("Search Bar: Prominent input field with search icon")
        if "video_player" in components:
            templates.append("Video Player: Large embedded player with controls")
        if "product_grid" in components:
            templates.append("Product Grid: Cards with image, title, price, rating")
        if "feed" in components:
            templates.append("Feed: Vertical list of posts/content cards")
        if "dashboard_cards" in components:
            templates.append("Dashboard Cards: Stats cards with numbers and charts")
        
        return "\n".join(templates) if templates else "Standard web components"

    def _enhance_css_for_app_type(self, css: str, analysis: Dict) -> str:
        """Add CSS enhancements based on app type"""
        app_type = analysis.get('app_type', 'landing_page')
        
        if app_type == 'video_platform':
            enhancement = """/* Video Platform Styles */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

:root {
    --yt-black: #0f0f0f;
    --yt-dark: #212121;
    --yt-white: #ffffff;
    --yt-text: #f1f1f1;
    --yt-border: #303030;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Roboto', sans-serif;
    background: var(--yt-black);
    color: var(--yt-text);
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--yt-black);
    border-bottom: 1px solid var(--yt-border);
}

.sidebar {
    position: fixed;
    left: 0;
    top: 56px;
    width: 240px;
    height: calc(100vh - 56px);
    background: var(--yt-black);
    overflow-y: auto;
    padding: 12px 0;
}

.main-content {
    margin-left: 240px;
    margin-top: 56px;
    padding: 24px;
}

.video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
}

.video-card {
    cursor: pointer;
}

.video-thumbnail {
    width: 100%;
    aspect-ratio: 16/9;
    background: var(--yt-dark);
    border-radius: 12px;
    position: relative;
    overflow: hidden;
}

.video-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.video-info {
    display: flex;
    gap: 12px;
    padding-top: 12px;
}

.channel-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--yt-dark);
}

.video-details h3 {
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
    margin-bottom: 4px;
}

.video-meta {
    font-size: 12px;
    color: #aaa;
}"""
        else:
            enhancement = """@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #6366f1;
    --background: #0f172a;
    --surface: #1e293b;
    --text: #f1f5f9;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', sans-serif;
    background: var(--background);
    color: var(--text);
    line-height: 1.6;
}"""
        
        return enhancement + "\n\n" + css

    async def _generate_fallback_frontend(self, prompt: str, analysis: Dict) -> Dict[str, str]:
        """Generate a fallback based on app type"""
        app_type = analysis.get('app_type', 'landing_page')
        
        if app_type == 'video_platform':
            return self._create_video_platform_fallback(prompt)
        else:
            return self._create_generic_fallback(prompt)

    def _create_video_platform_fallback(self, prompt: str) -> Dict[str, str]:
        """Create a video platform UI fallback with EMBEDDED styles and modern libraries"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VideoTube</title>
    
    <!-- Modern Icon Libraries -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    
    <!-- Animation Libraries -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css">
    
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0f0f0f;
            color: #f1f1f1;
            overflow-x: hidden;
        }}
        
        /* Header */
        .header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 56px;
            background: #0f0f0f;
            border-bottom: 1px solid #303030;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 100;
        }}
        
        .header-left {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .menu-btn {{
            background: none;
            border: none;
            color: #fff;
            font-size: 20px;
            cursor: pointer;
            padding: 8px;
            border-radius: 50%;
            transition: background 0.2s;
        }}
        
        .menu-btn:hover {{
            background: rgba(255,255,255,0.1);
        }}
        
        .logo {{
            font-size: 20px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
            color: #fff;
        }}
        
        .logo-icon {{
            font-size: 28px;
        }}
        
        .header-center {{
            flex: 1;
            max-width: 640px;
            display: flex;
            margin: 0 40px;
        }}
        
        .search-container {{
            flex: 1;
            display: flex;
            border: 1px solid #303030;
            border-radius: 40px;
            overflow: hidden;
            background: #121212;
        }}
        
        .search-bar {{
            flex: 1;
            background: transparent;
            border: none;
            padding: 12px 16px;
            color: #f1f1f1;
            font-size: 16px;
            outline: none;
        }}
        
        .search-btn {{
            background: #222;
            border: none;
            border-left: 1px solid #303030;
            padding: 0 20px;
            color: #fff;
            cursor: pointer;
            font-size: 18px;
            transition: background 0.2s;
        }}
        
        .search-btn:hover {{
            background: #333;
        }}
        
        .header-right {{
            display: flex;
            gap: 8px;
        }}
        
        .header-btn {{
            background: none;
            border: none;
            color: #fff;
            font-size: 22px;
            cursor: pointer;
            padding: 8px;
            border-radius: 50%;
            transition: background 0.2s;
        }}
        
        .header-btn:hover {{
            background: rgba(255,255,255,0.1);
        }}
        
        /* Sidebar */
        .sidebar {{
            position: fixed;
            left: 0;
            top: 56px;
            width: 240px;
            height: calc(100vh - 56px);
            background: #0f0f0f;
            overflow-y: auto;
            padding: 12px 0;
            border-right: 1px solid #303030;
        }}
        
        .sidebar::-webkit-scrollbar {{
            width: 8px;
        }}
        
        .sidebar::-webkit-scrollbar-thumb {{
            background: #303030;
            border-radius: 4px;
        }}
        
        .nav-item {{
            display: flex;
            align-items: center;
            padding: 10px 24px;
            color: #f1f1f1;
            text-decoration: none;
            transition: background 0.2s;
            gap: 24px;
            font-size: 14px;
        }}
        
        .nav-item:hover {{
            background: #272727;
        }}
        
        .nav-item.active {{
            background: #272727;
            font-weight: 500;
        }}
        
        .nav-separator {{
            height: 1px;
            background: #303030;
            margin: 12px 0;
        }}
        
        .nav-section-title {{
            padding: 8px 24px;
            font-size: 14px;
            font-weight: 500;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        /* Main Content */
        .main-content {{
            margin-left: 240px;
            margin-top: 56px;
            padding: 24px;
            min-height: calc(100vh - 56px);
        }}
        
        /* Chips/Filters */
        .chips-container {{
            display: flex;
            gap: 12px;
            padding-bottom: 24px;
            overflow-x: auto;
        }}
        
        .chips-container::-webkit-scrollbar {{
            height: 0;
        }}
        
        .chip {{
            padding: 8px 16px;
            background: #272727;
            border: 1px solid #303030;
            border-radius: 8px;
            color: #f1f1f1;
            font-size: 14px;
            white-space: nowrap;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .chip:hover {{
            background: #3f3f3f;
        }}
        
        .chip.active {{
            background: #f1f1f1;
            color: #0f0f0f;
            font-weight: 500;
        }}
        
        /* Video Grid */
        .video-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 40px 16px;
        }}
        
        .video-card {{
            cursor: pointer;
        }}
        
        .video-thumbnail {{
            position: relative;
            width: 100%;;
            aspect-ratio: 16/9;
            border-radius: 12px;
            overflow: hidden;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 60px;
            transition: transform 0.2s;
        }}
        
        .video-card:hover .video-thumbnail {{
            transform: scale(1.02);
        }}
        
        .duration {{
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: rgba(0,0,0,0.9);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}
        
        .video-info {{
            display: flex;
            gap: 12px;
            padding-top: 12px;
        }}
        
        .channel-avatar {{
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }}
        
        .video-details {{
            flex: 1;
        }}
        
        .video-title {{
            font-size: 14px;
            font-weight: 500;
            line-height: 1.4;
            margin-bottom: 4px;
            color: #f1f1f1;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        
        .video-meta {{
            font-size: 12px;
            color: #aaa;
            line-height: 1.6;
        }}
        
        .channel-name {{
            color: #aaa;
            transition: color 0.2s;
        }}
        
        .channel-name:hover {{
            color: #fff;
        }}
        
        /* Responsive */
        @media (max-width: 1024px) {{
            .video-grid {{
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            }}
        }}
        
        @media (max-width: 768px) {{
            .sidebar {{
                transform: translateX(-100%);
                transition: transform 0.3s;
            }}
            
            .sidebar.open {{
                transform: translateX(0);
            }}
            
            .main-content {{
                margin-left: 0;
            }}
            
            .video-grid {{
                grid-template-columns: 1fr;
                gap: 24px;
            }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-left">
            <button class="menu-btn" onclick="toggleSidebar()">☰</button>
            <div class="logo">
                <span class="logo-icon">📺</span>
                VideoTube
            </div>
        </div>
        <div class="header-center">
            <div class="search-container">
                <input type="text" class="search-bar" placeholder="Search" id="searchInput">
                <button class="search-btn" onclick="handleSearch()">🔍</button>
            </div>
        </div>
        <div class="header-right">
            <button class="header-btn">➕</button>
            <button class="header-btn">🔔</button>
            <button class="header-btn">👤</button>
        </div>
    </header>
    
    <aside class="sidebar" id="sidebar">
        <nav>
            <a href="#" class="nav-item active">🏠 Home</a>
            <a href="#" class="nav-item">🎬 Shorts</a>
            <a href="#" class="nav-item">📺 Subscriptions</a>
        </nav>
        <div class="nav-separator"></div>
        <nav>
            <a href="#" class="nav-item">📚 Library</a>
            <a href="#" class="nav-item">🕐 History</a>
            <a href="#" class="nav-item">📹 Your videos</a>
            <a href="#" class="nav-item">⏰ Watch later</a>
            <a href="#" class="nav-item">👍 Liked videos</a>
        </nav>
        <div class="nav-separator"></div>
        <div class="nav-section-title">Subscriptions</div>
        <nav>
            <a href="#" class="nav-item">🎨 TechReviews</a>
            <a href="#" class="nav-item">🎮 CodeWithMe</a>
            <a href="#" class="nav-item">🎵 MusicVibes</a>
            <a href="#" class="nav-item">🎯 GameZone</a>
        </nav>
        <div class="nav-separator"></div>
        <div class="nav-section-title">Explore</div>
        <nav>
            <a href="#" class="nav-item">🔥 Trending</a>
            <a href="#" class="nav-item">🛍️ Shopping</a>
            <a href="#" class="nav-item">🎵 Music</a>
            <a href="#" class="nav-item">🎬 Movies</a>
            <a href="#" class="nav-item">📡 Live</a>
            <a href="#" class="nav-item">🎮 Gaming</a>
            <a href="#" class="nav-item">⚽ Sports</a>
        </nav>
    </aside>
    
    <main class="main-content">
        <div class="chips-container">
            <div class="chip active">All</div>
            <div class="chip">Music</div>
            <div class="chip">Gaming</div>
            <div class="chip">News</div>
            <div class="chip">Live</div>
            <div class="chip">Sports</div>
            <div class="chip">Learning</div>
            <div class="chip">Fashion</div>
            <div class="chip">Podcasts</div>
        </div>
        
        <div class="video-grid" id="videoGrid"></div>
    </main>
    
    <script>
        const videos = [
            {{ title: 'Master JavaScript in 30 Minutes', channel: 'CodeMaster', views: '1.2M', time: '2 days ago', duration: '30:45', emoji: '💻' }},
            {{ title: 'Top 10 Web Design Trends 2024', channel: 'DesignPro', views: '856K', time: '1 week ago', duration: '15:22', emoji: '🎨' }},
            {{ title: 'Build a Full Stack App Tutorial', channel: 'DevGuru', views: '2.1M', time: '3 days ago', duration: '1:25:30', emoji: '🚀' }},
            {{ title: 'React Hooks Deep Dive', channel: 'CodeMaster', views: '1.8M', time: '5 days ago', duration: '22:10', emoji: '⚛️' }},
            {{ title: 'CSS Grid vs Flexbox Explained', channel: 'DesignPro', views: '943K', time: '1 week ago', duration: '18:33', emoji: '🎯' }},
            {{ title: 'Python Django for Beginners', channel: 'PythonPro', views: '1.5M', time: '2 weeks ago', duration: '45:12', emoji: '🐍' }},
            {{ title: 'AI and Machine Learning Basics', channel: 'AIAcademy', views: '2.8M', time: '4 days ago', duration: '38:45', emoji: '🤖' }},
            {{ title: 'Database Design Best Practices', channel: 'DataExpert', views: '678K', time: '1 week ago', duration: '28:17', emoji: '🗄️' }},
            {{ title: 'Modern UI/UX Design Principles', channel: 'DesignPro', views: '1.4M', time: '3 days ago', duration: '20:55', emoji: '✨' }},
            {{ title: 'Docker & Kubernetes Tutorial', channel: 'DevOps101', views: '1.1M', time: '5 days ago', duration: '52:30', emoji: '🐳' }},
            {{ title: 'GraphQL vs REST API', channel: 'DevGuru', views: '789K', time: '2 days ago', duration: '25:40', emoji: '📡' }},
            {{ title: 'TypeScript Complete Guide', channel: 'CodeMaster', views: '1.3M', time: '1 week ago', duration: '1:10:22', emoji: '📘' }}
        ];
        
        function createVideoCard(video) {{
            return `
                <div class="video-card" onclick="playVideo('${{video.title}}')">
                    <div class="video-thumbnail">
                        ${{video.emoji}}
                        <span class="duration">${{video.duration}}</span>
                    </div>
                    <div class="video-info">
                        <div class="channel-avatar">${{video.emoji}}</div>
                        <div class="video-details">
                            <div class="video-title">${{video.title}}</div>
                            <div class="video-meta">
                                <div class="channel-name">${{video.channel}}</div>
                                <div>${{video.views}} views • ${{video.time}}</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }}
        
        function renderVideos() {{
            const grid = document.getElementById('videoGrid');
            grid.innerHTML = videos.map(video => createVideoCard(video)).join('');
        }}
        
        function toggleSidebar() {{
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.toggle('open');
        }}
        
        function handleSearch() {{
            const query = document.getElementById('searchInput').value;
            if (query) {{
                alert('Searching for: ' + query);
            }}
        }}
        
        function playVideo(title) {{
            alert('Playing: ' + title);
        }}
        
        // Chip interaction
        document.addEventListener('DOMContentLoaded', () => {{
            renderVideos();
            
            const chips = document.querySelectorAll('.chip');
            chips.forEach(chip => {{
                chip.addEventListener('click', () => {{
                    chips.forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                }});
            }});
            
            // Search on Enter
            document.getElementById('searchInput').addEventListener('keypress', (e) => {{
                if (e.key === 'Enter') handleSearch();
            }});
        }});
    </script>
</body>
</html>"""

        # Extract the embedded CSS and JS for the separate tabs
        css_match = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
        css = css_match.group(1).strip() if css_match else """@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Roboto', sans-serif;
    background: #0f0f0f;
    color: #f1f1f1;
}

.header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: #0f0f0f;
    border-bottom: 1px solid #303030;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    z-index: 100;
}

.header-left, .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
}

.menu-btn {
    background: none;
    border: none;
    color: #fff;
    font-size: 20px;
    cursor: pointer;
    padding: 8px;
}

.logo {
    font-size: 20px;
    font-weight: 700;
}

.header-center {
    flex: 1;
    max-width: 600px;
    display: flex;
    gap: 8px;
    margin: 0 40px;
}

.search-bar {
    flex: 1;
    background: #121212;
    border: 1px solid #303030;
    border-radius: 40px;
    padding: 10px 16px;
    color: #f1f1f1;
    font-size: 16px;
}

.search-bar:focus {
    outline: none;
    border-color: #1e90ff;
}

.search-btn {
    background: #222;
    border: 1px solid #303030;
    border-radius: 40px;
    padding: 10px 20px;
    color: #fff;
    cursor: pointer;
}

.header-right button {
    background: none;
    border: none;
    color: #fff;
    font-size: 20px;
    cursor: pointer;
    padding: 8px;
}

.sidebar {
    position: fixed;
    left: 0;
    top: 56px;
    width: 240px;
    height: calc(100vh - 56px);
    background: #0f0f0f;
    overflow-y: auto;
    padding: 12px 0;
    border-right: 1px solid #303030;
}

.sidebar::-webkit-scrollbar { width: 8px; }
.sidebar::-webkit-scrollbar-thumb { background: #303030; border-radius: 4px; }

.nav-item {
    display: flex;
    align-items: center;
    padding: 10px 24px;
    color: #f1f1f1;
    text-decoration: none;
    transition: background 0.2s;
    gap: 24px;
}

.nav-item:hover {
    background: #272727;
}

.nav-item.active {
    background: #272727;
    font-weight: 500;
}

.main-content {
    margin-left: 240px;
    margin-top: 56px;
    padding: 24px;
    min-height: calc(100vh - 56px);
}

.video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 40px 16px;
}

.video-card {
    cursor: pointer;
}

.video-thumbnail {
    position: relative;
    width: 100%;
    aspect-ratio: 16/9;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
}

.video-thumbnail:hover {
    transform: scale(1.02);
    transition: transform 0.2s;
}

.duration {
    position: absolute;
    bottom: 8px;
    right: 8px;
    background: rgba(0,0,0,0.8);
    padding: 3px 6px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
}

.video-info {
    display: flex;
    gap: 12px;
    padding-top: 12px;
}

.channel-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    flex-shrink: 0;
}

.video-details h3 {
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
    margin-bottom: 4px;
    color: #f1f1f1;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.video-meta {
    font-size: 12px;
    color: #aaa;
    line-height: 1.4;
}

.channel-name {
    color: #aaa;
}

.channel-name:hover {
    color: #fff;
}

@media (max-width: 1024px) {
    .video-grid {
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    }
}

@media (max-width: 768px) {
    .sidebar {
        transform: translateX(-100%);
    }
    
    .main-content {
        margin-left: 0;
    }
    
    .video-grid {
        grid-template-columns: 1fr;
    }
}"""

        # Extract the embedded JavaScript
        js_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
        js = js_match.group(1).strip() if js_match else """// Video Platform JavaScript
const videoData = [
    { title: 'Amazing Tutorial: Learn Web Development', channel: 'CodeMaster', views: '1.2M', time: '2 days ago', duration: '15:30' },
    { title: 'Top 10 JavaScript Tips and Tricks', channel: 'DevGuru', views: '856K', time: '1 week ago', duration: '12:45' },
    { title: 'Build a Full Stack App from Scratch', channel: 'TechLead', views: '2.1M', time: '3 days ago', duration: '45:20' },
    { title: 'CSS Grid vs Flexbox: Complete Guide', channel: 'DesignPro', views: '543K', time: '5 days ago', duration: '18:15' },
    { title: 'React Hooks Explained Simply', channel: 'CodeMaster', views: '1.8M', time: '1 week ago', duration: '22:10' },
    { title: 'Python for Beginners 2024', channel: 'PythonAcademy', views: '3.2M', time: '2 weeks ago', duration: '1:05:30' },
    { title: 'Database Design Best Practices', channel: 'DataEngineer', views: '678K', time: '4 days ago', duration: '28:45' },
    { title: 'API Development with FastAPI', channel: 'BackendPro', views: '945K', time: '1 week ago', duration: '35:20' },
    { title: 'Modern UI/UX Design Principles', channel: 'DesignPro', views: '1.4M', time: '3 days ago', duration: '20:15' },
    { title: 'Docker & Kubernetes Tutorial', channel: 'DevOpsGuru', views: '1.1M', time: '5 days ago', duration: '42:30' },
    { title: 'Machine Learning Basics', channel: 'AIAcademy', views: '2.5M', time: '1 week ago', duration: '52:10' },
    { title: 'Git and GitHub for Teams', channel: 'TechLead', views: '789K', time: '2 days ago', duration: '25:40' }
];

const emojis = ['🎬', '🎮', '🎨', '🎯', '🎪', '🎭', '🎰', '🎲', '🎵', '🎸', '🎹', '🎺'];

function createVideoCard(video, index) {
    return `
        <div class="video-card">
            <div class="video-thumbnail">
                ${emojis[index % emojis.length]}
                <span class="duration">${video.duration}</span>
            </div>
            <div class="video-info">
                <div class="channel-avatar"></div>
                <div class="video-details">
                    <h3>${video.title}</h3>
                    <div class="video-meta">
                        <div class="channel-name">${video.channel}</div>
                        <div>${video.views} views • ${video.time}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderVideos() {
    const grid = document.getElementById('videoGrid');
    grid.innerHTML = videoData.map((video, index) => createVideoCard(video, index)).join('');
    
    // Add click handlers
    document.querySelectorAll('.video-card').forEach((card, index) => {
        card.addEventListener('click', () => {
            console.log('Playing video:', videoData[index].title);
            alert(`Now playing: ${videoData[index].title}`);
        });
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderVideos();
    
    // Search functionality
    const searchBar = document.querySelector('.search-bar');
    const searchBtn = document.querySelector('.search-btn');
    
    function handleSearch() {
        const query = searchBar.value.toLowerCase();
        if (query) {
            console.log('Searching for:', query);
            alert(`Searching for: ${query}`);
        }
    }
    
    searchBtn.addEventListener('click', handleSearch);
    searchBar.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    
    // Sidebar toggle for mobile
    const menuBtn = document.querySelector('.menu-btn');
    const sidebar = document.querySelector('.sidebar');
    
    menuBtn.addEventListener('click', () => {
        sidebar.style.transform = sidebar.style.transform === 'translateX(0px)' 
            ? 'translateX(-100%)' 
            : 'translateX(0px)';
    });
});"""

        return {"html": html, "css": css, "js": js}

    def _create_generic_fallback(self, prompt: str) -> Dict[str, str]:
        """Generic fallback for landing pages and general websites"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Website</title>
    
    <!-- Modern Libraries -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #ffffff;
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        /* Header */
        header {{
            padding: 20px 0;
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.1);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        nav {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .logo {{
            font-size: 28px;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .nav-links {{
            display: flex;
            gap: 30px;
            list-style: none;
        }}
        
        .nav-links a {{
            color: #ffffff;
            text-decoration: none;
            font-weight: 500;
            transition: opacity 0.3s;
        }}
        
        .nav-links a:hover {{
            opacity: 0.8;
        }}
        
        /* Hero Section */
        .hero {{
            text-align: center;
            padding: 120px 20px;
        }}
        
        .hero h1 {{
            font-size: 64px;
            font-weight: 800;
            margin-bottom: 24px;
            line-height: 1.2;
            text-shadow: 0 2px 20px rgba(0,0,0,0.2);
        }}
        
        .hero p {{
            font-size: 24px;
            margin-bottom: 40px;
            opacity: 0.95;
            font-weight: 300;
        }}
        
        .cta-buttons {{
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        
        .btn {{
            padding: 16px 40px;
            font-size: 18px;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }}
        
        .btn-primary {{
            background: #ffffff;
            color: #667eea;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.2);
            color: #ffffff;
            backdrop-filter: blur(10px);
            border: 2px solid rgba(255, 255, 255, 0.3);
        }}
        
        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }}
        
        /* Features Section */
        .features {{
            padding: 80px 20px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }}
        
        .features h2 {{
            text-align: center;
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 60px;
        }}
        
        .feature-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 40px;
        }}
        
        .feature-card {{
            background: rgba(255, 255, 255, 0.15);
            padding: 40px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s;
        }}
        
        .feature-card:hover {{
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }}
        
        .feature-icon {{
            font-size: 48px;
            margin-bottom: 20px;
        }}
        
        .feature-card h3 {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 16px;
        }}
        
        .feature-card p {{
            font-size: 16px;
            opacity: 0.9;
            line-height: 1.8;
        }}
        
        /* Footer */
        footer {{
            text-align: center;
            padding: 40px 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
            margin-top: 80px;
        }}
        
        footer p {{
            opacity: 0.8;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .hero h1 {{
                font-size: 40px;
            }}
            
            .hero p {{
                font-size: 18px;
            }}
            
            .nav-links {{
                display: none;
            }}
            
            .feature-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <nav class="container">
            <div class="logo">
                <i class="fas fa-rocket"></i>
                <span>Generated Site</span>
            </div>
            <ul class="nav-links">
                <li><a href="#home">Home</a></li>
                <li><a href="#features">Features</a></li>
                <li><a href="#about">About</a></li>
                <li><a href="#contact">Contact</a></li>
            </ul>
        </nav>
    </header>
    
    <section class="hero">
        <div class="container">
            <h1>Welcome to Your<br>Generated Website</h1>
            <p>Built with AI • Powered by Code Weaver</p>
            <div class="cta-buttons">
                <button class="btn btn-primary" onclick="handleGetStarted()">
                    <i class="fas fa-rocket"></i> Get Started
                </button>
                <button class="btn btn-secondary" onclick="handleLearnMore()">
                    <i class="fas fa-info-circle"></i> Learn More
                </button>
            </div>
        </div>
    </section>
    
    <section class="features" id="features">
        <div class="container">
            <h2>Amazing Features</h2>
            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-bolt"></i>
                    </div>
                    <h3>Lightning Fast</h3>
                    <p>Optimized for speed and performance with modern web technologies.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-mobile-alt"></i>
                    </div>
                    <h3>Fully Responsive</h3>
                    <p>Looks great on all devices, from mobile phones to desktop screens.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">
                        <i class="fas fa-shield-alt"></i>
                    </div>
                    <h3>Secure & Reliable</h3>
                    <p>Built with security best practices and modern web standards.</p>
                </div>
            </div>
        </div>
    </section>
    
    <footer>
        <div class="container">
            <p>&copy; 2025 Generated Website • Built with Code Weaver</p>
        </div>
    </footer>
    
    <script>
        function handleGetStarted() {{
            alert('Get Started clicked! This would normally redirect to a signup page.');
        }}
        
        function handleLearnMore() {{
            alert('Learn More clicked! This would show more information.');
        }}
        
        // Smooth scroll for navigation
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{
                        behavior: 'smooth',
                        block: 'start'
                    }});
                }}
            }});
        }});
        
        console.log('Website loaded successfully!');
    </script>
</body>
</html>"""

        # Extract CSS and JS for the separate tabs
        css_match = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
        css = css_match.group(1).strip() if css_match else ""
        
        js_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
        js = js_match.group(1).strip() if js_match else ""
        
        return {"html": html, "css": css, "js": js}

    async def _generate_backend(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, str]:
        """Generate Python FastAPI backend"""
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_backend",
            system_message="You are an expert backend developer. Generate production-ready FastAPI code."
        )
        chat.with_model(provider, model)
        
        backend_prompt = f"""Create a Python FastAPI backend for: {prompt}

Generate server.py with:
- FastAPI app
- CORS middleware
- RESTful routes
- MongoDB integration
- Pydantic models

Also provide requirements.txt.

Format:
```python
# server.py
[CODE]
```

```txt
# requirements.txt
[DEPENDENCIES]
```"""
        
        user_message = UserMessage(text=backend_prompt)
        response = await chat.send_message(user_message)
        
        python_code = self._extract_code_block(response, "python") or ""
        requirements = self._extract_code_block(response, "txt") or "fastapi==0.104.1\nuvicorn==0.24.0\nmotor==3.3.2\npydantic==2.5.0\npython-dotenv==1.0.0"
        
        return {"python": python_code, "requirements": requirements, "models": ""}

    async def _generate_readme(self, prompt: str, provider: str, model: str, session_id: str) -> str:
        """Generate README"""
        return f"# Generated Project\n\n{prompt}\n\n## Features\n- Modern UI\n- Responsive design\n- Working functionality"

    def _generate_package_json(self, prompt: str) -> str:
        return json.dumps({"name": "generated-app", "version": "1.0.0"}, indent=2)

    def _format_frameworks_knowledge(self) -> str:
        """Format comprehensive framework knowledge for AI"""
        output = ["═══════════════════════════════════════════════════════════════"]
        output.append("📚 COMPREHENSIVE FRAMEWORK & LIBRARY ACCESS")
        output.append("═══════════════════════════════════════════════════════════════\n")
        
        # Animation Libraries
        output.append("**ANIMATION LIBRARIES:**")
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

    async def _generate_fallback_project(self, prompt: str) -> Dict[str, Any]:
        """Complete fallback"""
        fallback = self._create_video_platform_fallback(prompt)
        
        return {
            "html_content": fallback['html'],
            "css_content": fallback['css'],
            "js_content": fallback['js'],
            "python_backend": "",
            "requirements_txt": "",
            "package_json": self._generate_package_json(prompt),
            "readme": f"# {prompt}",
            "files": [],
            "structure": {}
        }

    def _extract_code_block(self, text: str, language: str) -> Optional[str]:
        """Enhanced code block extraction with multiple fallback methods"""
        try:
            # Method 1: Standard markdown code block
            marker = f"```{language}"
            if marker in text:
                parts = text.split(marker)
                if len(parts) > 1:
                    code = parts[1].split("```")[0].strip()
                    if code:
                        logger.debug(f"Extracted {language} via standard marker: {len(code)} chars")
                        return code
            
            # Method 2: Code block without language specifier (```\n code \n```)
            if "```" in text:
                # Find all code blocks
                blocks = re.findall(r'```(?:\w+)?\s*(.*?)\s*```', text, re.DOTALL)
                for block in blocks:
                    # Check if this block looks like the requested language
                    if language == "html" and ("<!DOCTYPE" in block or "<html" in block):
                        logger.debug(f"Extracted HTML via generic code block: {len(block)} chars")
                        return block.strip()
                    elif language == "css" and ("{" in block and (":" in block or ";" in block)):
                        logger.debug(f"Extracted CSS via generic code block: {len(block)} chars")
                        return block.strip()
                    elif language in ["javascript", "js"] and ("function" in block or "const " in block or "let " in block or "var " in block):
                        logger.debug(f"Extracted JS via generic code block: {len(block)} chars")
                        return block.strip()
        except Exception as e:
            logger.error(f"Code extraction error: {e}")
        return None

    def _extract_html_direct(self, text: str) -> str:
        """Enhanced HTML extraction with multiple methods"""
        try:
            # Method 1: Standard DOCTYPE to </html>
            start = text.find("<!DOCTYPE")
            if start == -1:
                start = text.find("<html")
            if start != -1:
                end = text.rfind("</html>")
                if end != -1:
                    html = text[start:end + 7].strip()
                    logger.debug(f"Extracted HTML via DOCTYPE method: {len(html)} chars")
                    return html
            
            # Method 2: Find HTML even without DOCTYPE
            html_match = re.search(r'<html[^>]*>.*?</html>', text, re.DOTALL | re.IGNORECASE)
            if html_match:
                html = html_match.group(0)
                logger.debug(f"Extracted HTML via regex: {len(html)} chars")
                return html
                
        except Exception as e:
            logger.error(f"HTML extraction error: {e}")
        return ""

    async def generate_image(self, prompt: str) -> str:
        return "https://via.placeholder.com/800x600"
