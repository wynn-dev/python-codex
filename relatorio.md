## Relatório Técnico — Codex CLI (Assistente de Programação em Linha de Comando)

### Objetivo

Este relatório descreve, em detalhe e em português de Portugal, o procedimento e desenvolvimento do programa Codex CLI, o material e software utilizados, uma discussão crítica das opções de desenho e limitações, e a conclusão do trabalho. Incluem‑se snippets de código representativos para facilitar a compreensão.

### Procedimento e Desenvolvimento

#### Visão geral da arquitetura

O Codex CLI é uma aplicação de terminal com interface textual (TUI) baseada em Textual/Rich que:

- inicia a app via `codex_cli/__main__.py` (parsing de argumentos e validação do workspace);
- constrói a interface no `codex_cli/app.py` com widgets personalizados em `codex_cli/widgets.py`;
- comunica com um modelo LLM via OpenRouter no `codex_cli/client.py`, com suporte a streaming e chamadas de ferramentas;
- expõe um conjunto de ferramentas (ler/escrever ficheiros, listar diretórios, executar comandos, etc.) no `codex_cli/tools.py`;
- lê configuração e credenciais a partir de variáveis de ambiente em `codex_cli/config.py`.

#### Entrada da aplicação (CLI)

O ponto de entrada define a linha de comandos, valida o diretório de trabalho e arranca a aplicação Textual.

```python
# codex_cli/__main__.py (excerto)
import sys
import argparse
from pathlib import Path
from .app import run

def main():
    parser = argparse.ArgumentParser(
        description="Codex CLI - AI Coding Assistant powered by Claude",
    )
    parser.add_argument('workspace', nargs='?', help='Workspace directory to open')
    parser.add_argument('-w', '--workspace', dest='workspace_flag')
    args = parser.parse_args()

    workspace_path = args.workspace_flag if args.workspace_flag else args.workspace
    if not workspace_path:
        parser.error("workspace argument is required.")

    workspace_path = Path(workspace_path).resolve()
    if not workspace_path.exists() or not workspace_path.is_dir():
        print(f"Error: '{workspace_path}' inválido", file=sys.stderr)
        sys.exit(1)

    run(workspace_path)

if __name__ == "__main__":
    main()
```

#### Aplicação Textual (TUI) e ciclo de interação

A interface cria cabeçalho, área de conversação com scroll, barra de estado e um campo de input no rodapé. Cada submissão do utilizador é enviada ao cliente LLM com streaming de conteúdos, raciocínio e chamadas de ferramentas.

```python
# codex_cli/app.py (excerto)
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input
from textual.containers import Container, Vertical
from .client import CodexClient
from .widgets import ConversationView, StatusBar

class CodexApp(App):
    def __init__(self, workspace_path):
        super().__init__()
        self.workspace_path = workspace_path
        self.client = CodexClient(self.workspace_path)
        self.is_processing = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            yield ConversationView()
            with Container(id="input-container"):
                yield Input(placeholder="›", id="message-input")
        yield StatusBar(workspace_path=self.workspace_path)
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.is_processing:
            return
        message = event.value.strip()
        if not message:
            return
        event.input.value = ""
        conv_view = self.query_one(ConversationView)
        conv_view.add_message("user", message)
        conv_view.show_loading("processing")
        status_bar = self.query_one(StatusBar)
        status_bar.set_thinking()
        self.is_processing = True

        try:
            async for content, info in self.client.send_message(message):
                # Gestão de raciocínio, streaming, tool calls e resultados...
                pass
        finally:
            self.is_processing = False
            status_bar.set_ready()
```

#### Cliente LLM com streaming e chamadas de ferramentas

O cliente agrega o histórico, cria o pedido ao OpenRouter e faz streaming de tokens. Quando o modelo pede ferramentas (function calling), delega na `ToolRegistry` e reenvia os resultados para o modelo até obter a resposta final.

```python
# codex_cli/client.py (excerto)
from openai import AsyncOpenAI
from .config import Config
from .tools import ToolRegistry

class CodexClient:
    def __init__(self, workspace_path):
        Config.validate()
        self.client = AsyncOpenAI(
            api_key=Config.OPENROUTER_API_KEY,
            base_url=Config.OPENROUTER_BASE_URL
        )
        self.model = Config.OPENROUTER_DEFAULT_MODEL
        self.tool_registry = ToolRegistry(workspace_path)
        self.conversation_history = []

    async def send_message(self, user_message: str):
        messages = [{"role": "system", "content": "...prompt..."}]
        # acumular histórico ...
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tool_registry.get_tool_schemas(),
            tool_choice="auto",
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS,
            extra_body={"route": Config.ROUTE_BY},
            stream=True,
            stream_options={"include_usage": True}
        )
        async for chunk in stream:
            # emitir eventos: reasoning/content/tool_call/tool_result/complete
            yield "", {"type": "content", "partial": True}
```

#### Ferramentas do agente (file ops, shell, pesquisa)

As ferramentas são registadas com esquema de parâmetros e implementações assíncronas. O registo expõe schemas compatíveis com “function calling” e executa a ferramenta pedida pelo modelo.

```python
# codex_cli/tools.py (excerto)
from dataclasses import dataclass
from typing import Any, Dict, Callable, List

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable

class ToolRegistry:
    def __init__(self, workspace_path):
        self.workspace_path = workspace_path
        self.tools: Dict[str, Tool] = {}
        self._register_tools()

    def register_tool(self, name, description, parameters, function):
        self.tools[name] = Tool(name, description, parameters, function)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            }
        } for t in self.tools.values()]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        tool = self.tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        return await tool.function(**arguments)
```

#### Configuração e variáveis de ambiente

A validação garante que existe `OPENROUTER_API_KEY` carregada, por exemplo, via `.env`.

```python
# codex_cli/config.py (excerto)
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "x-ai/grok-code-fast-1")
    MAX_TOKENS = 20000
    TEMPERATURE = 0
    ROUTE_BY = "throughput"

    @classmethod
    def validate(cls) -> bool:
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found")
        return True
```

#### Widgets personalizados e experiência de streaming

Os widgets (`ConversationView`, `LoadingWidget`, `StreamingMessageWidget`, etc.) fornecem animações, controlo de estado e formatação de resultados das ferramentas, melhorando a perceção de “raciocínio” e streaming de conteúdo.

```python
# codex_cli/widgets.py (excerto)
from textual.widgets import Static, Collapsible
from textual.containers import VerticalScroll
from rich.markdown import Markdown

class StreamingMessageWidget(Static):
    def __init__(self, role: str = "assistant", **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content_buffer = ""
        self.is_streaming = True

    def append_content(self, text: str):
        self.content_buffer += text
        self.update(Markdown(self.content_buffer))

    def finalize(self):
        self.is_streaming = False
        self.update(Markdown(self.content_buffer))
```

### Material e Software

- **Hardware**: Máquina local de desenvolvimento (CPU moderna; sem requisitos específicos de GPU).
- **Sistema operativo**: macOS 15 (Darwin 24.2.0).
- **Shell**: `/bin/zsh`.
- **Linguagem**: Python 3.10+ recomendado.
- **Dependências principais** (de `requirements.txt`):
  - textual (>= 0.47.0) — UI em terminal
  - openai (>= 1.12.0) — cliente AsyncOpenAI (usado com OpenRouter)
  - python-dotenv (>= 1.0.0) — carregamento de `.env`
  - rich (>= 13.7.0) — formatação/markdown/syntax highlight
  - aiofiles (>= 23.2.1) — IO assíncrono em ficheiros
  - httpx (>= 0.26.0), pygments (>= 2.17.2)
- **Conta/credenciais**: Chave `OPENROUTER_API_KEY` válida.
- **Estrutura de pastas**: código em `codex_cli/`; espaço de testes em `test_workspace/`.

### Discussão

- **Opções de desenho**:

  - UI baseada em Textual permite uma experiência rica em terminal (atalhos, scroll, widgets). O streaming no `ConversationView` oferece feedback imediato e melhora a usabilidade.
  - O cliente LLM (`AsyncOpenAI` com OpenRouter) dá suporte a modelos diversos via `base_url` configurável, com routing por throughput para respostas rápidas.
  - A `ToolRegistry` encapsula schemas e execuções de ferramentas, alinhada com “function calling” do modelo, facilitando extensibilidade (adicionar novas ferramentas é direto).

- **Robustez e UX**:

  - Entradas de utilizador validadas no `__main__.py` (existência e tipo de diretório).
  - Estados visuais (thinking/streaming/erro) e spinners melhoram a perceção de progresso.
  - Erros são capturados e apresentados como mensagens na conversa e barra de estado.

- **Limitações**:

  - Requer rede e uma `OPENROUTER_API_KEY` válida; indisponibilidade do serviço interrompe o fluxo.
  - O tempo-limite de comandos de shell (30s) pode ser curto para tarefas pesadas; aumentar com cautela.
  - Iterações de chamadas de ferramenta limitadas a 10 por salvaguarda — cenários complexos podem precisar de ajuste.
  - Segurança: execução de comandos/IO no workspace deve ser usada com prudência (superfície de risco inerente).

- **Melhorias futuras**:
  - Persistência e exportação de conversas (e.g., para Markdown/HTML).
  - Gestão de perfis/modelos e comutação dinâmica em UI.
  - Mais ferramentas (git, grep semântico local, runners de teste) com sandboxing reforçado.
  - Telemetria opcional de performance (latência, tokens) com vista de diagnóstico.

### Conclusão

O Codex CLI materializa um assistente de programação em terminal com interface moderna, streaming e integração de ferramentas orientadas ao workspace. A arquitetura modular (CLI → App Textual → Cliente LLM → Registry de Ferramentas) simplifica manutenção e extensão. Apesar das dependências de conectividade e credenciais, o sistema demonstra uma base sólida para evoluir em direção a um ambiente de desenvolvimento conversacional mais completo, com segurança e produtividade reforçadas.

### Anexo: Exemplo simples de utilização de ferramenta

```python
# Ler um ficheiro do workspace (via ferramenta)
result = await tool_registry.execute_tool("read_file", {"file_path": "README.md"})
print(result)
```
