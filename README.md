# Dashboard PCH–FBP | Versão 7 (auditoria de 16/11/2026)

Painel Streamlit para acompanhamento de avaliações pré/pós-teste, ligado em tempo real ao servidor Kobo PCH. A versão 7 inclui **curadoria específica de registos** com validação por identificador, UUID e assinatura das 15 respostas.

## Instalação / atualização

1. Fazer cópia de segurança do repositório atual.
2. Substituir os ficheiros da aplicação pelos ficheiros desta pasta, incluindo `curadoria.py` e `data/curadoria_2026-11-16.json`.
3. **Não colocar as duas bases XLSX nem o relatório nominal num repositório público.** Esses ficheiros são apenas materiais privados de auditoria.
4. Configurar `KOBO_BASE_URL`, `KOBO_PRE_UID`, `KOBO_POS_UID` e `KOBO_TOKEN` nas **Secrets do Streamlit** (não no código).
5. Configurar `DASHBOARD_PASSWORD` nas Secrets para aceder às tabelas nominais e decisões de qualidade. Deixar `ENABLE_KOBO_DELETE=false`, salvo decisão expressa do administrador.
6. Publicar e conferir os 33 participantes, os 30 pares com os dois recuperados incluídos e os 3 pendentes, **desde que o Kobo continue com as mesmas submissões das extrações de 16/11/2026**.

Exemplo **sem token** de Secrets:

```toml
KOBO_BASE_URL = "https://kf.kobo.ucp-pch.org"
KOBO_PRE_UID = "a9UStPiv4QDyzfZeHiBzwu"
KOBO_POS_UID = "a2JXAwUZP7h3z3nUmpfchj"
KOBO_TOKEN = "INSERIR_TOKEN_NAS_SECRETS"
DASHBOARD_PASSWORD = "DEFINIR_UMA_PALAVRA_PASSE_FORTE"
ENABLE_KOBO_DELETE = false
```

## O que foi corrigido na base de 16/11/2026

- **41 pré-testes / 29 pós-testes** brutos, incluindo um provável teste técnico.
- **8 pré-testes** não contabilizados como pré independentes (inclui registo de teste, inscrições repetidas e duas avaliações utilizadas como pós provisórios).
- **1 pós-teste** retirado provisoriamente dos resultados por ter características de teste técnico.
- **2 pós-testes verdadeiros** reassociados ao primeiro pré correto; nenhum foi descartado.
- **2 segundos pré-testes** contabilizados como pós **provisórios**.
- Resultado: **33 participantes**, **30 pares comparáveis**, **3 casos sem pós**. A identidade de um registo com nome semelhante ainda exige confirmação.

Na barra lateral existe um interruptor **Incluir 2 pós provisórios**. Desativando-o, permanecem 33 participantes e 28 pares exclusivamente provenientes do pós-teste oficial. Os números mudam automaticamente caso cheguem novas submissões.

## Segurança e transparência

A curadoria **não apaga nem edita submissões no Kobo**. Atua na camada de análise do Streamlit, e só sobre os IDs específicos auditados. Cada regra verifica simultaneamente o ID da submissão, o UUID do participante, a nota e a assinatura das respostas. Se os dados não corresponderem, a ação é bloqueada e surge um aviso em Qualidade dos dados.

Os valores de classificação são recalculados a partir das 15 respostas. Uma avaliação recuperada do segundo pré é sempre identificada como **provisória** e não é apresentada como pós-teste originalmente submetido no formulário final.

## Páginas

- **Dashboard:** participantes, cobertura, médias, evolução, perguntas com menor taxa de acerto, resultados individuais.
- **Aprendizagem:** comparação por pergunta, competência e instituição; ficha individual com respostas pré/pós.
- **Qualidade dos dados:** histórico de decisões, duplicados, verificações e exportações. Eliminação física, se alguma vez for ativada, exige autorização e revalidação independente.

## Limitações a confirmar

- Rever o tratamento do terceiro pré-teste num grupo com três tentativas.
- Confirmar se dois nomes parcialmente coincidentes correspondem à mesma pessoa (funções declaradas diferentes); por segurança continuam separados.
- Confirmar a exclusão do registo técnico da equipa.
- Confirmar com o formador a interpretação da resposta oficial da questão **P02**, cuja formulação admite leitura próxima de mais de uma opção.

O relatório individual detalhado é entregue separadamente no ficheiro `FBP_PCH_Auditoria_Resultados_16Nov2026.xlsx` e **não está incluído neste ZIP de aplicação**.
