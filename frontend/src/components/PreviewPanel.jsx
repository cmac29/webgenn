import React, { useState } from 'react';
import { Maximize2, Code, Download, ExternalLink } from 'lucide-react';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import Editor from '@monaco-editor/react';

export default function PreviewPanel({ website }) {
  const [activeTab, setActiveTab] = useState('preview');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const downloadCode = () => {
    if (!website) return;

    const blob = new Blob([website.html_content || ''], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'website.html';
    a.click();
    URL.revokeObjectURL(url);
  };

  const openInNewTab = () => {
    if (!website?.html_content) return;
    
    const newWindow = window.open('', '_blank');
    if (newWindow) {
      newWindow.document.open();
      newWindow.document.write(website.html_content);
      newWindow.document.close();
    } else {
      alert('Please allow pop-ups for this site to open in new tab');
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-900/30" data-testid="preview-panel">
      {/* Toolbar */}
      <div className="h-14 bg-slate-900/50 border-b border-slate-700 px-4 flex items-center justify-between">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="flex items-center justify-between">
            <TabsList className="bg-slate-800 border-slate-600">
              <TabsTrigger value="preview" className="data-[state=active]:bg-purple-600" data-testid="preview-tab">
                Preview
              </TabsTrigger>
              <TabsTrigger value="html" className="data-[state=active]:bg-purple-600" data-testid="html-tab">
                HTML
              </TabsTrigger>
              <TabsTrigger value="css" className="data-[state=active]:bg-purple-600" data-testid="css-tab">
                CSS
              </TabsTrigger>
              <TabsTrigger value="js" className="data-[state=active]:bg-purple-600" data-testid="js-tab">
                JavaScript
              </TabsTrigger>
              <TabsTrigger value="backend" className="data-[state=active]:bg-purple-600" data-testid="backend-tab">
                Backend
              </TabsTrigger>
              {website?.files && website.files.length > 0 && (
                <TabsTrigger value="files" className="data-[state=active]:bg-purple-600" data-testid="files-tab">
                  All Files ({website.files.length})
                </TabsTrigger>
              )}
            </TabsList>

            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={downloadCode}
                disabled={!website}
                className="text-slate-400 hover:text-slate-100"
                data-testid="download-button"
              >
                <Download className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={openInNewTab}
                disabled={!website}
                className="text-slate-400 hover:text-slate-100"
                data-testid="open-new-tab-button"
              >
                <ExternalLink className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </Tabs>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden">
        {!website ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="w-20 h-20 bg-slate-800 rounded-full mx-auto flex items-center justify-center">
                <Code className="w-10 h-10 text-slate-600" />
              </div>
              <p className="text-slate-400">
                Your generated website will appear here
              </p>
            </div>
          </div>
        ) : (
          <Tabs value={activeTab} className="h-full">
            <TabsContent value="preview" className="h-full m-0 p-0">
              {website.preview_url ? (
                <iframe
                  src={`${process.env.REACT_APP_BACKEND_URL || ''}${website.preview_url}`}
                  className="w-full h-full bg-white"
                  title="Website Preview"
                  sandbox="allow-scripts allow-same-origin allow-forms"
                  data-testid="preview-iframe"
                />
              ) : (
                <iframe
                  srcDoc={website.html_content}
                  className="w-full h-full bg-white"
                  title="Website Preview"
                  sandbox="allow-scripts allow-same-origin"
                  data-testid="preview-iframe"
                />
              )}
            </TabsContent>

            <TabsContent value="html" className="h-full m-0">
              <Editor
                height="100%"
                defaultLanguage="html"
                value={website.html_content || ''}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                }}
              />
            </TabsContent>

            <TabsContent value="css" className="h-full m-0">
              <Editor
                height="100%"
                defaultLanguage="css"
                value={website.css_content || '/* No additional CSS */'}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                }}
              />
            </TabsContent>

            <TabsContent value="js" className="h-full m-0">
              <Editor
                height="100%"
                defaultLanguage="javascript"
                value={website.js_content || '// No JavaScript'}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                }}
              />
            </TabsContent>

            <TabsContent value="backend" className="h-full m-0">
              <Editor
                height="100%"
                defaultLanguage="python"
                value={website.python_backend || '# No backend generated'}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                }}
              />
            </TabsContent>

            {website?.files && website.files.length > 0 && (
              <TabsContent value="files" className="h-full m-0 p-4 overflow-y-auto">
                <div className="space-y-2">
                  {website.files.map((file, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-800 rounded-lg p-4 border border-slate-700 hover:border-purple-600 transition-colors cursor-pointer"
                      onClick={() => setSelectedFile(file)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <span className="px-2 py-1 bg-purple-600 rounded text-xs font-mono">
                            {file.file_type}
                          </span>
                          <span className="text-slate-100 font-medium">{file.filename}</span>
                        </div>
                        <span className="text-xs text-slate-400">
                          {file.content?.length || 0} chars
                        </span>
                      </div>
                      {file.description && (
                        <p className="text-sm text-slate-400 mt-2">{file.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </TabsContent>
            )}
          </Tabs>
        )}
      </div>
    </div>
  );
}