# Documentação do Recurso de Fontes (Sources) - Suna.so

## Visão Geral

O recurso "Sources" foi implementado para permitir que o agente da Suna.so anexe e extraia automaticamente fontes como links, imagens e vídeos durante suas pesquisas. Este recurso enriquece os threads com referências visuais e contextuais, permitindo aos usuários visualizar diretamente o conteúdo encontrado pelo agente.

**Problemas Resolvidos:**
- Falta de contexto visual durante as pesquisas
- Dificuldade em localizar fontes originais mencionadas pelo agente
- Ausência de visualização direta de vídeos e imagens referenciadas
- Inconsistência na exibição de conteúdo de diferentes formatos

## Guia de Implementação Rápida

A implementação foi realizada na branch `feature/sources` com os seguintes passos:

1. **Backend**: 
   - Criado `sources_tool.py` com a ferramenta SourcesTool incluindo métodos `add_source` e `extract_sources`
   - Registrado a ferramenta no `run.py` e atualizado instruções no `prompt.py`

2. **Frontend**:
   - Criado `SourcesToolView.tsx` com sistema de abas, exibição de links, imagens e vídeos
   - Integrado componente em `tool-call-side-panel.tsx` para os tipos 'add-source' e 'extract-sources'
   - Implementado armazenamento local no localStorage para persistência de fontes

3. **Correções**:
   - Corrigido erro de importação nos decoradores: alterado de `agentpress.decorators` para `agentpress.tool`
   - O import correto é: `from agentpress.tool import Tool, ToolResult, openapi_schema, xml_schema`

4. **Versão de Controle**:
   - Branch: `feature/sources`
   - Commit: "Adiciona recurso Sources para referências de links, imagens e vídeos"

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
  - **Linha 25**: Adição da importação `from agent.tools.sources_tool import SourcesTool`
  - **Linha 71**: Registro da ferramenta no thread manager com `thread_manager.add_tool(SourcesTool)`

- **`backend/agent/prompt.py`**: Atualização do prompt do sistema para incluir instruções sobre o uso de fontes
  - **Linhas 347-367**: Seção adicionada sobre "Using Sources Tool"

### Frontend (`/frontend`)

- **`frontend/src/components/thread/tool-views/SourcesToolView.tsx`**: Componente principal para renderização de fontes
  - **407 linhas**: Implementação compacta do componente de visualização de fontes
  - **Interface**: Define tipos para `Source` e outras estruturas de dados

- **`frontend/src/components/thread/tool-call-side-panel.tsx`**: Integração do componente SourcesToolView
  - **Linha 21**: Importação do componente SourcesToolView
  - **Linhas 142-152**: Registro do componente para uso com tipos 'add-source' e 'extract-sources'

## Implementação Detalhada

### Backend: SourcesTool (`backend/agent/tools/sources_tool.py`)

A implementação é compacta e eficiente, com foco em três funcionalidades principais:

1. **Detecção automática de tipo de mídia**: Identifica automaticamente URLs de YouTube, imagens e outros tipos
2. **Extração de informações de URLs**: Extrai título e metadados de páginas web
3. **Raspagem de conteúdo**: Extrai fontes de HTML quando fornecido um URL

Exemplo do método central:

```python
async def add_source(self, url: str, title: Optional[str] = None, 
                    type: str = "link", description: Optional[str] = None) -> ToolResult:
    """
    Adiciona uma fonte (link, imagem ou vídeo) ao thread atual.
    """
    # Auto-detectar tipo se não especificado
    if type == "link":
        # Verificar URLs de vídeo
        youtube_patterns = [...]
        is_youtube = any(re.search(pattern, url, re.IGNORECASE) for pattern in youtube_patterns)
        
        if is_youtube:
            type = "video"
        # Verificar URLs de imagem
        elif url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
            type = "image"
    
    # Extrair título da URL se não fornecido
    if not title:
        # Lógica de extração de título...
    
    # Criar o objeto fonte
    source = {
        "url": url,
        "title": title,
        "type": type,
        "description": description,
        "timestamp": datetime.now().isoformat()
    }
    
    return ToolResult(success=True, output=source)
```

### Frontend: SourcesToolView (`frontend/src/components/thread/tool-views/SourcesToolView.tsx`)

O componente frontend implementa:

1. **Sistema de persistência**: Armazena fontes no localStorage por thread
2. **UI com abas**: Filtra fontes por tipo (Todos, Links, Imagens, Vídeos)
3. **Visualização integrada**: Renderiza imagens e vídeos diretamente na interface

Destaques da implementação:

```typescript
// Extração de fontes do conteúdo da ferramenta
function extractSourcesFromToolContent(content: string): Source[] {
  // Múltiplas estratégias de extração para diferentes formatos de resposta
  try {
    // Tentar parse como JSON
    // Estratégias de fallback
    // Extração via regex
  } catch (error) {
    console.error("Erro ao extrair fontes:", error);
  }
  
  return [];
}

// Renderização de vídeos do YouTube
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
        // Fallback para vídeos não incorporáveis
      );
    })()}
  </div>
)}
```

## Fluxo de Dados e Funcionamento

O fluxo compacto do recurso funciona em 4 etapas:

1. **Backend**: Agente chama `add_source` ou `extract_sources` ao encontrar referências
2. **Transporte**: Dados são enviados ao frontend via resposta da ferramenta
3. **Processamento**: Frontend extrai e categoriza as fontes, armazenando no localStorage
4. **Visualização**: Fontes são exibidas no painel lateral com suporte para imagens e vídeos

## Correções e Melhorias

### 1. Correção de Erro de Importação
- **Problema**: `Import "agentpress.decorators" could not be resolved`
- **Solução**: Atualizado o import para `from agentpress.tool import Tool, ToolResult, openapi_schema, xml_schema`
- **Arquivos Afetados**: `backend/agent/tools/sources_tool.py`

### 2. Embed de Vídeos
- **Implementação**: Iframe responsivo para vídeos do YouTube
- **Detalhes**: Extração robusta de IDs, proporção de aspecto correta

### 3. Sistema de Abas e Filtragem
- **Implementação**: Interface com abas para diferentes tipos de conteúdo
- **Detalhes**: UI responsiva, contadores por categoria

## Oportunidades de Melhoria Futura

1. **Persistência no Banco de Dados**: Migrar do localStorage para armazenamento permanente
2. **Suporte para mais Plataformas**: Adicionar Vimeo, TikTok e outros serviços de vídeo
3. **Interface de Gerenciamento**: Adicionar opções para editar e excluir fontes

## Conclusão

O recurso Sources é uma implementação compacta mas poderosa que melhora significativamente a experiência do usuário na plataforma Suna.so. Com apenas 2 arquivos novos e pequenas modificações em arquivos existentes, o recurso oferece uma experiência completa de visualização de fontes com suporte para links, imagens e vídeos.

A implementação foi projetada visando alta taxa de sucesso através de técnicas robustas de processamento de dados e estratégias de fallback, garantindo que as fontes sejam exibidas corretamente mesmo em cenários complexos. 