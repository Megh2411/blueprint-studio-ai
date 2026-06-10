import { useState, useRef, useEffect } from 'react';
import { Sparkles, Eraser, Download, Loader2, SlidersHorizontal, Settings2, Upload, Activity, Wand2, Paintbrush, Palette, Sliders } from 'lucide-react';
// 1. Importing the Gallery
import Gallery from './components/Gallery';

export default function App() {
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const socketRef = useRef(null);
  
  // Using the valid User ID from your 'users' database table
  // Frictionless Auth: Get existing ID from browser, or generate a new one!
  const [clientId] = useState(() => {
    let storedId = localStorage.getItem('blueprint_session_id');
    if (!storedId) {
      storedId = crypto.randomUUID(); // Generates a standard UUIDv4
      localStorage.setItem('blueprint_session_id', storedId);
    }
    return storedId;
  });
  const [isDrawing, setIsDrawing] = useState(false);
  const [canvasMode, setCanvasMode] = useState('sketch'); 
  const [prompt, setPrompt] = useState('A brutalist concrete house in a lush forest, cinematic lighting');
  const [isRendering, setIsRendering] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [resultImage, setResultImage] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [galleryRefreshTrigger, setGalleryRefreshTrigger] = useState(0);

  // Brush Settings
  const [brushColor, setBrushColor] = useState('#000000');
  const [brushSize, setBrushSize] = useState(4);

  // Post-Processing Settings
  const [showPostProcess, setShowPostProcess] = useState(false);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [saturation, setSaturation] = useState(100);

  // Hyperparameters
  const [showSettings, setShowSettings] = useState(false);
  const [controlStrength, setControlStrength] = useState(0.7);
  const [steps, setSteps] = useState(25);
  const [cfgScale, setCfgScale] = useState(7.0);

  useEffect(() => {
    clearCanvas();
    let socket;
    let reconnectTimeout;

    const connectWebSocket = () => {
      console.log("[WEBSOCKET] Connecting...");
      socket = new WebSocket(`ws://127.0.0.1:8000/ws/${clientId}`);
      socketRef.current = socket;

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.status === 'completed') {
          setResultImage(data.render_path);
          setMetrics(data.metrics);
          setIsRendering(false);
          setGalleryRefreshTrigger(prev => prev + 1);
        } else if (data.status === 'failed') {
          setIsRendering(false);
          alert("Render failed. Check backend logs.");
        }
      };

      socket.onclose = (e) => {
        console.log("[WEBSOCKET] Connection closed. Attempting reconnect in 3s...", e.reason);
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
      };

      socket.onerror = (err) => {
        console.error("[WEBSOCKET] Error:", err);
        socket.close();
      };
    };

    connectWebSocket();

    return () => {
      clearTimeout(reconnectTimeout);
      if (socket) {
        socket.close();
      }
    };
  }, [clientId]);

  const startDrawing = (e) => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    // Support for both Mouse and Touch
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    
    ctx.beginPath();
    ctx.moveTo(clientX - rect.left, clientY - rect.top);
    setIsDrawing(true);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    // Support for both Mouse and Touch
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    
    ctx.lineTo(clientX - rect.left, clientY - rect.top);
    
    ctx.strokeStyle = canvasMode === 'mask' ? 'rgba(236, 72, 153, 0.6)' : brushColor;
    ctx.lineWidth = canvasMode === 'mask' ? 24 : brushSize;
    ctx.lineCap = 'round';
    ctx.stroke();
  };
  const stopDrawing = () => setIsDrawing(false);

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    setResultImage(null);
    setMetrics(null);
    // Reset filters
    setBrightness(100);
    setContrast(100);
    setSaturation(100);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  };

  const handleOptimizePrompt = async () => {
    if (!prompt) return;
    setIsOptimizing(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/prompt/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });
      if (!response.ok) throw new Error("API Route Missing");
      const data = await response.json();
      setPrompt(data.optimized_prompt);
    } catch (err) {
      console.error("Optimization failed:", err);
      alert("Magic Enhance failed. Is your GEMINI_API_KEY set in the backend .env?");
    } finally {
      setIsOptimizing(false);
    }
  };

  // Mathematical Filter Baking Download
  const handleDownload = () => {
    if (!resultImage) return;

    const img = new Image();
    img.crossOrigin = "anonymous"; 
    img.src = resultImage;
    
    img.onload = () => {
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = img.width;
      tempCanvas.height = img.height;
      const ctx = tempCanvas.getContext('2d');

      ctx.filter = `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturation}%)`;
      ctx.drawImage(img, 0, 0, tempCanvas.width, tempCanvas.height);

      const url = tempCanvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = url;
      a.download = `blueprint-pro-${Date.now()}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    };
  };

  const handleGenerate = async () => {
    if (!prompt) return alert("Please enter a prompt!");
    setIsRendering(true);
    setMetrics(null);
    
    const canvas = canvasRef.current;
    const base64Image = canvas.toDataURL('image/png');

    try {
      await fetch('http://127.0.0.1:8000/api/renders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: clientId,
          prompt: prompt,
          sketch_base64: base64Image,
          mode: canvasMode,
          control_strength: controlStrength,
          steps: steps,
          cfg_scale: cfgScale
        })
      });
    } catch (error) {
      console.error(error);
      setIsRendering(false);
    }
  };

  const handleLoadJob = (job) => {
    setPrompt(job.prompt);
    setResultImage(job.render_path);
    if (job.metrics) {
      setMetrics(job.metrics);
    }
    
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = job.sketch_path;
    img.onload = () => {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
  };

  const handleLoadRenderAsSketch = (imageUrl) => {
    if (!imageUrl) return;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = imageUrl;
    img.onload = () => {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
  };


  return (
    <div className="min-h-screen bg-[#0E111A] text-slate-100 flex flex-col items-center py-12 px-4 selection:bg-indigo-500 selection:text-white">
      
      <div className="text-center mb-12">
        <h1 className="text-5xl font-extrabold tracking-tight mb-4 flex items-center justify-center gap-3">
          Blueprint <span className="text-indigo-400 bg-indigo-500/10 px-3.5 py-1.5 rounded-xl border border-indigo-500/20 font-mono tracking-wider text-4xl">Studio AI</span>
        </h1>
        <p className="text-slate-400 text-lg max-w-xl mx-auto">Iterative Sketch-to-Render Architecture Engine powered by Latent Diffusion</p>
      </div>

      <div className="w-full max-w-7xl grid grid-cols-1 lg:grid-cols-12 gap-8 mb-16">
        
        {/* Left Column: Canvas */}
        <div className="lg:col-span-5 backdrop-blur-md bg-white/[0.02] border border-white/10 rounded-2xl p-6 shadow-xl flex flex-col transition-all duration-300 hover:border-white/15">
          <div className="flex justify-between items-center mb-4">
            <div className="flex bg-black/30 p-1 rounded-xl border border-white/5 gap-1">
              <button 
                onClick={() => setCanvasMode('sketch')}
                className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all duration-200 ${canvasMode === 'sketch' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'}`}
              >
                <Paintbrush size={14} /> Structure
              </button>
              <button 
                onClick={() => setCanvasMode('mask')}
                className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all duration-200 ${canvasMode === 'mask' ? 'bg-pink-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'}`}
              >
                <Eraser size={14} /> Inpaint Mask
              </button>
            </div>
            
            <div className="flex gap-4">
              <input type="file" accept="image/*" ref={fileInputRef} onChange={handleFileUpload} className="hidden" />
              <button onClick={() => fileInputRef.current?.click()} className="flex items-center gap-1.5 text-sm text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                <Upload size={14} /> Upload
              </button>
              <button onClick={clearCanvas} className="text-sm text-slate-400 hover:text-white transition-colors">Clear</button>
            </div>
          </div>

          {/* Brush Controls */}
          {canvasMode === 'sketch' && (
            <div className="flex items-center gap-4 mb-4 p-3 bg-black/30 rounded-xl border border-white/5">
               <div className="flex items-center gap-2.5 text-xs text-slate-400 font-medium">
                  <Palette size={14} className="text-indigo-400" /> Color
                  <input type="color" value={brushColor} onChange={(e) => setBrushColor(e.target.value)} className="w-6 h-6 rounded cursor-pointer bg-transparent border-0" />
               </div>
               <div className="flex items-center gap-2.5 text-xs text-slate-400 flex-1 font-medium">
                  <span>Size ({brushSize}px)</span>
                  <input type="range" min="1" max="20" value={brushSize} onChange={(e) => setBrushSize(parseInt(e.target.value))} className="w-full accent-indigo-500 cursor-pointer" />
               </div>
            </div>
          )}
          
          <div className="bg-white rounded-xl overflow-hidden border border-white/10 shadow-inner cursor-crosshair flex-1 relative">
            <canvas
              ref={canvasRef}
              width={512}
              height={512}
              onMouseDown={startDrawing}
              onMouseMove={draw}
              onMouseUp={stopDrawing}
              onMouseLeave={stopDrawing}
              onTouchStart={startDrawing}
              onTouchMove={draw}
              onTouchEnd={stopDrawing}
              onTouchCancel={stopDrawing}
              className="w-full h-auto aspect-square object-cover"
              style={{ touchAction: 'none' }}
            />
          </div>
        </div>

        {/* Center Column: Controls */}
        <div className="lg:col-span-3 flex flex-col gap-6">
          <div className="backdrop-blur-md bg-white/[0.02] border border-white/10 rounded-2xl p-6 shadow-xl flex-1 flex flex-col transition-all duration-300 hover:border-white/15">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-slate-200">Conditioning</h2>
              <button 
                onClick={handleOptimizePrompt}
                disabled={isOptimizing}
                className="text-xs bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 hover:bg-purple-500/20 transition-all font-medium"
              >
                {isOptimizing ? <Loader2 size={12} className="animate-spin" /> : <Wand2 size={12} />}
                Magic Enhance
              </button>
            </div>
            
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="w-full bg-black/30 border border-white/10 rounded-xl p-4 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 h-32 mb-4 resize-none transition-all duration-300"
              placeholder="Describe your architectural design..."
            />

            <button 
              onClick={() => setShowSettings(!showSettings)}
              className="flex items-center justify-between w-full p-3 bg-white/[0.04] rounded-xl text-sm text-slate-300 mb-4 hover:bg-white/[0.08] border border-white/5 transition-all"
            >
              <div className="flex items-center gap-2"><Settings2 size={16} className="text-indigo-400" /> Hyperparameters</div>
              <SlidersHorizontal size={16} className={showSettings ? "text-indigo-400 rotate-180" : "transition-transform"} />
            </button>

            {showSettings && (
              <div className="space-y-4 mb-6 p-4 bg-black/40 rounded-xl border border-white/5 text-sm transition-all duration-300">
                <div>
                  <div className="flex justify-between text-slate-400 mb-1 font-medium text-xs">
                    <span>Control Strength</span>
                    <span className="text-indigo-400">{controlStrength}</span>
                  </div>
                  <input type="range" min="0.0" max="1.0" step="0.1" value={controlStrength} onChange={(e) => setControlStrength(parseFloat(e.target.value))} className="w-full accent-indigo-500 cursor-pointer" />
                </div>
                <div>
                  <div className="flex justify-between text-slate-400 mb-1 font-medium text-xs">
                    <span>DDIM Steps (S)</span>
                    <span className="text-indigo-400">{steps}</span>
                  </div>
                  <input type="range" min="10" max="50" step="1" value={steps} onChange={(e) => setSteps(parseInt(e.target.value))} className="w-full accent-indigo-500 cursor-pointer" />
                </div>
                <div>
                  <div className="flex justify-between text-slate-400 mb-1 font-medium text-xs">
                    <span>CFG Scale</span>
                    <span className="text-indigo-400">{cfgScale}</span>
                  </div>
                  <input type="range" min="1.0" max="15.0" step="0.5" value={cfgScale} onChange={(e) => setCfgScale(parseFloat(e.target.value))} className="w-full accent-indigo-500 cursor-pointer" />
                </div>
              </div>
            )}
            
            <div className="mt-auto">
              <button
                onClick={handleGenerate}
                disabled={isRendering}
                className={`w-full py-4 rounded-xl font-semibold text-lg flex items-center justify-center gap-3 transition-all duration-300 ${
                  isRendering ? 'bg-indigo-600/40 text-slate-400 cursor-not-allowed' : 'bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white shadow-lg shadow-indigo-500/20 hover:-translate-y-0.5'
                }`}
              >
                {isRendering ? <Loader2 className="animate-spin" size={24} /> : <Sparkles size={24} />}
                {isRendering ? 'Denoising Latents...' : 'Execute Run'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Output */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          <div className="backdrop-blur-md bg-white/[0.02] border border-white/10 rounded-2xl p-6 shadow-xl flex-1 flex flex-col justify-center items-center relative overflow-hidden group min-h-[400px] transition-all duration-300 hover:border-white/15">
            {resultImage ? (
              <>
                <img 
                  src={resultImage} 
                  alt="Rendered result" 
                  className="w-full h-full object-cover rounded-xl transition-all duration-200"
                  style={{ filter: `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturation}%)` }}
                />
                
                {metrics && (
                  <div className="absolute top-4 left-4 bg-black/80 backdrop-blur-md border border-white/10 p-3 rounded-lg flex flex-col gap-1.5">
                    <div className="flex items-center gap-2 text-xs text-slate-300 font-mono">
                      <Activity size={14} className="text-indigo-400 animate-pulse" /> Telemetry
                    </div>
                    <div className="text-xs text-slate-400 font-mono">CLIP: <span className="text-white">{metrics.clipScore}</span></div>
                    <div className="text-xs text-slate-400 font-mono">SSIM: <span className="text-white">{metrics.ssim}</span></div>
                  </div>
                )}
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col gap-3 items-center justify-center">
                  <button onClick={handleDownload} className="bg-white text-black px-6 py-2 rounded-full font-semibold flex items-center gap-2 hover:scale-105 transition-transform text-sm w-48 justify-center">
                    <Download size={16} /> Download High-Res
                  </button>
                  <button onClick={() => handleLoadRenderAsSketch(resultImage)} className="bg-indigo-600 text-white px-6 py-2 rounded-full font-semibold flex items-center gap-2 hover:scale-105 transition-transform text-sm w-48 justify-center">
                    <Paintbrush size={16} /> Send Render to Canvas
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center text-slate-500">
                <Sparkles size={48} className="mx-auto mb-4 opacity-15" />
                <p className="font-mono text-sm">Awaiting Latent Diffusion</p>
              </div>
            )}
          </div>

          {resultImage && (
            <div className="backdrop-blur-md bg-white/[0.02] border border-white/10 rounded-xl p-4 transition-all duration-300 hover:border-white/15">
               <button 
                onClick={() => setShowPostProcess(!showPostProcess)}
                className="flex items-center justify-between w-full text-sm font-semibold text-slate-200"
              >
                <div className="flex items-center gap-2"><Sliders size={16} className="text-indigo-400"/> Post-Processing</div>
              </button>
              
              {showPostProcess && (
                <div className="space-y-3 mt-4 text-xs">
                  <div>
                    <div className="flex justify-between text-slate-400 mb-1"><span>Brightness</span><span>{brightness}%</span></div>
                    <input type="range" min="50" max="150" value={brightness} onChange={(e) => setBrightness(e.target.value)} className="w-full accent-indigo-500 cursor-pointer" />
                  </div>
                  <div>
                    <div className="flex justify-between text-slate-400 mb-1"><span>Contrast</span><span>{contrast}%</span></div>
                    <input type="range" min="50" max="150" value={contrast} onChange={(e) => setContrast(e.target.value)} className="w-full accent-indigo-500 cursor-pointer" />
                  </div>
                  <div>
                    <div className="flex justify-between text-slate-400 mb-1"><span>Saturation</span><span>{saturation}%</span></div>
                    <input type="range" min="0" max="200" value={saturation} onChange={(e) => setSaturation(e.target.value)} className="w-full accent-indigo-500 cursor-pointer" />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="w-full max-w-7xl pt-8 border-t border-white/10 mt-8">
        <Gallery 
          clientId={clientId} 
          refreshTrigger={galleryRefreshTrigger} 
          onLoadJob={handleLoadJob}
          onLoadRenderAsSketch={(job) => {
            setPrompt(job.prompt);
            handleLoadRenderAsSketch(job.render_path);
          }}
        />
      </div>

    </div>
  );
}