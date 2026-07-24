#!/usr/bin/env python3
"""
Memory MCP — LEON XAU ELITE AI
Memória, Obsidian vault, busca de contexto e aprendizado diário.

Tools:
  - get_daily_context      Retorna o contexto acumulado (CONTEXTO_EVOLUCAO.md)
  - search_knowledge_base  Busca notas no vault Obsidian
  - store_note             Armazena uma nota no vault Obsidian
  - register_learning      Registra aprendizado diário
  - list_recent_learnings  Lista aprendizados recentes
  - get_vault_structure    Retorna estrutura do vault
"""

import json
import os
import sys
import glob
from datetime import datetime
from pathlib import Path

# Ensure src/mcp/ is in path for both script execution and module import
_MCP_DIR = str(Path(__file__).resolve().parent)
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from mcp_protocol import MCPBaseHandler, MCPError, INVALID_PARAMS, run_server


# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OBSIDIAN_VAULT = PROJECT_ROOT / "obsidian_vault"
LEARNINGS_DIR = OBSIDIAN_VAULT / "aprendizados_diarios"
TAREFAS_LEARNINGS = PROJECT_ROOT / "tarefas" / "aprendizados_diarios"
CONTEXTO_FILE = LEARNINGS_DIR / "CONTEXTO_EVOLUCAO.md"
INDICE_FILE = LEARNINGS_DIR / "INDICE.md"


class MemoryMCPHandler(MCPBaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__("leon-memory-mcp", "1.0.0")

    def register_tools(self):
        # 1. get_daily_context
        self.add_tool_def(
            name="get_daily_context",
            description="Retorna o contexto acumulado do LEON (CONTEXTO_EVOLUCAO.md) para carregamento rápido no início de cada missão.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self.get_daily_context
        )

        # 2. search_knowledge_base
        self.add_tool_def(
            name="search_knowledge_base",
            description="Busca notas e aprendizados no vault Obsidian por palavra-chave ou expressão.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Palavra-chave ou expressão para busca"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Número máximo de resultados (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            },
            handler=self.search_knowledge_base
        )

        # 3. store_note
        self.add_tool_def(
            name="store_note",
            description="Armazena uma nova nota no vault Obsidian (modo append ou novo arquivo). Não permite sobrescrita.",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Título da nota (sem espaços ou usar underscores)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Conteúdo da nota em Markdown"
                    },
                    "folder": {
                        "type": "string",
                        "description": "Pasta destino (ex: 'analise', 'operacional', 'referencias'). Default: raiz do vault.",
                        "default": ""
                    }
                },
                "required": ["title", "content"]
            },
            handler=self.store_note
        )

        # 4. register_learning
        self.add_tool_def(
            name="register_learning",
            description="Registra um aprendizado no arquivo de aprendizado diário (YYYY-MM-DD.md).",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Conteúdo do aprendizado em Markdown"
                    },
                    "date": {
                        "type": "string",
                        "description": "Data no formato YYYY-MM-DD. Default: data atual.",
                        "default": ""
                    },
                    "category": {
                        "type": "string",
                        "description": "Categoria: operacao, decisao, erro, correcao, padrao, recomendacao",
                        "default": "operacao"
                    }
                },
                "required": ["content"]
            },
            handler=self.register_learning
        )

        # 5. list_recent_learnings
        self.add_tool_def(
            name="list_recent_learnings",
            description="Lista os aprendizados diários mais recentes do LEON.",
            input_schema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Número de dias para listar (default: 7)",
                        "default": 7
                    }
                },
                "required": []
            },
            handler=self.list_recent_learnings
        )

        # 6. get_vault_structure
        self.add_tool_def(
            name="get_vault_structure",
            description="Retorna a estrutura de pastas e arquivos do vault Obsidian.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self.get_vault_structure
        )

    # --- Tool implementations ---

    def get_daily_context(self) -> dict:
        # Sync from tarefas to vault if tarefas version is newer (daily_learning_sync
        # updates context/indice in tarefas/; we want the vault to reflect the latest)
        tarefas_contexto = TAREFAS_LEARNINGS / "CONTEXTO_EVOLUCAO.md"
        if tarefas_contexto.exists() and (
            not CONTEXTO_FILE.exists()
            or tarefas_contexto.stat().st_mtime > CONTEXTO_FILE.stat().st_mtime
        ):
            CONTEXTO_FILE.write_text(
                tarefas_contexto.read_text(encoding="utf-8"), encoding="utf-8"
            )

        if not CONTEXTO_FILE.exists():
            return {"context": "", "note": "Arquivo CONTEXTO_EVOLUCAO.md não encontrado"}
        
        content = CONTEXTO_FILE.read_text(encoding="utf-8")
        # Sync vault version to tarefas as fallback
        self._sync_file(CONTEXTO_FILE)
        
        return {
            "context": content,
            "file": str(CONTEXTO_FILE),
            "size_chars": len(content),
            "note": "Carregue este contexto no início de cada missão"
        }

    def search_knowledge_base(self, query: str, max_results: int = 10) -> dict:
        results = []
        md_files = list(OBSIDIAN_VAULT.rglob("*.md"))
        
        for fpath in md_files:
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                if query.lower() in content.lower():
                    # Get context around match
                    lines = content.split("\n")
                    matching_lines = [
                        {"line": i + 1, "text": line.strip()}
                        for i, line in enumerate(lines)
                        if query.lower() in line.lower()
                    ]
                    results.append({
                        "file": str(fpath.relative_to(OBSIDIAN_VAULT)),
                        "matches": len(matching_lines),
                        "snippets": matching_lines[:5]  # max 5 snippets per file
                    })
            except Exception:
                continue
        
        # Sort by match count descending
        results.sort(key=lambda x: x["matches"], reverse=True)
        results = results[:max_results]
        
        return {
            "query": query,
            "total_results": len(results),
            "results": results
        }

    def store_note(self, title: str, content: str, folder: str = "") -> dict:
        # Sanitize title for filename
        safe_title = title.replace(" ", "_").replace("/", "_").replace("\\", "_")
        if not safe_title.endswith(".md"):
            safe_title += ".md"
        
        # Determine path
        if folder:
            folder_path = OBSIDIAN_VAULT / folder
            if not folder_path.exists():
                return {
                    "success": False,
                    "error": f"Pasta '{folder}' não existe no vault. Pastas: analise, operacional, referencias, reunioes, aprendizados_diarios"
                }
        else:
            folder_path = OBSIDIAN_VAULT
        
        filepath = folder_path / safe_title
        
        # Block overwrite — only create new files
        if filepath.exists():
            return {
                "success": False,
                "error": f"Arquivo '{safe_title}' já existe. Use outro título ou mova o arquivo existente."
            }
        
        # Build markdown content with frontmatter
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_content = f"""---
title: {title}
created: {now}
source: leon-memory-mcp
---

{content}
"""
        filepath.write_text(full_content, encoding="utf-8")
        
        return {
            "success": True,
            "file": str(filepath.relative_to(OBSIDIAN_VAULT)),
            "size_chars": len(full_content)
        }

    def register_learning(self, content: str, date: str = "", category: str = "operacao") -> dict:
        # Determine date
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        else:
            # Validate date format
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise MCPError(INVALID_PARAMS, f"Data inválida: {date}. Use YYYY-MM-DD.")
        
        # Valid categories
        valid_categories = ["operacao", "decisao", "erro", "correcao", "padrao", "recomendacao"]
        if category not in valid_categories:
            raise MCPError(INVALID_PARAMS, f"Categoria inválida: {category}. Válidas: {', '.join(valid_categories)}")
        
        # File path
        learning_file = LEARNINGS_DIR / f"{date}.md"
        
        # Append or create
        header = f"## {category.title()}\n\n"
        entry = f"- {content}\n"
        
        if learning_file.exists():
            existing = learning_file.read_text(encoding="utf-8")
            existing += entry
            learning_file.write_text(existing, encoding="utf-8")
        else:
            full = f"# Aprendizados Diários — {date}\n\n{header}{entry}\n"
            learning_file.write_text(full, encoding="utf-8")
        
        # Sync to tarefas directory
        tarefas_file = TAREFAS_LEARNINGS / f"{date}.md"
        if tarefas_file.exists():
            existing_t = tarefas_file.read_text(encoding="utf-8")
            existing_t += entry
            tarefas_file.write_text(existing_t, encoding="utf-8")
        else:
            full_t = f"# Aprendizados Diários — {date}\n\n{header}{entry}\n"
            tarefas_file.write_text(full_t, encoding="utf-8")
        
        return {
            "success": True,
            "file": f"aprendizados_diarios/{date}.md",
            "category": category,
            "note": "Aprendizado registrado e sincronizado com tarefas/"
        }

    def list_recent_learnings(self, days: int = 7) -> dict:
        learnings = []
        from datetime import timedelta
        
        today = datetime.now()
        
        for i in range(days):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            fpath = LEARNINGS_DIR / f"{d}.md"
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                # Extract first 500 chars as preview
                preview = content[:500] + ("..." if len(content) > 500 else "")
                learnings.append({
                    "date": d,
                    "file": f"aprendizados_diarios/{d}.md",
                    "size_chars": len(content),
                    "preview": preview
                })
        
        return {
            "days_requested": days,
            "days_found": len(learnings),
            "learnings": learnings
        }

    def get_vault_structure(self) -> dict:
        structure = {}
        for root, dirs, files in os.walk(OBSIDIAN_VAULT):
            # Skip .obsidian dir
            if ".obsidian" in root:
                continue
            rel_path = Path(root).relative_to(OBSIDIAN_VAULT)
            parts = list(rel_path.parts) if str(rel_path) != "." else []
            
            md_files = [f for f in files if f.endswith(".md")]
            other_files = [f for f in files if not f.endswith(".md") and not f.startswith(".")]
            
            current = structure
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Use a sentinel key for file listing
            current["_files"] = {
                "markdown": md_files,
                "other": other_files
            }
        
        return {
            "vault_path": str(OBSIDIAN_VAULT),
            "structure": structure
        }

    def _sync_file(self, source: Path):
        """Sync a file from obsidian_vault to tarefas directory."""
        rel_path = source.relative_to(LEARNINGS_DIR)
        target = TAREFAS_LEARNINGS / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    run_server(MemoryMCPHandler, "leon-memory-mcp", "1.0.0")
