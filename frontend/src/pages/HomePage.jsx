import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ChatInterface from '../components/ChatInterface';
import PreviewPanel from '../components/PreviewPanel';
import SessionList from '../components/SessionList';
import Header from '../components/Header';
import { Toaster, toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function HomePage() {
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [generatedWebsite, setGeneratedWebsite] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('claude-sonnet-4');
  const [generationSteps, setGenerationSteps] = useState([]);

  useEffect(() => {
    // Load sessions first
    const storedSessions = JSON.parse(localStorage.getItem('sessions') || '[]');
    setSessions(storedSessions);
    
    // Create initial session if no sessions exist
    if (storedSessions.length === 0) {
      createSession();
    } else {
      // Set the most recent session as active
      setSessionId(storedSessions[0].session_id);
    }
  }, []);

  useEffect(() => {
    // Load messages and website when session changes
    if (sessionId) {
      loadMessages(sessionId);
      loadLatestWebsite(sessionId);
    }
  }, [sessionId]);

  const createSession = async (projectName = 'New Website Project') => {
    try {
      const response = await axios.post(`${API}/session/create`, {
        project_name: projectName
      });
      
      const newSession = response.data;
      setSessionId(newSession.session_id);
      
      // Save to localStorage
      const storedSessions = JSON.parse(localStorage.getItem('sessions') || '[]');
      storedSessions.unshift(newSession);
      localStorage.setItem('sessions', JSON.stringify(storedSessions));
      setSessions(storedSessions);
      
      // Clear current state
      setMessages([]);
      setGeneratedWebsite(null);
      
      toast.success('New project created!');
      return newSession.session_id;
    } catch (error) {
      console.error('Failed to create session:', error);
      toast.error('Failed to create session');
      return null;
    }
  };

  const renameSession = async (sessionId, newName) => {
    try {
      // Update in localStorage
      const storedSessions = JSON.parse(localStorage.getItem('sessions') || '[]');
      const updatedSessions = storedSessions.map(s => 
        s.session_id === sessionId ? { ...s, project_name: newName } : s
      );
      localStorage.setItem('sessions', JSON.stringify(updatedSessions));
      setSessions(updatedSessions);
      toast.success('Project renamed!');
    } catch (error) {
      console.error('Failed to rename session:', error);
      toast.error('Failed to rename project');
    }
  };

  const selectSession = async (newSessionId) => {
    if (newSessionId === sessionId) return; // Already selected
    
    setSessionId(newSessionId);
    setMessages([]);
    setGeneratedWebsite(null);
    // Messages and website will be loaded by useEffect
  };

  const loadMessages = async (sessionId) => {
    try {
      const response = await axios.get(`${API}/session/${sessionId}/messages`);
      setMessages(response.data);
      console.log(`Loaded ${response.data.length} messages for session ${sessionId}`);
    } catch (error) {
      console.error('Failed to load messages:', error);
      setMessages([]);
    }
  };

  const loadLatestWebsite = async (sessionId) => {
    try {
      const response = await axios.get(`${API}/website/${sessionId}/latest`);
      setGeneratedWebsite(response.data);
      console.log('Loaded website for session', sessionId);
    } catch (error) {
      // No website yet, that's ok
      setGeneratedWebsite(null);
    }
  };

  const sendMessage = async (message) => {
    if (!sessionId) {
      toast.error('No active session');
      return;
    }

    // CRITICAL: If a website already exists in this session, ALWAYS edit it (never create new)
    if (generatedWebsite) {
      console.log('🔒 EDIT-ONLY MODE: Website exists - routing to edit/modify existing website');
      await generateWebsite(message);
      return;
    }

    // Check if message is asking for website generation or modification
    const isWebsiteRequest = detectWebsiteIntent(message);
    
    if (isWebsiteRequest) {
      // Route to website generation instead of chat
      console.log('🔄 Detected website generation/modification request - routing to generateWebsite');
      await generateWebsite(message);
      return;
    }

    setIsLoading(true);
    
    // Add user message immediately
    const userMsg = { role: 'user', content: message, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);

    try {
      const response = await axios.post(`${API}/chat/message`, {
        session_id: sessionId,
        message: message,
        model: selectedModel
      });

      // Add assistant message
      const assistantMsg = {
        role: 'assistant',
        content: response.data.content,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, assistantMsg]);

      // If website data is included
      if (response.data.website_data) {
        setGeneratedWebsite(response.data.website_data);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
      
      // Remove user message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const detectWebsiteIntent = (message) => {
    const lowerMessage = message.toLowerCase();
    
    // Keywords indicating website generation/modification
    const generationKeywords = [
      'create', 'build', 'make', 'generate', 'design',
      'add', 'modify', 'change', 'update', 'edit',
      'remove', 'delete', 'fix', 'improve', 'enhance',
      'website', 'page', 'site', 'clone', 'app',
      'button', 'section', 'feature', 'component',
      'color', 'style', 'layout', 'header', 'footer',
      'navigation', 'nav', 'menu', 'sidebar'
    ];
    
    // Check if message contains any generation keywords
    return generationKeywords.some(keyword => lowerMessage.includes(keyword));
  };

  const generateWebsite = async (prompt) => {
    if (!sessionId) {
      toast.error('No active session');
      return;
    }

    setIsLoading(true);
    
    // Add user message to UI
    const userMsg = { role: 'user', content: prompt, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    
    // IMPORTANT: Save user message to backend first
    try {
      await axios.post(`${API}/chat/message`, {
        session_id: sessionId,
        message: prompt,
        model: selectedModel
      });
    } catch (error) {
      console.error('Failed to save user message:', error);
    }
    
    // Initialize generation steps
    setGenerationSteps([
      { title: 'Understanding Requirements', description: 'Analyzing your request and planning the website structure...', status: 'active' },
      { title: 'Designing Layout', description: 'Creating visual design, color schemes, and component layout...', status: 'pending' },
      { title: 'Writing Code', description: 'Generating HTML, CSS, and JavaScript for full functionality...', status: 'pending' },
      { title: 'Final Polish', description: 'Optimizing code and ensuring responsiveness...', status: 'pending' }
    ]);

    try {
      // Step 1: Planning
      await new Promise(resolve => setTimeout(resolve, 1500));
      setGenerationSteps(prev => prev.map((step, idx) => 
        idx === 0 ? { ...step, status: 'complete' } :
        idx === 1 ? { ...step, status: 'active' } : step
      ));

      // Step 2: Design
      await new Promise(resolve => setTimeout(resolve, 1500));
      setGenerationSteps(prev => prev.map((step, idx) => 
        idx === 1 ? { ...step, status: 'complete' } :
        idx === 2 ? { ...step, status: 'active' } : step
      ));

      // Step 3: Code Generation & Netlify Deployment (actual API call)
      const response = await axios.post(`${API}/netlify/generate-and-deploy`, {
        session_id: sessionId,
        prompt: prompt,
        model: selectedModel,
        edit_mode: generatedWebsite !== null
      });

      setGenerationSteps(prev => prev.map((step, idx) => 
        idx === 2 ? { ...step, status: 'complete' } :
        idx === 3 ? { ...step, status: 'active' } : step
      ));

      // Step 4: Optimization
      await new Promise(resolve => setTimeout(resolve, 1000));
      setGenerationSteps(prev => prev.map(step => ({ ...step, status: 'complete' })));

      setGeneratedWebsite(response.data);
      
      // Add success message
      const successMsg = {
        role: 'assistant',
        content: `✅ I've successfully generated your website! You can see it in the preview panel on the right. Feel free to:
- View the HTML, CSS, and JavaScript tabs to see the code
- Download the code using the download button
- Open it in a new tab for full-screen viewing
- Ask me to make any changes or improvements!`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, successMsg]);
      
      toast.success('Website generated successfully!');
    } catch (error) {
      console.error('Failed to generate website:', error);
      toast.error('Failed to generate website. Please try again.');
      
      // Add error message
      const errorMsg = {
        role: 'assistant',
        content: 'I apologize, but I encountered an error while generating your website. Please try again with a different description or simpler requirements.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMsg]);
      
      setGenerationSteps([]);
    } finally {
      setIsLoading(false);
      setTimeout(() => setGenerationSteps([]), 3000);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900" data-testid="homepage">
      <Toaster position="top-right" richColors />
      
      <Header 
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
      />

      <div className="flex h-[calc(100vh-4rem)]">
        {/* Session List Sidebar */}
        <SessionList
          sessions={sessions}
          currentSessionId={sessionId}
          onSelectSession={selectSession}
          onCreateSession={() => createSession()}
          onRenameSession={renameSession}
        />

        {/* Chat Panel */}
        <div className="flex-1 border-r border-slate-700">
          <ChatInterface
            messages={messages}
            onSendMessage={sendMessage}
            onGenerateWebsite={generateWebsite}
            isLoading={isLoading}
            sessionId={sessionId}
            generationSteps={generationSteps}
          />
        </div>

        {/* Preview Panel */}
        <div className="flex-1">
          <PreviewPanel website={generatedWebsite} />
        </div>
      </div>
    </div>
  );
}