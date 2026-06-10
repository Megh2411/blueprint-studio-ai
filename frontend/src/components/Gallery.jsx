import React, { useState, useEffect } from 'react';
import { Download, RotateCcw, Paintbrush } from 'lucide-react'; 

const Gallery = ({ clientId, refreshTrigger, onLoadJob, onLoadRenderAsSketch }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch(`http://127.0.0.1:8000/api/renders/history/${clientId}`);
        if (!response.ok) throw new Error('Failed to fetch history');
        
        const data = await response.json();
        setHistory(data);
      } catch (error) {
        console.error("Error fetching gallery:", error);
      } finally {
        setLoading(false);
      }
    };

    if (clientId) fetchHistory();
  }, [clientId, refreshTrigger]);

  // 2. Add a robust download handler that fetches the Supabase image directly
  const handleDownload = async (url, prompt) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `blueprint-${prompt.substring(0, 15).replace(/\s+/g, '-')}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error("Download failed", err);
    }
  };

  if (loading) {
    return (
      <div className="w-full mx-auto p-6 mt-12">
        <h2 className="text-2xl font-bold mb-6 text-slate-200">Your Design Gallery</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="bg-white/[0.02] border border-white/5 rounded-2xl h-72 animate-pulse flex flex-col justify-between p-4">
              <div className="bg-white/5 rounded-xl h-40 w-full"></div>
              <div className="space-y-2">
                <div className="bg-white/5 h-4 w-3/4 rounded"></div>
                <div className="bg-white/5 h-3 w-1/2 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="w-full mx-auto p-6 mt-12 text-center border border-white/5 rounded-2xl bg-white/[0.01] py-16">
        <h2 className="text-2xl font-bold mb-2 text-slate-300">Your Design Gallery</h2>
        <p className="text-slate-500 text-sm max-w-sm mx-auto">No past renders found. Create your first sketch above and watch it transform!</p>
      </div>
    );
  }

  return (
    <div className="w-full mx-auto p-6 mt-12">
      <h2 className="text-2xl font-bold mb-6 text-slate-200">Your Design Gallery</h2>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {history.map((job) => (
          <div 
            key={job.job_id} 
            className="backdrop-blur-md bg-white/[0.02] rounded-2xl shadow-lg border border-white/10 overflow-hidden hover:border-indigo-500/40 transition-all duration-300 transform hover:-translate-y-1 group"
          >
            <div className="relative overflow-hidden">
              <img 
                src={job.render_path} 
                alt="Architectural Render" 
                className="w-full h-48 object-cover border-b border-white/10 transition-transform duration-500 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center gap-3">
                  <button 
                    onClick={() => onLoadJob && onLoadJob(job)} 
                    className="bg-indigo-600 text-white p-3 rounded-full hover:scale-110 transition-transform shadow-lg"
                    title="Edit Original Sketch"
                  >
                    <RotateCcw size={18} />
                  </button>
                  <button 
                    onClick={() => onLoadRenderAsSketch && onLoadRenderAsSketch(job)} 
                    className="bg-purple-600 text-white p-3 rounded-full hover:scale-110 transition-transform shadow-lg"
                    title="Use Render as Canvas Input"
                  >
                    <Paintbrush size={18} />
                  </button>
                  <button 
                    onClick={() => handleDownload(job.render_path, job.prompt)} 
                    className="bg-white text-black p-3 rounded-full hover:scale-110 transition-transform shadow-lg"
                    title="Download Render"
                  >
                    <Download size={18} />
                  </button>
              </div>
            </div>
            
            <div className="p-4 bg-black/10 flex flex-col justify-between flex-1">
              <div>
                <p className="text-sm text-slate-300 line-clamp-2 italic mb-3 font-medium" title={job.prompt}>
                  "{job.prompt}"
                </p>
              </div>
              <div className="space-y-3 mt-auto">
                <div className="flex justify-between items-center mt-auto">
                  <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-2 py-0.5 rounded-full">
                    Completed
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    {new Date(job.created_at).toLocaleDateString()}
                  </span>
                </div>
                
                <div className="grid grid-cols-3 gap-1 pt-2 border-t border-white/5">
                  <button
                    onClick={() => onLoadJob && onLoadJob(job)}
                    className="text-[10px] bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 py-1 rounded flex items-center justify-center gap-1 transition-colors"
                    title="Edit original sketch & prompt"
                  >
                    <RotateCcw size={10} /> Sketch
                  </button>
                  <button
                    onClick={() => onLoadRenderAsSketch && onLoadRenderAsSketch(job)}
                    className="text-[10px] bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/20 py-1 rounded flex items-center justify-center gap-1 transition-colors"
                    title="Load final render as sketch input"
                  >
                    <Paintbrush size={10} /> Render
                  </button>
                  <button
                    onClick={() => handleDownload(job.render_path, job.prompt)}
                    className="text-[10px] bg-slate-500/10 hover:bg-slate-500/20 text-slate-300 border border-slate-500/10 py-1 rounded flex items-center justify-center gap-1 transition-colors"
                    title="Download high-res image"
                  >
                    <Download size={10} /> Get
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Gallery;