import React, { useState, useEffect } from 'react';
import { 
  Globe, 
  Image as ImageIcon, 
  Video, 
  Link as LinkIcon, 
  ExternalLink, 
  FileVideo
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Definição de tipos
interface Source {
  url: string;
  title: string;
  type: "link" | "image" | "video";
  description?: string;
  timestamp?: string;
  category?: string;
}

// Interface para propriedades do componente
interface SourcesToolViewProps {
  name: string;
  assistantContent?: string;
  toolContent?: string;
  assistantTimestamp?: string;
  toolTimestamp?: string;
  isSuccess?: boolean;
  isStreaming?: boolean;
}

// Chave para armazenamento no localStorage
const STORAGE_KEY_BASE = "suna_sources_data";

// Função para obter a chave de armazenamento específica para o thread atual
function getStorageKey(threadId?: string): string {
  if (!threadId) return STORAGE_KEY_BASE;
  
  // Extrair threadId da URL se estiver disponível
  if (typeof window !== "undefined") {
    const pathname = window.location.pathname;
    const match = pathname.match(/\/agents\/([^/]+)/);
    if (match && match[1]) {
      return `${STORAGE_KEY_BASE}_${match[1]}`;
    }
  }
  
  return `${STORAGE_KEY_BASE}_${threadId}`;
}

// Função para carregar fontes do localStorage
function loadSourcesFromStorage(): Source[] {
  if (typeof window === "undefined") return [];
  
  try {
    // Extrair threadId da URL
    const pathname = window.location.pathname;
    const match = pathname.match(/\/agents\/([^/]+)/);
    const storageKey = match && match[1] 
      ? `${STORAGE_KEY_BASE}_${match[1]}` 
      : STORAGE_KEY_BASE;
    
    const storedData = localStorage.getItem(storageKey);
    if (!storedData) return [];
    
    const parsedData = JSON.parse(storedData);
    return Array.isArray(parsedData) ? parsedData : [];
  } catch (error) {
    console.error("Erro ao carregar fontes do localStorage:", error);
    return [];
  }
}

// Função para salvar fontes no localStorage
function saveSourcesToStorage(sources: Source[]): void {
  if (typeof window === "undefined") return;
  
  try {
    // Extrair threadId da URL
    const pathname = window.location.pathname;
    const match = pathname.match(/\/agents\/([^/]+)/);
    const storageKey = match && match[1] 
      ? `${STORAGE_KEY_BASE}_${match[1]}` 
      : STORAGE_KEY_BASE;
    
    localStorage.setItem(storageKey, JSON.stringify(sources));
  } catch (error) {
    console.error("Erro ao salvar fontes no localStorage:", error);
  }
}

// Função para limpar URLs
function cleanUrl(url: string): string {
  return url.replace(/\\"/g, '"').replace(/\\n/g, '').trim();
}

// Função para verificar se é uma URL do YouTube
function isYoutubeUrl(url: string): boolean {
  return url.includes('youtube.com') || url.includes('youtu.be');
}

// Função para extrair o ID do vídeo do YouTube
function getYoutubeVideoId(url: string): string | null {
  if (!url) return null;
  
  // Limpar URL de caracteres de escape
  const cleanedUrl = cleanUrl(url);
  
  // Padrões comuns de URLs do YouTube
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/i,
    /(?:youtube\.com\/watch\?v=)([^&]+)/i,
    /(?:youtu\.be\/)([^?]+)/i
  ];
  
  for (const pattern of patterns) {
    const match = cleanedUrl.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }
  
  return null;
}

// Componente principal
export function SourcesToolView({
  name,
  assistantContent,
  toolContent,
  assistantTimestamp,
  toolTimestamp,
  isSuccess = true,
  isStreaming = false
}: SourcesToolViewProps) {
  const [sources, setSources] = useState<Source[]>([]);
  const [activeTab, setActiveTab] = useState<string>("todos");
  
  // Processar conteúdo da ferramenta quando disponível
  useEffect(() => {
    if (!toolContent || !isSuccess) return;
    
    try {
      // Carregar fontes existentes do localStorage
      const existingSources = loadSourcesFromStorage();
      
      // Extrair novas fontes do conteúdo da ferramenta
      const newSources = extractSourcesFromToolContent(toolContent);
      
      if (newSources.length > 0) {
        // Combinar as fontes existentes com as novas, removendo duplicatas por URL
        const combined = [...existingSources];
        
        for (const newSource of newSources) {
          if (!combined.some(existing => existing.url === newSource.url)) {
            combined.push(newSource);
          }
        }
        
        // Atualizar estado e salvar no localStorage
        setSources(combined);
        saveSourcesToStorage(combined);
      } else {
        // Se não houver novas fontes, apenas carregue as existentes
        setSources(existingSources);
      }
    } catch (error) {
      console.error("Erro ao processar conteúdo da ferramenta:", error);
    }
  }, [toolContent, isSuccess]);
  
  // Extrair fontes do conteúdo da ferramenta
  function extractSourcesFromToolContent(content: string): Source[] {
    if (!content) return [];
    
    try {
      // Tentar fazer parse como JSON primeiro
      try {
        const contentObj = JSON.parse(content);
        
        // Verificar se é o formato esperado
        if (contentObj && typeof contentObj === 'object') {
          // Caso 1: { "sources": [...] }
          if (contentObj.sources && Array.isArray(contentObj.sources)) {
            return contentObj.sources;
          }
          
          // Caso 2: { "url": "...", "title": "...", ... }
          if (contentObj.url) {
            return [contentObj];
          }
          
          // Caso 3: ToolResult com output que contém source
          if (contentObj.output) {
            const output = contentObj.output;
            if (typeof output === 'object') {
              if (output.sources && Array.isArray(output.sources)) {
                return output.sources;
              }
              if (output.url) {
                return [output];
              }
            }
          }
        }
      } catch (e) {
        // Se não for JSON válido, continuar com outras estratégias
      }
      
      // Estratégia de fallback: Buscar por URLs no conteúdo
      const urlPattern = /(https?:\/\/[^\s"']+)/g;
      const matches = content.match(urlPattern);
      
      if (matches) {
        return matches.map(url => ({
          url: cleanUrl(url),
          title: cleanUrl(url).split('/').pop()?.replace(/[-_]/g, ' ') || 'Link',
          type: url.match(/\.(jpg|jpeg|png|gif|webp|svg)$/i) 
            ? 'image' 
            : isYoutubeUrl(url) 
              ? 'video' 
              : 'link'
        }));
      }
    } catch (error) {
      console.error("Erro ao extrair fontes:", error);
    }
    
    return [];
  }
  
  // Filtrar fontes com base na aba ativa
  const filteredSources = React.useMemo(() => {
    if (activeTab === "todos") return sources;
    
    if (activeTab === "imagens") {
      return sources.filter(source => source.type === "image");
    }
    
    if (activeTab === "videos") {
      return sources.filter(source => source.type === "video" || 
        (source.type === "link" && isYoutubeUrl(source.url)));
    }
    
    return sources.filter(source => 
      source.type === "link" && 
      !isYoutubeUrl(source.url));
  }, [sources, activeTab]);
  
  // Contagem de fontes por tipo
  const counts = {
    total: sources.length,
    links: sources.filter(s => s.type === "link" && !isYoutubeUrl(s.url)).length,
    images: sources.filter(s => s.type === "image").length,
    videos: sources.filter(s => s.type === "video" || (s.type === "link" && isYoutubeUrl(s.url))).length
  };
  
  // Definição das abas
  const tabs = [
    { id: "todos", label: "Todos", icon: <Globe className="w-3.5 h-3.5" />, count: counts.total },
    { id: "links", label: "Links", icon: <LinkIcon className="w-3.5 h-3.5" />, count: counts.links },
    { id: "imagens", label: "Imagens", icon: <ImageIcon className="w-3.5 h-3.5" />, count: counts.images },
    { id: "videos", label: "Vídeos", icon: <Video className="w-3.5 h-3.5" />, count: counts.videos }
  ];
  
  // Se não houver fontes, mostrar mensagem
  if (sources.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-zinc-500 dark:text-zinc-400">
        Nenhuma fonte encontrada.
      </div>
    );
  }
  
  return (
    <div className="p-4">
      {/* Abas para categorias */}
      <div className="bg-zinc-50 dark:bg-zinc-900 rounded-lg p-1 mb-3 overflow-x-auto flex items-center">
        <div className="flex w-full">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1 transition-all duration-200 px-2 py-1.5 text-xs rounded-md flex-1 justify-center",
                activeTab === tab.id
                  ? "bg-white dark:bg-zinc-800 shadow-sm text-blue-600 dark:text-blue-400"
                  : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
              )}
            >
              {tab.icon}
              <span className="hidden sm:inline">{tab.label}</span>
              {tab.count > 0 && (
                <span className={cn(
                  "text-[10px] min-w-[16px] h-4 flex items-center justify-center rounded-full",
                  activeTab === tab.id
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                    : "bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300"
                )}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
      
      {/* Lista de fontes */}
      <div className="space-y-3">
        {filteredSources.map((source, index) => (
          <div 
            key={`${source.url}-${index}`} 
            className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden"
          >
            <div className="px-3 py-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {source.type === "link" && !isYoutubeUrl(source.url) && (
                  <Globe className="h-4 w-4 text-blue-500 dark:text-blue-400" />
                )}
                {source.type === "image" && (
                  <ImageIcon className="h-4 w-4 text-purple-500 dark:text-purple-400" />
                )}
                {(source.type === "video" || (source.type === "link" && isYoutubeUrl(source.url))) && (
                  <Video className="h-4 w-4 text-red-500 dark:text-red-400" />
                )}
                <a 
                  href={source.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-sm font-medium hover:underline truncate max-w-[200px] sm:max-w-xs" 
                  title={source.title}
                >
                  {source.title}
                </a>
              </div>
              
              <a 
                href={source.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
            
            {source.description && (
              <div className="text-xs text-zinc-500 dark:text-zinc-400 px-3 pb-2">
                {source.description}
              </div>
            )}
            
            {/* Renderização específica para cada tipo */}
            {source.type === "image" && (
              <div className="w-full max-h-80 overflow-hidden">
                <a href={source.url} target="_blank" rel="noopener noreferrer">
                  <img 
                    src={source.url} 
                    alt={source.title}
                    className="w-full h-auto object-contain" 
                    loading="lazy"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiIGNsYXNzPSJsdWNpZGUgbHVjaWRlLWltYWdlLW9mZiI+PHBhdGggZD0iTTAxOC42IDE4LjZMMDA2IDE4LjZMMDYgMDguNkwwOC42IDAzLjZDMDh4ZSgxLDIpIEQrTCsxIDB4bWwoLyspIHt9JiM2MDsuY2hhckNvZGVBdCguIiAvPjxsaW5lIHgxPSIyIiB5MT0iMiIgeDI9IjIyIiB5Mj0iMjIiIC8+PC9zdmc+';
                      target.className = 'w-full h-40 object-contain opacity-50';
                    }}
                  />
                </a>
              </div>
            )}
            
            {(source.type === "video" || (source.type === "link" && isYoutubeUrl(source.url))) && (
              <div className="mt-2 border border-zinc-200 dark:border-zinc-700 rounded-md overflow-hidden">
                {(() => {
                  const videoId = getYoutubeVideoId(source.url);
                  
                  return videoId ? (
                    <div className="aspect-video w-full">
                      <iframe 
                        width="100%" 
                        height="100%" 
                        src={`https://www.youtube.com/embed/${videoId}`}
                        title={source.title}
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowFullScreen
                        className="border-0"
                        loading="lazy"
                      ></iframe>
                    </div>
                  ) : (
                    <div className="aspect-video bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
                      <FileVideo className="h-8 w-8 text-zinc-400 dark:text-zinc-500" />
                      <span className="text-xs ml-2 text-zinc-500 dark:text-zinc-400">
                        Vídeo não pode ser incorporado. Clique no link acima para assistir.
                      </span>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
} 