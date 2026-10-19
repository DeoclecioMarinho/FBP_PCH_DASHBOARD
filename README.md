# Dashboard de Formação FBP — Projeto de Capital Humano · v4

**Aplicação Streamlit para acompanhamento dos 15 itens do pré e pós-teste FBP.**

## Estrutura e decisões de desenho

Três páginas principais, com menu lateral compacto:

1. **Dashboard** — total de participantes com pré-teste completo, pós-testes associados, média inicial, evolução dos pares válidos, cinco perguntas mais difíceis e consulta individual.
2. **Aprendizagem** — resultados por competência, por pergunta, análise pré/pós exclusivamente para os mesmos participantes, evolução por instituição e exportação.
3. **Qualidade dos dados** — duplicados reais (mesmo ID), duplicados potenciais (mesmo nome e instituição com IDs diferentes), submissões incompletas, notas divergentes, respostas sem correspondência e gestão cuidadosa de duplicados.

**Não existe meta fixa de 40 participantes.** O sistema conta apenas os participantes registados; o número de 40 referido inicialmente era indicativo e não é tratado como valor de referência. «Ainda sem pós-teste» = pessoas com pré-teste completo, mas sem pós-teste válido associado. **Não corresponde a ausências antes do pré-teste**, que não podemos identificar sem uma lista de presenças.

**Tabelas:** HTML responsivo, linhas com quebra automática e paginação (6 a 8 registos por página). Sem barras de scroll internas, mesmo com mais de 40 participantes.

## Instalação na aplicação Streamlit existente

1. Descompactar o ZIP e copiar **todos** os ficheiros `.py`, `questionario.json`, `requirements.txt`, a pasta `assets/` e a pasta `.streamlit/` para a raiz do repositório GitHub usado pelo dashboard atual. Substituir os ficheiros da versão anterior. `tests/` pode também ser copiada.
2. Confirmar o ficheiro de entrada **`app.py`** nas configurações da aplicação Streamlit Cloud.
3. Em **Manage app → Settings → Secrets**, adicionar as variáveis do ficheiro `SECRETS_EXEMPLO.toml`, substituindo apenas os campos de credenciais. **Não guardar o token nem as passwords no GitHub.**
4. Fazer *Commit changes*. O Streamlit atualiza a aplicação. Se necessário, clicar em *Reboot app*.
5. Na barra lateral, usar **Atualizar Kobo** para forçar nova leitura. Os dados são consultados automaticamente a cada 120 segundos.

### Exemplo de Secrets

```toml
KOBO_BASE_URL = "https://kf.kobo.ucp-pch.org"
KOBO_PRE_UID = "a9UStPiv4QDyzfZeHiBzwu"
KOBO_POS_UID = "a2JXAwUZP7h3z3nUmpfchj"
KOBO_TOKEN = "INSERIR_NOVO_TOKEN"
DASHBOARD_PASSWORD = "CRIAR_PASSWORD_FORTE"
ENABLE_KOBO_DELETE = false
ADMIN_DELETE_PASSWORD = "CRIAR_SEGUNDA_PASSWORD_FORTE"
```

- **KOBO_TOKEN** autentica os pedidos à API. Trocar o token divulgado anteriormente.
- **DASHBOARD_PASSWORD** protege nomes e resultados; se ausente, apenas indicadores agregados são apresentados.
- **ENABLE_KOBO_DELETE** ativa a gestão definitiva de exclusões. **Por defeito = false**.
- **ADMIN_DELETE_PASSWORD** deve ser **diferente** da password do dashboard e é exigida para cada eliminação.

## Tratamento de duplicados

O sistema não elimina automaticamente qualquer submissão.

- **IDs iguais (mesma fase):** escolhe um registo canónico, dando prioridade ao primeiro registo com 15 respostas completas; os outros tornam-se candidatos à eliminação após verificação.
- **Nomes e instituição iguais com IDs diferentes na mesma edição:** são **possíveis** duplicados, não uma prova. Dois trabalhadores podem ter o mesmo nome. A revisão deve confirmar identidade e contactos antes da exclusão. Não se apaga um pré-teste se houver pós-teste associado ao ID a eliminar.
- Não se elimina a última submissão de um identificador.
- Antes de ativar a eliminação, confirmar que o **token Kobo tem permissão para apagar submissões**. Uma conta com apenas leitura poderá ver candidatos, mas o Kobo recusará os pedidos DELETE.
- Cada exclusão: selecionar **grupo** → escolher **submissão por Kobo ID** → descarregar **cópia de segurança JSON** → confirmar password de administração → escrever `ELIMINAR <ID>` → assinalar confirmação → executar. Antes de apagar, a aplicação consulta a API de novo e verifica se a remoção continua segura. Apenas um registo é eliminado por operação.
- Uma remoção por API é **definitiva**. A cópia de segurança deve ser arquivada fora do Streamlit. O dashboard não constitui um arquivo de auditoria permanente. Para uma trilha auditável, guardar o backup e a autorização institucional.

**Cuidado:** o pós-teste utiliza uma ligação nativa ao pré-teste. Eliminações no formulário original podem impactar ligações e submissões relacionadas. Faça o primeiro teste com registos fictícios.

Endpoint oficial de remoção: `DELETE /api/v2/assets/{asset_uid}/data/{submission_id}/`. Fonte: [KoboToolbox API v2](https://eu.kobotoolbox.org/api/v2/docs/).

## Definição dos indicadores

- **Participantes com pré-teste:** um registo completo por `participante_id` válido; outras submissões com o mesmo ID são sinalizadas separadamente.
- **Pós-testes associados:** ID igual, identidade confirmada e 15 respostas válidas. Registos incompletos ou não confirmados não entram nas médias emparelhadas.
- **Média inicial:** média das percentagens de acertos de todos os participantes com pré-teste completo selecionados nos filtros.
- **Ganho médio:** média da diferença `Pós (%) - Pré (%)`, dos mesmos participantes, em pontos percentuais.
- **Dificuldades:** taxa de acerto de cada uma das 15 questões no pré-teste; perguntas com menos de 50% são assinaladas como pontos a reforçar após volume suficiente de respostas.
- **Instituições:** comparação das médias pré/pós dos **mesmos participantes** de cada instituição; evita comparação de amostras diferentes.
- **Questionário:** a grelha de 15 respostas foi preservada conforme o documento original. A questão 2 precisa de validação pedagógica, por poder ter alternativas ambíguas.

## Testes

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
streamlit run app.py
```

Os testes cobrem cálculos, associação pré/pós, consulta de API, paginação, proteção do registo canónico, duplicados com a mesma identidade em edições diferentes, permissão de eliminação e backup JSON.

**Estado:** código compilado e 20 testes automatizados passaram (pytest). Esta sessão não teve acesso HTTP ao servidor Kobo e não conseguiu executar um servidor Streamlit local (biblioteca não instalada/indisponível para instalação). **A interface e a API DELETE ainda precisam de validação na aplicação publicada e numa conta autorizada.**
