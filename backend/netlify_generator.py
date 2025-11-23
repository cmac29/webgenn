"""
Netlify Code Generation Service
Generates deployment-ready, serverless code for Netlify platform
"""
import os
import logging
import json
from typing import Dict, Any, List, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage

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
        
        logger.info(f"🚀 NETLIFY PROJECT GENERATION")
        logger.info(f"   Model: {provider}/{model_name}")
        logger.info(f"   Prompt: {prompt}")
        
        # Determine if this is editing or new generation
        is_editing = current_project is not None and len(current_project.get("files", {})) > 0
        
        if is_editing:
            logger.info(f"📝 EDIT MODE: Modifying existing Netlify project")
            return await self._edit_netlify_project(prompt, current_project, provider, model_name, session_id)
        else:
            logger.info(f"🆕 NEW PROJECT: Creating from scratch")
            return await self._create_netlify_project(prompt, provider, model_name, session_id)
    
    async def _create_netlify_project(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, Any]:
        """Create a new Netlify project from scratch"""
        
        # Analyze user intent
        analysis = await self._analyze_project_requirements(prompt, provider, model, session_id)
        logger.info(f"Project analysis: {json.dumps(analysis, indent=2)}")
        
        # Generate the system prompt for Netlify-compatible code
        system_prompt = """You are an expert full-stack developer specializing in Netlify deployments.

🎯 MISSION: Generate production-ready, Netlify-compatible code that deploys instantly with Deploy Preview URLs.

═══════════════════════════════════════════════════════════════
CRITICAL NETLIFY REQUIREMENTS
═══════════════════════════════════════════════════════════════

1. **SERVERLESS ARCHITECTURE ONLY**
   - NO persistent servers (No Express.js, Flask, FastAPI)
   - ALL backend logic MUST be Netlify Functions
   - Functions go in `netlify/functions/` directory
   - Accessible via `/.netlify/functions/[function-name]`

2. **NETLIFY FUNCTIONS FORMAT**
   ```javascript
   // netlify/functions/api.js
   exports.handler = async (event, context) => {
       return {
           statusCode: 200,
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ message: 'Hello' })
       };
   };
   ```

3. **BUILD CONFIGURATION**
   - Must include `netlify.toml` in project root
   - Standard build command: `npm run build` or static
   - Publish directory: `dist`, `build`, `out`, or `.` (for static sites)
   - Example netlify.toml:
     ```toml
     [build]
       publish = "dist"
       functions = "netlify/functions"
     
     [[redirects]]
       from = "/api/*"
       to = "/.netlify/functions/:splat"
       status = 200
     ```

4. **DATABASE INTEGRATION**
   - Use API-based databases: Supabase, FaunaDB, Firebase
   - Environment variables via `process.env.VARIABLE_NAME`
   - Include placeholder keys with `// TODO: Add to Netlify Environment Variables`

5. **FRONTEND REQUIREMENTS**
   - React/Next.js preferred, or vanilla HTML/CSS/JS
   - Modern, responsive design with Tailwind CSS
   - API calls to `/.netlify/functions/[function-name]`
   - No hardcoded backend URLs

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT REQUIREMENTS
═══════════════════════════════════════════════════════════════

Generate code as a JSON object with this EXACT structure:

```json
{
  "files": {
    "index.html": "<!DOCTYPE html>...",
    "styles.css": "body { ... }",
    "app.js": "// JavaScript code",
    "netlify.toml": "[build]\\n  publish = \\".\\"\\n  functions = \\"netlify/functions\\"",
    "netlify/functions/api.js": "exports.handler = async ...",
    "netlify/functions/contact.js": "exports.handler = async ...",
    "package.json": "{ \\"name\\": \\"project\\" ... }",
    "README.md": "# Project Name\\n..."
  },
  "deploy_config": {
    "build_command": "npm run build",
    "publish_dir": "dist",
    "functions_dir": "netlify/functions",
    "environment_variables": {
      "SUPABASE_URL": "https://example.supabase.co",
      "SUPABASE_KEY": "your-key-here"
    }
  }
}
```

KEY POINTS:
- ALL file paths as keys (including subdirectories)
- File content as string values
- Escape special characters in strings
- Include ALL necessary files
- netlify.toml is REQUIRED
- Environment variables list what's needed

═══════════════════════════════════════════════════════════════
"""
        
        # Build user prompt based on analysis
        needs_backend = analysis.get("needs_backend", False)
        needs_database = analysis.get("needs_database", False)
        framework = analysis.get("framework", "vanilla")
        
        user_prompt = f"""Generate a complete Netlify-deployable project for:

{prompt}

PROJECT SPECIFICATIONS:
- Type: {analysis.get('project_type', 'web app')}
- Framework: {framework}
- Backend Required: {needs_backend}
- Database Required: {needs_database}
- Features: {', '.join(analysis.get('features', []))}

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
- Make it production-ready and beautiful
- Use modern design patterns (gradients, shadows, animations)
- Ensure mobile responsiveness

OUTPUT AS JSON with structure shown above."""

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_prompt
            )
            chat.with_model(provider, model)
            
            response = await chat.send_message(UserMessage(text=user_prompt))
            logger.info(f"AI Response received: {len(response)} characters")
            
            # Parse the JSON response
            project_data = self._parse_project_response(response)
            
            if not project_data.get("files"):
                logger.error("No files in response, generating fallback")
                project_data = self._generate_fallback_project(prompt, analysis)
            
            # Validate Netlify requirements
            self._validate_netlify_project(project_data)
            
            logger.info(f"✅ Generated {len(project_data['files'])} files")
            return project_data
            
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            # Return fallback project
            return self._generate_fallback_project(prompt, analysis)
    
    async def _edit_netlify_project(self, prompt: str, current_project: Dict, provider: str, model: str, session_id: str) -> Dict[str, Any]:
        """Edit an existing Netlify project"""
        
        current_files = current_project.get("files", {})
        logger.info(f"Editing project with {len(current_files)} existing files")
        
        system_prompt = """You are an expert full-stack developer editing a Netlify-deployed project.

🔄 EDITING MODE - PRESERVE EXISTING STRUCTURE

CRITICAL RULES:
1. You are EDITING existing code, NOT creating from scratch
2. PRESERVE all existing files unless explicitly asked to remove them
3. Make SURGICAL changes - only modify what's requested
4. Maintain Netlify Functions format and structure
5. Keep netlify.toml configuration unless changes are needed
6. Return the COMPLETE project with modifications

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
            logger.info(f"Edit response received: {len(response)} characters")
            
            # Parse edited project
            edited_project = self._parse_project_response(response)
            
            if not edited_project.get("files"):
                logger.warning("Edit failed, returning original project")
                return current_project
            
            logger.info(f"✅ Edit complete: {len(edited_project['files'])} files")
            return edited_project
            
        except Exception as e:
            logger.error(f"Edit failed: {str(e)}")
            return current_project
    
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
            # Try to find JSON block
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                project_data = json.loads(json_str)
                return project_data
            else:
                logger.error("No JSON found in response")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
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
