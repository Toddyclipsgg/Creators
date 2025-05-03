# Documentação do Recurso de Fontes (Sources) - Suna.so

## Visão Geral

O recurso "Sources" foi implementado para permitir que o agente da Suna.so anexe e extraia automaticamente fontes como links, imagens e vídeos durante suas pesquisas. Este recurso enriquece os threads com referências visuais e contextuais, permitindo aos usuários visualizar diretamente o conteúdo encontrado pelo agente.

**Problemas Resolvidos:**
- Falta de contexto visual durante as pesquisas
- Dificuldade em localizar fontes originais mencionadas pelo agente
- Ausência de visualização direta de vídeos e imagens referenciadas
- Inconsistência na exibição de conteúdo de diferentes formatos

## Arquitetura e Componentes

![Arquitetura do Recurso Sources](docs/images/sources-architecture.png)

### Backend (`/backend`)

- **`backend/agent/tools/sources_tool.py`**: Implementação principal da ferramenta SourcesTool
  - **Classe**: `SourcesTool(Tool)`
  - **Métodos**:
    - `add_source`: Adiciona manualmente uma fonte (link, imagem ou vídeo)
    - `extract_sources`: Extrai automaticamente fontes de um URL ou conteúdo textual
  - **Decoradores**: Utiliza `@openapi_schema` e `@xml_schema` para definir a interface da ferramenta

- **`backend/agent/run.py`**: Arquivo onde a ferramenta é registrada no sistema de agentes
  - **Linha 50**: Adição da importação `from agent.tools.sources_tool import SourcesTool`
  - **Linha 94**: Registro da ferramenta no thread manager com `thread_manager.add_tool(SourcesTool)`

- **`backend/agent/prompt.py`**: Atualização do prompt do sistema para incluir instruções sobre o uso de fontes
  - **Linhas 347-367**: Seção modificada sobre "Using Sources Tool (MANDATORY for Videos, Images, and Links)"
  - **Linhas 373-403**: Instruções sobre gerenciamento de fontes e workflow obrigatório

### Frontend (`/frontend`)

- **`frontend/src/components/thread/tool-views/SourcesToolView.tsx`**: Componente principal para renderização de fontes
  - **Linhas 1-836**: Implementação completa do componente de visualização de fontes
  - **Interface**: Define tipos para `Source`, `SourceStats` e outras estruturas de dados

- **`frontend/src/components/thread/tool-call-side-panel.tsx`**: Integração do componente SourcesToolView no painel lateral
  - **Linhas 22-23**: Importação do componente SourcesToolView
  - **Linhas 113-120**: Registro do componente para uso com tipos 'add-source' e 'extract-sources'

- **`frontend/src/components/thread/tool-views/utils.ts`**: Funções utilitárias para processamento de fontes
  - **Linhas 612-654**: Funções para extrair URLs, títulos e conteúdo de webpages
  - **Linhas 655-684**: Função `getToolComponent` atualizada para incluir componentes de Sources

## Implementação Detalhada

### Backend: SourcesTool (`backend/agent/tools/sources_tool.py`)

A implementação completa da ferramenta segue o padrão estabelecido pelo sistema de ferramentas da Suna.so:

```python
class SourcesTool(Tool):
    """Tool for saving and managing sources like links, images, and videos."""

    def __init__(self):
        super().__init__()
        # Load environment variables
        load_dotenv()

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "add_source",
            "description": "Add a source (link, image, or video) to the current thread. This tool allows you to save references to web content that can be displayed in the thread's sources section.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the source to add (webpage, image, or video URL)."
                    },
                    "title": {
                        "type": "string",
                        "description": "A descriptive title for the source. If not provided, the system will attempt to extract one from the URL."
                    },
                    "type": {
                        "type": "string",
                        "description": "The type of the source: 'link', 'image', or 'video'.",
                        "enum": ["link", "image", "video"],
                        "default": "link"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the source content."
                    }
                },
                "required": ["url"]
            }
        }
    })
    @xml_schema(
        tag_name="add-source",
        mappings=[
            {"param_name": "url", "node_type": "attribute", "path": "."},
            {"param_name": "title", "node_type": "attribute", "path": "."},
            {"param_name": "type", "node_type": "attribute", "path": "."},
            {"param_name": "description", "node_type": "text", "path": "."}
        ],
        example='''<add-source url="https://example.com/video" title="Example Video" type="video">Description text</add-source>'''
    )
    async def add_source(self, url: str, title: Optional[str] = None, 
                        type: str = "link", description: Optional[str] = None) -> ToolResult:
        """
        Adiciona uma fonte (link, imagem ou vídeo) ao thread atual.
        
        Implementação:
        1. Valida o URL e tipo fornecidos
        2. Auto-detecta o tipo de mídia baseado na URL se não especificado
        3. Cria um objeto fonte estruturado com metadados
        4. Retorna o objeto para ser processado pelo frontend
        """
        # [Código detalhado com algoritmo de detecção de tipo de mídia]
        # ...
```

#### Algoritmo de Detecção de Tipo de Mídia (`add_source`, linhas 77-88)

```python
# Auto-detect type if not specified or if we can improve it
if type == "link":
    # Check for video URLs usando regex para maior precisão
    youtube_patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)',
        r'youtube\.com\/shorts\/',
        r'youtube\.com\/v\/'
    ]
    
    is_youtube = any(re.search(pattern, url, re.IGNORECASE) for pattern in youtube_patterns)
    
    if is_youtube:
        type = "video"
    # Check for image URLs
    elif url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
        type = "image"
```

#### Extração de Fontes (`extract_sources`, linhas 140-269)

A função `extract_sources` utiliza diferentes estratégias para extrair fontes de conteúdo:

1. **Extração de URL**: Utiliza expressões regulares para identificar URLs de páginas web, imagens e vídeos
2. **Raspagem de HTML**: Quando fornecido um URL, raspa o conteúdo HTML para extrair links, imagens e vídeos embutidos
3. **Processamento de Texto**: Identifica URLs em texto livre fornecido pelo usuário
4. **Classificação**: Categoriza automaticamente as fontes baseado em padrões de URL e conteúdo

```python
async def extract_sources(self, url: Optional[str] = None, 
                         content: Optional[str] = None,
                         types: Optional[List[str]] = None) -> ToolResult:
    """
    Extrai fontes (links, imagens, vídeos) de um URL ou conteúdo textual.
    
    Parameters:
    -----------
    url : str, optional
        URL da página para extrair fontes
    content : str, optional
        Texto para analisar e extrair fontes
    types : List[str], optional
        Tipos de fontes a serem extraídas (link, image, video)
        
    Returns:
    --------
    ToolResult
        Resultado contendo lista de fontes extraídas
    """
    # [Implementação detalhada da extração]
```

### Frontend: SourcesToolView (`frontend/src/components/thread/tool-views/SourcesToolView.tsx`)

O componente frontend é responsável por exibir as fontes de forma organizada e categorizada, com suporte para diferentes tipos de mídia.

#### Definição de Interfaces (linhas 6-19)

```typescript
// Definição de tipos para as fontes
interface Source {
  url: string;
  title: string;
  type: "link" | "image" | "video" | "social" | "community" | "academic";
  description?: string;
  timestamp?: string;
  category?: string;
}

// Interface para estatísticas das fontes
interface SourceStats {
  total: number;
  byCategory: Record<string, number>;
}
```

#### Sistema de Armazenamento Local (linhas 22-48)

O componente implementa um sistema de persistência local usando localStorage para garantir que fontes permaneçam disponíveis entre sessões:

```typescript
// Chave base para armazenamento no localStorage
const STORAGE_KEY_BASE = "suna_sources_data";

// Função para obter a chave de armazenamento específica para o thread atual
function getStorageKey(threadId?: string): string {
  if (!threadId) return STORAGE_KEY_BASE;
  return `${STORAGE_KEY_BASE}_${threadId}`;
}

// Função para carregar fontes do localStorage específicas para um thread
function loadSourcesFromStorage(threadId?: string): Source[] {
  if (typeof window === "undefined") return [];
  
  try {
    const storageKey = getStorageKey(threadId);
    const storedData = localStorage.getItem(storageKey);
    if (!storedData) return [];
    
    const parsedData = JSON.parse(storedData);
    return Array.isArray(parsedData) ? parsedData : [];
  } catch (error) {
    console.error("Erro ao carregar fontes do localStorage:", error);
    return [];
  }
}
```

#### Extração de ID de Vídeos do YouTube (linhas 62-90)

A função `getYoutubeVideoId` é uma implementação robusta que lida com múltiplos formatos de URL do YouTube:

```typescript
// Helper function to extract YouTube video ID from URL
function getYoutubeVideoId(url: string): string | null {
  if (!url) return null;
  
  // Limpar URL de caracteres de escape primeiro
  const cleanedUrl = cleanUrl(url);
  
  // Limpar possíveis parametros adicionais
  const urlWithoutParams = cleanedUrl.split('&')[0];
  
  // Padrões comuns de URLs do YouTube
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/i,
    /(?:youtube\.com\/watch\?v=)([^&]+)/i,
    /(?:youtu\.be\/)([^?]+)/i
  ];
  
  for (const pattern of patterns) {
    const match = urlWithoutParams.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }
  
  // Se não encontrou com os padrões padrão, tenta uma abordagem mais flexível
  const anyYoutubeId = cleanedUrl.match(/(?:v=|\/)([\w-]{11})(?:\?|&|\/|$)/);
  if (anyYoutubeId && anyYoutubeId[1]) {
    return anyYoutubeId[1];
  }
  
  return null;
}
```

#### Renderização de Vídeos do YouTube (linhas 462-494)

A implementação de iframe para vídeos do YouTube substitui a abordagem anterior que apenas mostrava ícones:

```typescript
{(source.type === "video" || (source.type === "link" && isYoutubeUrl(source.url))) && (
  <div className="mt-2 border border-zinc-200 dark:border-zinc-700 rounded-md overflow-hidden">
    {(() => {
      const videoId = getYoutubeVideoId(source.url);
      console.log("Vídeo detectado:", source.url, "ID:", videoId);
      
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
```

#### Sistema de Abas para Filtrar Fontes (linhas 404-439)

O componente implementa um sistema de abas para filtrar fontes por categoria (web, vídeos, imagens, etc.):

```typescript
{/* Abas para as categorias - Design mais moderno e compacto */}
<div className="bg-zinc-50 dark:bg-zinc-900 rounded-lg p-1 mb-3 overflow-x-auto flex items-center">
  <div className="flex w-full">
    {tabs.filter(tab => tab.count > 0 || tab.id === "todos").map(tab => (
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
```

### Integração no Sistema (tool-call-side-panel.tsx)

A integração do componente SourcesToolView no sistema existente foi feita no arquivo `tool-call-side-panel.tsx`:

```typescript
// Importação do componente
import { SourcesToolView } from "./tool-views/SourcesToolView";

// Registro do componente para os tipos de ferramentas relacionadas a fontes
case 'add-source':
case 'extract-sources':
  return (
    <SourcesToolView
      name={normalizedToolName}
      assistantContent={assistantContent}
      toolContent={toolContent}
      assistantTimestamp={assistantTimestamp}
      toolTimestamp={toolTimestamp}
      isSuccess={isSuccess}
      isStreaming={isStreaming}
    />
  );
```

## Algoritmos e Processos Importantes

### 1. Extração de Fontes de Diferentes Formatos JSON (SourcesToolView.tsx, linhas 98-358)

Um dos desafios críticos foi lidar com a variabilidade nos formatos de resposta da ferramenta backend. O componente implementa várias estratégias de extração:

1. **Parsing de JSON direto**: Tenta fazer parse do conteúdo como JSON
2. **Extração de conteúdo de tags XML**: Busca por padrões como `<tool_result>` e `<add-source>`
3. **Extração via regex**: Usa expressões regulares para extrair URLs e metadados
4. **Fallbacks em cascata**: Implementa múltiplas estratégias de fallback

Exemplo de um dos métodos de extração (parcial):

```typescript
// Caso especial para o formato "ToolResult(success=True, output={...})"
if (typeof content === 'string' && content.includes('ToolResult(success=True, output=')) {
  try {
    // Extrair o objeto de saída usando regex
    const outputMatch = content.match(/output=({[\s\S]*?})\)/);
    if (outputMatch && outputMatch[1]) {
      // Converter a string do objeto para um objeto JSON válido
      let jsonStr = outputMatch[1]
        .replace(/'/g, '"')                 // Substitui aspas simples por duplas
        .replace(/(\w+):/g, '"$1":')        // Adiciona aspas aos nomes das propriedades
        .replace(/"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)"/g, '"$1"'); // Mantém formato de data
      
      try {
        const outputObj = JSON.parse(jsonStr);
        return [categorizeSource(outputObj)];
      } catch (jsonError) {
        // Tentativa de extração manual em caso de falha
        const url = content.match(/'url':\s*'([^']+)'/)?.[1];
        const title = content.match(/'title':\s*'([^']+)'/)?.[1];
        // ...
      }
    }
  } catch (e) {
    console.error("Erro ao processar ToolResult:", e);
  }
}
```

### 2. Categorização Automática de Fontes (linhas 93-125)

A função `categorizeSource` implementa um algoritmo avançado para classificar fontes em diferentes categorias baseado na URL e conteúdo:

```typescript
function categorizeSource(source: Source): Source {
  const url = source.url.toLowerCase();
  let category = "web"; // Categoria padrão
  let type = source.type;
  
  // Determinar tipo baseado na URL
  if (source.type === "video" || url.includes("youtube.com") || url.includes("youtu.be") || url.includes("vimeo") || url.match(/\.(mp4|mov|webm|avi)$/i)) {
    type = "video";
    category = "videos";
  } else if (source.type === "image" || url.match(/\.(jpg|jpeg|png|gif|webp|svg)$/i)) {
    type = "image";
    category = "imagens";
  } else if (url.includes("twitter.com") || url.includes("x.com") || url.includes("facebook.com") || url.includes("instagram.com") || 
            url.includes("linkedin.com") || url.includes("tiktok.com") || 
            url.match(/social|profile|user/i)) {
    type = "social";
    category = "social";
  } else if (url.includes("forum") || url.includes("community") || url.includes("reddit.com") || 
            url.includes("stackoverflow.com") || url.includes("discourse") || 
            url.match(/forum|community|group|discussion/i)) {
    type = "community";
    category = "comunidade";
  } else if (url.includes("scholar.google") || url.includes("doi.org") || url.includes("arxiv.org") ||
            url.includes("sciencedirect.com") || url.includes("researchgate.net") || url.includes("academia.edu") ||
            url.match(/journal|paper|research|doi|abstract|proceedings|scholar/i)) {
    type = "academic";
    category = "academic";
  } else {
    type = "link";
    category = "web";
  }
  
  return { ...source, type: type as any, category };
}
```

## Fluxo de Dados e Funcionamento

O fluxo completo do recurso Sources funciona da seguinte forma:

1. **Coleta de Fontes (Backend)**:
   - O agente encontra uma fonte relevante durante pesquisa
   - Chama `add_source` ou `extract_sources` via XML ou JSON
   - A ferramenta processa e retorna dados estruturados

2. **Transporte de Dados**:
   - O resultado da ferramenta é enviado como resposta para o frontend
   - Os dados passam pelo formato de mensagem do sistema

3. **Processamento Frontend**:
   - O componente `SourcesToolView` recebe os dados da fonte
   - Extrai informações usando uma das várias estratégias de parsing
   - Categoriza automaticamente a fonte
   - Armazena localmente para persistência

4. **Renderização Visual**:
   - O componente renderiza diferentes visualizações baseadas no tipo da fonte:
     - Links como cards clicáveis
     - Imagens embutidas com visualização
     - Vídeos como iframes do YouTube
   - Oferece sistema de abas para filtrar por categoria

5. **Interação do Usuário**:
   - Usuário pode filtrar fontes por categoria
   - Clicar em links externos
   - Assistir vídeos embutidos
   - Visualizar imagens diretamente na interface

## Correções e Melhorias Detalhadas

### 1. Embed de Vídeos (SourcesToolView.tsx, linhas 462-494)
- **Problema**: Versões anteriores apenas mostravam ícones para vídeos
- **Solução**: Implementação de iframe para vídeos do YouTube
- **Detalhes Técnicos**:
  - Extração robusta de IDs de vídeo
  - Iframe responsivo com proporção de aspecto
  - Fallback para vídeos não incorporáveis
  - Lazy loading para melhor performance

### 2. Extração e Processamento de Dados (linhas 98-358)
- **Problema**: Inconsistência em formatos de resposta do backend
- **Solução**: Sistema de múltiplas estratégias de extração
- **Detalhes Técnicos**:
  - Suporte para diferentes padrões de JSON
  - Extração de dados de tags XML
  - Processamento de strings ToolResult
  - Regex para extração de última instância

### 3. Categorização e Filtragem Automática (linhas 93-125, 359-379)
- **Problema**: Fontes misturadas sem organização
- **Solução**: Sistema de categorias e abas de filtro
- **Detalhes Técnicos**:
  - Algoritmo de detecção de categoria
  - Interface de filtro por abas
  - Contadores por categoria
  - UI responsiva para desktop e mobile

### 4. Tratamento de Erros e Fallbacks (distribuído pelo componente)
- **Problema**: Falhas na renderização de alguns tipos de conteúdo
- **Solução**: Sistema abrangente de tratamento de erros
- **Detalhes Técnicos**:
  - Tratamento de URLs inválidas
  - Fallbacks para imagens que falham no carregamento
  - Estratégias alternativas de parsing
  - Logging detalhado para depuração

## Oportunidades de Melhoria Futura

1. **Pré-visualização de Links**: Implementar cards de pré-visualização para links regulares
2. **Extração de Metadados**: Melhorar a extração de metadados como descrições e thumbnails
3. **Suporte para mais Plataformas de Vídeo**: Adicionar suporte para Vimeo, TikTok e outros serviços
4. **Exportação de Fontes**: Permitir exportar lista de fontes em diferentes formatos
5. **Persistência no Banco de Dados**: Mover do localStorage para persistência no banco de dados
6. **Interface de Administração**: Ferramentas para gerenciar fontes (editar, excluir, etc.)
7. **Compartilhamento de Fontes**: Funcionalidade para compartilhar fontes específicas

## Testes Realizados

### Testes de Unidade
- Testes para a função `getYoutubeVideoId` com múltiplos formatos de URL
- Testes para a função `categorizeSource` com diferentes tipos de conteúdo
- Testes para as funções de extração com vários formatos de resposta

### Testes de Integração
- Testes de integração entre backend e frontend
- Verificação de compatibilidade com diferentes formatos de resposta
- Simulação de cenários de erro e validação de fallbacks

### Testes de UI
- Testes de renderização em diferentes tamanhos de tela
- Verificação de acessibilidade dos componentes
- Testes de usabilidade do sistema de abas e filtros

## Arquivos Modificados e Detalhes Técnicos

### Backend

| Arquivo | Linhas | Descrição das Modificações |
|---------|--------|----------------------------|
| `backend/agent/tools/sources_tool.py` | 1-374 | Novo arquivo com implementação completa da ferramenta SourcesTool |
| `backend/agent/run.py` | 50 | Importação: `from agent.tools.sources_tool import SourcesTool` |
| `backend/agent/run.py` | 94 | Registro: `thread_manager.add_tool(SourcesTool)` |
| `backend/agent/prompt.py` | 347-403 | Atualização das instruções do sistema sobre uso de Sources |

### Frontend

| Arquivo | Linhas | Descrição das Modificações |
|---------|--------|----------------------------|
| `frontend/src/components/thread/tool-views/SourcesToolView.tsx` | 1-836 | Novo arquivo com implementação completa do componente visual |
| `frontend/src/components/thread/tool-call-side-panel.tsx` | 22-23 | Importação do componente SourcesToolView |
| `frontend/src/components/thread/tool-call-side-panel.tsx` | 113-120 | Registro para uso com tipos 'add-source' e 'extract-sources' |
| `frontend/src/components/thread/tool-views/utils.ts` | 612-654 | Funções para extração de dados de fontes |
| `frontend/src/components/thread/tool-views/utils.ts` | 655-684 | Atualização da função getToolComponent |

## Conclusão

O recurso de Sources representa uma melhoria significativa na experiência do usuário da plataforma Suna.so, permitindo que o agente salve e organize automaticamente referências visuais e textuais importantes durante suas pesquisas.

A implementação foi projetada com foco em robustez e flexibilidade, utilizando técnicas avançadas de processamento de dados para lidar com diferentes formatos e cenários. O sistema de categorização automática e a interface de usuário intuitiva tornam a navegação pelas fontes uma experiência fluida.

A integração entre o backend e frontend foi construída para ser resiliente a diferentes formatos de dados, com várias estratégias de fallback e tratamento de erros para garantir que as fontes sejam corretamente exibidas mesmo em cenários complexos. 