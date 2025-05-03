import os
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import aiohttp
import uuid
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv

from agentpress.tool import Tool, ToolResult, openapi_schema, xml_schema

class SourcesTool(Tool):
    """Ferramenta para adicionar e extrair fontes (links, imagens, vídeos)."""

    def __init__(self):
        super().__init__()
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
        """
        # Validação básica
        if not url:
            return ToolResult(success=False, output="URL is required")
        
        # Auto-detectar tipo se não especificado
        if type == "link":
            # Verificar URLs de vídeo
            youtube_patterns = [
                r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)',
                r'youtube\.com\/shorts\/',
                r'youtube\.com\/v\/'
            ]
            
            is_youtube = any(re.search(pattern, url, re.IGNORECASE) for pattern in youtube_patterns)
            
            if is_youtube:
                type = "video"
            # Verificar URLs de imagem
            elif url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
                type = "image"
        
        # Extrair título da URL se não fornecido
        if not title:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if path_parts and path_parts[-1]:
                # Extrair nome do arquivo/último caminho e remover extensão
                title_candidate = path_parts[-1]
                title = re.sub(r'\.[^.]+$', '', title_candidate)  # Remove extensão
                title = title.replace('-', ' ').replace('_', ' ').title()
            else:
                # Usar hostname como título
                title = parsed_url.netloc
        
        # Criar o objeto fonte
        source = {
            "url": url,
            "title": title,
            "type": type,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        
        return ToolResult(success=True, output=source)

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "extract_sources",
            "description": "Extract sources (links, images, videos) from a URL or textual content. This helps gather multiple sources in one operation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the page to extract sources from."
                    },
                    "content": {
                        "type": "string",
                        "description": "Text to parse and extract sources from."
                    },
                    "types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["link", "image", "video"]
                        },
                        "description": "Types of sources to extract. If not specified, all types will be extracted."
                    }
                }
            }
        }
    })
    @xml_schema(
        tag_name="extract-sources",
        mappings=[
            {"param_name": "url", "node_type": "attribute", "path": "."},
            {"param_name": "content", "node_type": "text", "path": "."},
            {"param_name": "types", "node_type": "attribute", "path": ".", "custom_parser": lambda value: value.split(',')}
        ],
        example='''<extract-sources url="https://example.com" types="image,video">Additional text to parse</extract-sources>'''
    )
    async def extract_sources(self, url: Optional[str] = None, 
                             content: Optional[str] = None,
                             types: Optional[List[str]] = None) -> ToolResult:
        """
        Extrai fontes (links, imagens, vídeos) de um URL ou conteúdo textual.
        """
        # Validação básica
        if not url and not content:
            return ToolResult(success=False, output="Either URL or content must be provided")

        # Definir tipos padrão
        if not types:
            types = ["link", "image", "video"]
        
        sources = []
        
        # Extrair de URL
        if url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            # Extrair título da página
                            page_title = soup.title.string if soup.title else "Unknown Page"
                            
                            # Extrair links
                            if "link" in types:
                                for link in soup.find_all('a', href=True):
                                    href = link['href']
                                    if href.startswith('http'):
                                        link_title = link.get_text().strip() or href
                                        sources.append({
                                            "url": href,
                                            "title": link_title[:100],  # Limitar comprimento do título
                                            "type": "link",
                                            "description": f"Found on {page_title}",
                                            "timestamp": datetime.now().isoformat()
                                        })
                            
                            # Extrair imagens
                            if "image" in types:
                                for img in soup.find_all('img', src=True):
                                    src = img['src']
                                    if src.startswith(('http', '//')):
                                        img_src = src
                                    else:
                                        # Lidar com URLs relativas
                                        parsed_url = urlparse(url)
                                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                        img_src = base_url + src if src.startswith('/') else base_url + '/' + src
                                    
                                    alt_text = img.get('alt', 'Image')
                                    sources.append({
                                        "url": img_src,
                                        "title": alt_text[:100],
                                        "type": "image",
                                        "description": f"Image from {page_title}",
                                        "timestamp": datetime.now().isoformat()
                                    })
                            
                            # Extrair vídeos
                            if "video" in types:
                                # YouTube embeds
                                for iframe in soup.find_all('iframe', src=True):
                                    src = iframe['src']
                                    if 'youtube.com/embed/' in src:
                                        sources.append({
                                            "url": src,
                                            "title": iframe.get('title', 'YouTube Video'),
                                            "type": "video",
                                            "description": f"Video embedded on {page_title}",
                                            "timestamp": datetime.now().isoformat()
                                        })
                        else:
                            return ToolResult(success=False, output=f"Failed to fetch URL: HTTP status {response.status}")
            except Exception as e:
                return ToolResult(success=False, output=f"Error fetching URL: {str(e)}")
        
        # Extrair de conteúdo textual
        if content:
            # Extrair URLs de texto
            url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
            urls = re.findall(url_pattern, content)
            
            for found_url in urls:
                # Determinar tipo com base na URL
                source_type = "link"
                if any(vid_pattern in found_url.lower() for vid_pattern in ["youtube.com/watch", "youtu.be/", "youtube.com/embed"]):
                    source_type = "video"
                elif found_url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
                    source_type = "image"
                
                # Adicionar apenas se o tipo estiver entre os tipos solicitados
                if source_type in types:
                    sources.append({
                        "url": found_url,
                        "title": found_url.split("/")[-1].replace("-", " ").replace("_", " ").title(),
                        "type": source_type,
                        "description": f"Found in provided content",
                        "timestamp": datetime.now().isoformat()
                    })
        
        return ToolResult(success=True, output={"sources": sources}) 