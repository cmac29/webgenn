import os
import logging
import json
import base64
from typing import Dict, Any, List, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage

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
        return model_map.get(model, ("anthropic", "claude-4-sonnet-20250514"))

    async def generate_response(self, prompt: str, model: str, session_id: str) -> Dict[str, Any]:
        """
        Generate AI response for user prompt
        """
        provider, model_name = self._get_model_config(model)
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message="You are Code Weaver, an expert AI assistant that helps users create professional websites. You understand web design, modern frameworks, and can generate clean, production-ready code. Always be helpful, creative, and provide clear explanations."
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

    async def generate_website(self, prompt: str, model: str, framework: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        """
        Multi-agent website generation process:
        1. Requirement Planner Agent - Creates structured plan
        2. Code Generation Agent - Generates actual code
        3. Design & Styling Agent - Creates visual assets
        """
        provider, model_name = self._get_model_config(model)
        session_id = f"gen_{os.urandom(8).hex()}"
        
        try:
            # Step 1: Planning Agent
            planning_result = await self._planning_agent(prompt, provider, model_name, session_id)
            
            # Step 2: Code Generation Agent
            code_result = await self._code_generation_agent(planning_result, prompt, provider, model_name, session_id, framework)
            
            # Validate generated code
            if not code_result.get('html_content') or len(code_result.get('html_content', '')) < 100:
                # Fallback to direct generation if planning failed
                logger.warning("Planning-based generation failed, using direct generation")
                code_result = await self._direct_code_generation(prompt, provider, model_name, session_id, framework)
            
            return code_result
        except Exception as e:
            logger.error(f"Website generation failed: {str(e)}")
            # Return fallback website
            return await self._direct_code_generation(prompt, provider, model_name, session_id, framework)

    async def _planning_agent(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, Any]:
        """
        Requirement Planner Agent - Analyzes prompt and creates structured plan
        """
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_planner",
            system_message="""You are a website planning expert. Analyze user requirements and create a detailed JSON structure.
Output ONLY valid JSON with this structure:
{
  "pages": ["Home", "About", "Contact"],
  "sections": {
    "Home": ["Hero", "Features", "CTA"],
    "About": ["Story", "Team"],
    "Contact": ["Form", "Info"]
  },
  "style": {
    "theme": "modern/minimal/corporate/creative",
    "colors": {"primary": "#color", "secondary": "#color"},
    "typography": "font-family"
  },
  "features": ["responsive", "animations", "forms"]
}"""
        )
        chat.with_model(provider, model)
        
        user_message = UserMessage(
            text=f"Analyze this website request and create a JSON plan: {prompt}"
        )
        
        response = await chat.send_message(user_message)
        
        # Try to parse JSON from response
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            plan = json.loads(json_str)
            return plan
        except:
            # Fallback plan if JSON parsing fails
            return {
                "pages": ["Home"],
                "sections": {"Home": ["Hero", "Features", "About", "Contact"]},
                "style": {"theme": "modern", "colors": {"primary": "#3b82f6", "secondary": "#8b5cf6"}},
                "features": ["responsive"]
            }

    async def _code_generation_agent(self, plan: Dict, original_prompt: str, provider: str, model: str, session_id: str, framework: str) -> Dict[str, Any]:
        """
        Code Generation Agent - Generates actual HTML/CSS/JS code
        """
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_coder",
            system_message=f"""You are an expert web developer specializing in creating beautiful, functional websites.

IMPORTANT RULES:
1. Generate COMPLETE, WORKING HTML code with embedded CSS and JavaScript
2. Use modern design practices with proper spacing, colors, and typography
3. Make it fully responsive (mobile, tablet, desktop)
4. Include ALL necessary elements and functionality requested
5. Use semantic HTML5 tags
6. Add smooth animations and transitions
7. Ensure proper contrast and accessibility
8. Generate realistic content and text (not just placeholders)

For styling:
- Use embedded <style> tags in the HTML
- Use modern CSS with flexbox/grid
- Add hover effects and transitions
- Use professional color schemes
- Implement responsive breakpoints

For JavaScript:
- Use vanilla JavaScript (no dependencies)
- Add interactivity where needed
- Include event listeners and functionality
- Make it production-ready"""
        )
        chat.with_model(provider, model)
        
        prompt = f"""Create a complete, functional website based on this request:

USER REQUEST: {original_prompt}

PLAN: {json.dumps(plan, indent=2)}

Generate a COMPLETE HTML file with:
1. Full HTML structure (doctype, head, body)
2. Embedded CSS in <style> tags (make it beautiful and responsive)
3. Embedded JavaScript in <script> tags (add all necessary functionality)
4. Realistic content (not just placeholders)
5. All sections and features from the plan

IMPORTANT:
- Generate ONE complete HTML file with everything embedded
- Make it look professional and modern
- Include all navigation, sections, and interactive elements
- Use proper semantic HTML
- Add CSS for responsive design
- Include JavaScript for any dynamic features

Format your response with ONLY the HTML code inside triple backticks:

```html
[COMPLETE HTML CODE HERE]
```

Do NOT add any explanations before or after the code."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Extract HTML code
        html_content = self._extract_code_block(response, "html")
        
        if not html_content or len(html_content) < 100:
            # Try without language specifier
            if "```" in response:
                parts = response.split("```")
                for i in range(1, len(parts), 2):
                    potential_html = parts[i].strip()
                    if potential_html.startswith("<!DOCTYPE") or potential_html.startswith("<html"):
                        html_content = potential_html
                        break
        
        # Validate HTML
        if not html_content:
            html_content = response  # Use full response as fallback
        
        # Ensure HTML has DOCTYPE and basic structure
        if not html_content.strip().startswith("<!DOCTYPE"):
            html_content = f"<!DOCTYPE html>\n{html_content}"
        
        return {
            "html_content": html_content,
            "css_content": "",  # CSS is embedded in HTML
            "js_content": "",   # JS is embedded in HTML
            "structure": plan
        }

    async def _direct_code_generation(self, prompt: str, provider: str, model: str, session_id: str, framework: str) -> Dict[str, Any]:
        """
        Direct code generation without planning step (fallback method)
        """
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_direct",
            system_message="""You are an expert web developer. Generate complete, working HTML websites.

RULES:
1. Output ONLY HTML code (with embedded CSS and JS)
2. Make it beautiful, modern, and fully functional
3. Include ALL requested features and sections
4. Use responsive design
5. Add realistic content (not placeholders)
6. Embed CSS in <style> tags
7. Embed JavaScript in <script> tags
8. Make it production-ready"""
        )
        chat.with_model(provider, model)
        
        user_message = UserMessage(
            text=f"""Create a complete, functional website for:

{prompt}

Generate ONE complete HTML file with everything embedded (CSS and JavaScript).
Make it beautiful, modern, and fully functional.
Include all requested features and sections.

Output format:
```html
[YOUR COMPLETE HTML CODE]
```

Only output the HTML code, nothing else."""
        )
        
        response = await chat.send_message(user_message)
        
        # Extract HTML
        html_content = self._extract_code_block(response, "html")
        
        if not html_content:
            # Try to find HTML in response
            if "```" in response:
                parts = response.split("```")
                for i in range(1, len(parts), 2):
                    potential_html = parts[i].strip()
                    # Remove language identifier
                    if potential_html.startswith("html\n"):
                        potential_html = potential_html[5:]
                    if "<html" in potential_html or "<!DOCTYPE" in potential_html:
                        html_content = potential_html
                        break
        
        if not html_content or len(html_content) < 100:
            html_content = response
        
        # Ensure DOCTYPE
        if not html_content.strip().startswith("<!DOCTYPE"):
            html_content = f"<!DOCTYPE html>\n{html_content}"
        
        return {
            "html_content": html_content,
            "css_content": "",
            "js_content": "",
            "structure": {}
        }

    def _extract_code_block(self, text: str, language: str) -> Optional[str]:
        """Extract code from markdown code blocks"""
        try:
            marker = f"```{language}"
            if marker in text:
                parts = text.split(marker)
                if len(parts) > 1:
                    code = parts[1].split("```")[0].strip()
                    return code
            return None
        except:
            return None

    async def generate_image(self, prompt: str) -> str:
        """
        Generate image using Gemini Imagen (nano-banana)
        """
        session_id = f"img_{os.urandom(8).hex()}"
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message="You are a helpful AI assistant that generates images."
            )
            chat.with_model("gemini", "gemini-2.5-flash-image-preview").with_params(modalities=["image", "text"])
            
            msg = UserMessage(text=f"Create an image: {prompt}")
            text, images = await chat.send_message_multimodal_response(msg)
            
            if images and len(images) > 0:
                # Return base64 encoded image
                return f"data:{images[0]['mime_type']};base64,{images[0]['data']}"
            else:
                raise Exception("No image generated")
        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
            # Return placeholder
            return "https://via.placeholder.com/800x600?text=Image+Generation+Placeholder"