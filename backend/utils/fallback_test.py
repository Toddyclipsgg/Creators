"""
Teste de fallback de provedores LLM

Este arquivo contém testes para verificar se o mecanismo de fallback entre diferentes
provedores LLM está funcionando corretamente em todos os cenários possíveis.
"""

import sys
import os
import asyncio
import json
from typing import Dict, List, Optional, Any

# Adicionar diretório pai ao path para importar módulos corretamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.api import get_model_aliases
from services.llm import prepare_params, make_llm_api_call
from utils.config import config
from utils.logger import logger

# Configuração de mensagem de teste simples para uso com a API
TEST_MESSAGES = [
    {"role": "user", "content": "Hello, this is a test message to verify fallback mechanisms."}
]

async def test_get_model_aliases():
    """
    Testa a função get_model_aliases() com diferentes combinações de chaves API.
    """
    logger.info("\n=== TESTE DE FALLBACK NA FUNÇÃO get_model_aliases() ===")
    
    # Salvar configurações originais
    original_anthropic_key = config.ANTHROPIC_API_KEY
    original_gemini_key = config.GEMINI_API_KEY
    original_openai_key = config.OPENAI_API_KEY
    original_openrouter_key = config.OPENROUTER_API_KEY
    original_groq_key = config.GROQ_API_KEY
    original_aws_access_key = config.AWS_ACCESS_KEY_ID
    original_aws_secret_key = config.AWS_SECRET_ACCESS_KEY
    original_aws_region = config.AWS_REGION_NAME
    
    try:
        # Testar caso 1: Somente Anthropic disponível
        logger.info("\nCaso 1: Somente Anthropic disponível")
        config.ANTHROPIC_API_KEY = "test_key"
        config.GEMINI_API_KEY = None
        config.OPENAI_API_KEY = None
        config.OPENROUTER_API_KEY = None
        config.GROQ_API_KEY = None
        config.AWS_ACCESS_KEY_ID = None
        config.AWS_SECRET_ACCESS_KEY = None
        config.AWS_REGION_NAME = None
        
        aliases = get_model_aliases()
        logger.info(f"Modelo sonnet-3.7 mapeado para: {aliases.get('sonnet-3.7')}")
        assert aliases.get("sonnet-3.7") == "anthropic/claude-3-7-sonnet-latest", "Erro no fallback para Anthropic"
        
        # Testar caso 2: Anthropic indisponível, Gemini disponível
        logger.info("\nCaso 2: Anthropic indisponível, Gemini disponível")
        config.ANTHROPIC_API_KEY = None
        config.GEMINI_API_KEY = "test_key"
        
        aliases = get_model_aliases()
        logger.info(f"Modelo sonnet-3.7 mapeado para: {aliases.get('sonnet-3.7')}")
        assert "gemini" in aliases.get("sonnet-3.7"), "Erro no fallback para Gemini"
        
        # Testar caso 3: Anthropic e Gemini indisponíveis, OpenAI disponível
        logger.info("\nCaso 3: Anthropic e Gemini indisponíveis, OpenAI disponível")
        config.GEMINI_API_KEY = None
        config.OPENAI_API_KEY = "test_key"
        
        aliases = get_model_aliases()
        logger.info(f"Modelo sonnet-3.7 mapeado para: {aliases.get('sonnet-3.7')}")
        assert "openai" in aliases.get("sonnet-3.7"), "Erro no fallback para OpenAI"
        
        # Testar caso 4: Somente OpenRouter disponível
        logger.info("\nCaso 4: Somente OpenRouter disponível")
        config.OPENAI_API_KEY = None
        config.OPENROUTER_API_KEY = "test_key"
        
        aliases = get_model_aliases()
        logger.info(f"Modelo sonnet-3.7 mapeado para: {aliases.get('sonnet-3.7')}")
        assert "openrouter" in aliases.get("sonnet-3.7"), "Erro no fallback para OpenRouter"
        
        # Testar caso 5: Somente Groq disponível
        logger.info("\nCaso 5: Somente Groq disponível")
        config.OPENROUTER_API_KEY = None
        config.GROQ_API_KEY = "test_key"
        
        aliases = get_model_aliases()
        logger.info(f"Modelo sonnet-3.7 mapeado para: {aliases.get('sonnet-3.7')}")
        assert "groq" in aliases.get("sonnet-3.7"), "Erro no fallback para Groq"
        
        # Testar caso 6: Somente AWS Bedrock disponível
        logger.info("\nCaso 6: Somente AWS Bedrock disponível")
        config.GROQ_API_KEY = None
        config.AWS_ACCESS_KEY_ID = "test_key"
        config.AWS_SECRET_ACCESS_KEY = "test_key"
        config.AWS_REGION_NAME = "us-west-2"
        
        aliases = get_model_aliases()
        logger.info(f"Modelo sonnet-3.7 mapeado para: {aliases.get('sonnet-3.7')}")
        assert "bedrock" in aliases.get("sonnet-3.7"), "Erro no fallback para AWS Bedrock"
        
        # Testar caso 7: Nenhum provedor disponível
        logger.info("\nCaso 7: Nenhum provedor disponível")
        config.AWS_ACCESS_KEY_ID = None
        config.AWS_SECRET_ACCESS_KEY = None
        config.AWS_REGION_NAME = None
        
        aliases = get_model_aliases()
        logger.info(f"Modelo sonnet-3.7 mapeado para: {aliases.get('sonnet-3.7')}")
        assert "anthropic" in aliases.get("sonnet-3.7"), "Erro no fallback para o caso de nenhum provedor"
        
        logger.info("\n✅ Todos os testes de get_model_aliases() passaram com sucesso!")
        
    finally:
        # Restaurar configurações originais
        config.ANTHROPIC_API_KEY = original_anthropic_key
        config.GEMINI_API_KEY = original_gemini_key
        config.OPENAI_API_KEY = original_openai_key
        config.OPENROUTER_API_KEY = original_openrouter_key
        config.GROQ_API_KEY = original_groq_key
        config.AWS_ACCESS_KEY_ID = original_aws_access_key
        config.AWS_SECRET_ACCESS_KEY = original_aws_secret_key
        config.AWS_REGION_NAME = original_aws_region

async def test_prepare_params():
    """
    Testa a função prepare_params() com diferentes combinações de chaves API.
    """
    logger.info("\n=== TESTE DE FALLBACK NA FUNÇÃO prepare_params() ===")
    
    # Salvar configurações originais
    original_anthropic_key = config.ANTHROPIC_API_KEY
    original_gemini_key = config.GEMINI_API_KEY
    original_openai_key = config.OPENAI_API_KEY
    original_openrouter_key = config.OPENROUTER_API_KEY
    original_groq_key = config.GROQ_API_KEY
    original_aws_access_key = config.AWS_ACCESS_KEY_ID
    original_aws_secret_key = config.AWS_SECRET_ACCESS_KEY
    original_aws_region = config.AWS_REGION_NAME
    
    try:
        # Testar caso 1: Modelo Anthropic com key disponível
        logger.info("\nCaso 1: Modelo Anthropic com key disponível")
        config.ANTHROPIC_API_KEY = "test_key"
        
        params = prepare_params(
            messages=TEST_MESSAGES,
            model_name="anthropic/claude-3-7-sonnet-latest"
        )
        logger.info(f"Modelo original: anthropic/claude-3-7-sonnet-latest")
        logger.info(f"Modelo escolhido: {params.get('model')}")
        assert params.get("model") == "anthropic/claude-3-7-sonnet-latest", "Erro no modelo Anthropic"
        
        # Testar caso 2: Modelo Anthropic sem key, Gemini disponível
        logger.info("\nCaso 2: Modelo Anthropic sem key, Gemini disponível")
        config.ANTHROPIC_API_KEY = None
        config.GEMINI_API_KEY = "test_key"
        
        params = prepare_params(
            messages=TEST_MESSAGES,
            model_name="anthropic/claude-3-7-sonnet-latest"
        )
        logger.info(f"Modelo original: anthropic/claude-3-7-sonnet-latest")
        logger.info(f"Modelo escolhido: {params.get('model')}")
        assert "gemini" in params.get("model"), "Erro no fallback para Gemini"
        
        # Testar caso 3: Modelo Anthropic sem key, OpenAI disponível
        logger.info("\nCaso 3: Modelo Anthropic sem key, OpenAI disponível")
        config.GEMINI_API_KEY = None
        config.OPENAI_API_KEY = "test_key"
        
        params = prepare_params(
            messages=TEST_MESSAGES,
            model_name="anthropic/claude-3-7-sonnet-latest"
        )
        logger.info(f"Modelo original: anthropic/claude-3-7-sonnet-latest")
        logger.info(f"Modelo escolhido: {params.get('model')}")
        assert "openai" in params.get("model"), "Erro no fallback para OpenAI"
        
        # Testar caso 4: Modelo Anthropic sem key, OpenRouter disponível
        logger.info("\nCaso 4: Modelo Anthropic sem key, OpenRouter disponível")
        config.OPENAI_API_KEY = None
        config.OPENROUTER_API_KEY = "test_key"
        
        params = prepare_params(
            messages=TEST_MESSAGES,
            model_name="anthropic/claude-3-7-sonnet-latest"
        )
        logger.info(f"Modelo original: anthropic/claude-3-7-sonnet-latest")
        logger.info(f"Modelo escolhido: {params.get('model')}")
        assert "openrouter" in params.get("model"), "Erro no fallback para OpenRouter"
        
        # Testar caso 5: Modelo Anthropic sem key, Groq disponível
        logger.info("\nCaso 5: Modelo Anthropic sem key, Groq disponível")
        config.OPENROUTER_API_KEY = None
        config.GROQ_API_KEY = "test_key"
        
        params = prepare_params(
            messages=TEST_MESSAGES,
            model_name="anthropic/claude-3-7-sonnet-latest"
        )
        logger.info(f"Modelo original: anthropic/claude-3-7-sonnet-latest")
        logger.info(f"Modelo escolhido: {params.get('model')}")
        assert "groq" in params.get("model"), "Erro no fallback para Groq"
        
        # Testar caso 6: Modelo Anthropic sem key, AWS Bedrock disponível
        logger.info("\nCaso 6: Modelo Anthropic sem key, AWS Bedrock disponível")
        config.GROQ_API_KEY = None
        config.AWS_ACCESS_KEY_ID = "test_key"
        config.AWS_SECRET_ACCESS_KEY = "test_key"
        config.AWS_REGION_NAME = "us-west-2"
        
        params = prepare_params(
            messages=TEST_MESSAGES,
            model_name="anthropic/claude-3-7-sonnet-latest"
        )
        logger.info(f"Modelo original: anthropic/claude-3-7-sonnet-latest")
        logger.info(f"Modelo escolhido: {params.get('model')}")
        assert "bedrock" in params.get("model"), "Erro no fallback para AWS Bedrock"
        
        logger.info("\n✅ Todos os testes de prepare_params() passaram com sucesso!")
        
    finally:
        # Restaurar configurações originais
        config.ANTHROPIC_API_KEY = original_anthropic_key
        config.GEMINI_API_KEY = original_gemini_key
        config.OPENAI_API_KEY = original_openai_key
        config.OPENROUTER_API_KEY = original_openrouter_key
        config.GROQ_API_KEY = original_groq_key
        config.AWS_ACCESS_KEY_ID = original_aws_access_key
        config.AWS_SECRET_ACCESS_KEY = original_aws_secret_key
        config.AWS_REGION_NAME = original_aws_region

async def main():
    """Função principal para executar todos os testes."""
    try:
        logger.info("Iniciando testes de fallback de provedores LLM")
        
        await test_get_model_aliases()
        await test_prepare_params()
        
        logger.info("\n🎉 Todos os testes finalizados com sucesso! O mecanismo de fallback está funcionando corretamente.")
    except AssertionError as e:
        logger.error(f"\n❌ ERRO: {str(e)}")
    except Exception as e:
        logger.error(f"\n❌ ERRO INESPERADO: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 