# Documentação da API - Fiscaliza Brasil

Esta documentação descreve as rotas disponíveis no backend para consulta de dados da **Câmara dos Deputados** e do **Senado Federal**.

## Configuração para Postman
- **Base URL**: `http://localhost:8000/api`
- **Dica**: O FastAPI gera automaticamente uma documentação interativa em `http://localhost:8000/docs`, onde você pode testar cada rota e ver os esquemas de resposta.

### 📋 Lista Rápida de URLs (Copy & Paste)

Este novo padrão permite que você use a legislatura diretamente no caminho da URL, o que facilita muito o uso de variáveis no Postman (ex: `{{legislatura}}`).

#### Câmara
```text
http://localhost:8000/api/camara/{legislatura}/lista
http://localhost:8000/api/camara/{legislatura}/estatisticas
http://localhost:8000/api/camara/{legislatura}/empresas/estatisticas
http://localhost:8000/api/camara/{legislatura}/emendas
http://localhost:8000/api/camara/{legislatura}/emendas/resumo
http://localhost:8000/api/camara/{legislatura}/proposicoes
http://localhost:8000/api/camara/legislaturas
http://localhost:8000/api/camara/proposicoes/{id}/votos
http://localhost:8000/api/camara/comparar
http://localhost:8000/api/camara/{deputado_id}
```

#### Senado
```text
http://localhost:8000/api/senado/{legislatura}/lista
http://localhost:8000/api/senado/{legislatura}/estatisticas
http://localhost:8000/api/senado/{legislatura}/despesas/estatisticas
http://localhost:8000/api/senado/{legislatura}/empresas/estatisticas
http://localhost:8000/api/senado/{legislatura}/emendas
http://localhost:8000/api/senado/{legislatura}/emendas/resumo
http://localhost:8000/api/senado/{legislatura}/materia/listar
http://localhost:8000/api/senado/legislaturas
http://localhost:8000/api/senado/comparar
http://localhost:8000/api/senado/{senador_codigo}
http://localhost:8000/api/senado/{senador_codigo}/despesas
```

> **Nota**: As rotas originais via Query Parameter (ex: `?legislatura=57`) continuam funcionando normalmente para garantir compatibilidade.

---


## 🏛️ Câmara dos Deputados (`/api/camara`)

### Legislaturas
- **`GET /legislaturas`**: Lista os IDs de todas as legislaturas disponíveis (ex: 57, 56, 55...).

### Deputados e Estatísticas
- **`GET /lista`**: Lista todos os deputados ativos.
    - **Params**: `legislatura` (int, opcional) - Filtra quem exerceu mandato naquela legislatura.
- **`GET /estatisticas`**: Estatísticas gerais (total de deputados, distribuição por região).
    - **Resposta**: inclui `total_deputados`, `total_regioes`, `total_ufs` e `deputados_por_regiao`.
    - **Params**: `legislatura` (int, opcional).
- **`GET /{deputado_id}`**: Perfil detalhado de um deputado.
    - **Params**: `legislatura` (int, opcional) - Se passado, mostra as estatísticas focadas naquele período.
- **`GET /comparar`**: Compara perfil e gastos entre dois deputados.
    - **Params**: `id1` (int), `id2` (int), `ano` (int, opcional), `legislatura` (int, opcional).

### Despesas e Empresas
- **`GET /empresas/estatisticas`**: Ranking de fornecedores e empresas que mais receberam pagamentos.
    - **Params**: `legislatura` (int, opcional), `limit` (int, padrão 20).

### Emendas Parlamentares
- **`GET /emendas`**: Lista detalhada de emendas.
    - **Params**: `nome_deputado` (string), `ano` (int), `legislatura` (int), `pagina` (int).
- **`GET /emendas/resumo`**: Visão geral financeira das emendas por área e ranking de autores.
    - **Params**: `legislatura` (int, opcional).

### Projetos Legislativos
- **`GET /proposicoes`**: Lista de projetos de lei e outras proposições.
    - **Params**: `siglaTipo`, `ano`, `ementa`, `deputado` (nome), `legislatura`, `pagina`.
    - **Resposta**: retorna `proposicoes`, `paginacao` e `estatisticas` (total, tipo mais frequente e distribuição por tipo no conjunto filtrado completo).
- **`GET /proposicoes/{id}/votos`**: Histórico de votação nominal de um projeto específico.

---

## 🏛️ Senado Federal (`/api/senado`)

### Legislaturas
- **`GET /legislaturas`**: Lista os IDs das legislaturas do Senado.

### Senadores e Estatísticas
- **`GET /lista`**: Lista todos os senadores.
    - **Params**: `legislatura` (int, opcional).
- **`GET /estatisticas`**: Estatísticas macro do Senado (gastos totais, parlamentares por região).
    - **Params**: `legislatura` (int, opcional).
- **`GET /{senador_codigo}`**: Perfil detalhado de um senador.
    - **Params**: `legislatura` (int, opcional).
- **`GET /{senador_codigo}/despesas`**: Extrato detalhado de gastos de um senador (CEAPS).
    - **Params**: `legislatura` (int, opcional), `pagina` (int).
- **`GET /despesas/estatisticas`**: Rankings de maiores gastos e evolução mensal no Senado.
    - **Params**: `legislatura` (int, opcional).
- **`GET /comparar`**: Comparação entre dois senadores.
    - **Params**: `id1`, `id2`, `ano`, `legislatura`.

### Empresas e Matérias
- **`GET /empresas/estatisticas`**: Ranking das empresas fornecedoras do Senado.
    - **Params**: `legislatura` (int, opcional).
- **`GET /materia/listar`**: Consulta de matérias legislativas (projetos).
    - **Params**: `siglaTipo`, `ano`, `ementa`, `senador` (nome), `legislatura`, `pagina`, `limite`.
    - **Resposta**: retorna `materia`, `paginacao` e `estatisticas` (total, tipo mais frequente e distribuição por tipo).

### Emendas Parlamentares
- **`GET /emendas`**: Lista de emendas do Senado.
    - **Params**: `nome_senador`, `ano`, `legislatura`, `pagina`.
- **`GET /emendas/resumo`**: Resumo financeiro das emendas do Senado.
    - **Params**: `legislatura` (int, opcional).

---

## 💡 Sobre o parâmetro `legislatura`
A maioria das rotas aceita um parâmetro de consulta `legislatura` (PowerShell/Postman: `?legislatura=57`).

- **Por que usar?** Os dados históricos são vastos. Ao passar a legislatura, você filtra os resultados para um período de 4 anos específico, tornando as estatísticas muito mais precisas e comparáveis.
- **Onde encontrar os IDs?** Use as rotas `/api/camara/legislaturas` ou `/api/senado/legislaturas` para ver quais períodos estão disponíveis na sua base de dados.
