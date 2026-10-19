# Painel de Controlo PCH — Formação FBP

Dashboard Streamlit preparado para **dois formulários Kobo diretamente ligados**, sem CSV, ficheiros auxiliares nem carregamentos manuais de participantes.

## Projetos configurados

- Servidor: `https://kf.kobo.ucp-pch.org`
- Pré-teste — UID: `a9UStPiv4QDyzfZeHiBzwu`
- Pós-teste — UID: `a2JXAwUZP7h3z3nUmpfchj`

A app consulta a API Kobo v2 `/api/v2/assets/{uid}/data/`, incluindo todas as páginas (`next`). O painel é **só de leitura**.

## Instalação local

1. Instala Python 3.11+.
2. Descompacta este projeto e, no terminal, abre a pasta que contém `app.py`.
3. Instala as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Cria localmente `.streamlit/secrets.toml`, copiando o exemplo `.streamlit/secrets.toml.example`.
5. Substitui `COLOCAR_O_TOKEN_AQUI` pelo teu token Kobo. **Nunca coloques o token em `app.py` ou num repositório público.**
6. Executa:
   ```bash
   streamlit run app.py
   ```

## Publicação no Streamlit Community Cloud

1. Cria um repositório no GitHub e carrega estes ficheiros. Não publiques `.streamlit/secrets.toml`.
2. No Streamlit Cloud, cria uma app ligada ao repositório, com `app.py` como ficheiro principal.
3. Em **App settings → Secrets**, cola o conteúdo de `.streamlit/secrets.toml`, substituindo o token pelo valor real.
4. Recomenda-se acrescentar a chave opcional `DASHBOARD_PASSWORD = "UMA_PALAVRA_PASSE_FORTE"` para restringir o acesso aos dados nominais.
5. Guarda os secrets e faz **Reboot** da app. Confirma os dois formulários e os totais na secção Qualidade dos dados.

> **Segurança:** uma API token é uma credencial de acesso, mesmo se a conta ou alguns dados forem públicos. Não a partilhes em documentação nem no GitHub. Como já a partilhaste na conversa, considera **revogá-la e emitir uma nova** antes da publicação, especialmente se o dashboard ficar acessível publicamente.

## Estrutura

- `app.py` — páginas Visão geral, Participantes, Aprendizagem, Qualidade dos dados; filtros e exportação CSV.
- `kobo_client.py` — cliente API, paginação e tratamento seguro de falhas.
- `analysis.py` — cruzamento por UUID, recálculo das notas, auditoria e agregações.
- `questionario.json` — 15 perguntas e grelha do documento original.
- `demo.py` — dados **fictícios**; ativa *Modo demonstração* na barra lateral.
- `assets/logo_pch.png` — logótipo do projeto (versão melhorada do original).
- `tests/test_analysis.py` — testes de cálculo, cruzamento, duplicados e casos sem associação.

## Regras de análise

- Pré e pós são ligados exclusivamente por **`participante_id`** (UUID do pré-teste); nunca pelo nome.
- Se existirem submissões repetidas com o mesmo identificador, a **primeira completa** é utilizada e o caso é sinalizado.
- Para comparar notas, o pós-teste deve ter 15 respostas e `confirma_identidade = sim`.
- A média do pré-teste **emparelhada** inclui só quem também respondeu validamente ao pós-teste. Isto permite calcular uma evolução justa da mesma amostra.
- Nota em 15 = número de respostas iguais à grelha; percentagem = acertos/15×100; nota em 20 = acertos/15×20.
- O painel recalcula a partir das respostas `q01…q15`. Se `total_acertos` gravado no Kobo for diferente, a auditoria apresenta a ocorrência.
- Se ainda não houver pós-teste, não se apresenta uma evolução fictícia.
- Filtros: edição, instituição, situação do participante, pesquisa de nome.
- Dados atualizados periodicamente em cache (3 minutos); botão lateral força atualização.

## Validação operacional

1. Confirma que o token permite ler **ambos** os projetos.
2. Se quiseres, experimenta primeiro a app no *Modo demonstração*; identifica-se claramente como fictício.
3. Volta ao modo real e verifica os totais: devem corresponder às submissões válidas do Kobo.
4. Em Qualidade dos dados, verifica registos sem `participante_id`, pós-testes órfãos e notas inconsistentes.
5. Confirma manualmente um participante no Kobo e compara acertos, percentagens e evolução com o painel.

O ambiente de desenvolvimento utilizado para preparar este pacote não teve conectividade DNS com `kf.kobo.ucp-pch.org`; por isso, **não foram consultados nem validados os quatro registos reais**. A ligação real deve ser confirmada quando a app for executada num ambiente com acesso ao servidor.
