Project Structure:

Level 1: Structure Overview

```
├── docs (project documentation for MKDocs)
├── github.copilot.md (documentation and guides for GitHub Copilot)
├── Makefile (project build automation)
├── mkdocs.yml (project configuration for MkDocs)
├── notebooks (prototyping and experimentation)
├── pyproject.toml (project configuration for Python)
├── README.md (project overview and instructions)
├── src (source code)
└── uv.lock (dependency lock file)
```


Level 2: Source Code Structure

```
src
├── ailand (Main Packaged Application)
└── tools (Utility Functions and Scripts)
```

```
notebooks
├── aoai-client-example.ipynb (Example notebook for Enterprise OpenAI client)
```

Level 3: Main Packaged Application Structure

```
ailand
├── api (API Endpoints and Handlers)
├── core (Core Application Logic)
├── databases (Data Models and Schemas)
├── services (Business Logic and Services)
├── utils (Utility Functions and Helpers)
```

Level 4: Utility Functions and Helpers Structure

```
utils
├── logging (Logging Configuration and Utilities)
├── settings (Configuration Management)
└── auth (Authentication and Authorization Utilities)
```

Level 5: OpenAI client settings

```
settings
├── core.py (Core Settings Management)
├── base.py (Base Settings Classes)
```

```
auth
├── azure_identity.py (Authentication with Azure Identity)
```

```
Cliets
├── openai (AI Client Integrations)
├── interfaces (Client Interfaces)
└── retry (Retry Logic for API Calls)
```

```
openai
├── base.py (Azure OpenAI Client building logic)
├── catalog.py (Models Catalog for OpenAI, API Versions, Embeddings Models can be accessed and available)
├── chat.py (Chat Completion Client)
├── embed.py (Embeddings Client)
```


