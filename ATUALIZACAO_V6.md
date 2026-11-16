# Dashboard FBP/PCH — V6 · Reconciliação e duplicados

## Objetivo

Reconciliar os registos dos dois formulários Kobo **sem adulterar a base**. A app lê os mesmos projetos já configurados. Mantém o Dashboard, Aprendizagem e Qualidade dos Dados, com tabelas paginadas e ficha de cada participante.

**Os valores reais não foram vistos nesta sessão**: `kf.kobo.ucp-pch.org` não foi acessível por DNS a partir deste ambiente. A deteção exata será feita quando a V6 estiver no Streamlit Cloud, que consegue aceder ao servidor com as Secrets da aplicação.

## Regras de reconciliação

### A) Duplicados óbvios (exclusão lógica automática)

Duas submissões ao pré-teste são tratadas como **repetição técnica**, e uma delas é excluída dos indicadores, apenas quando:

- têm nome normalizado, instituição e edição idênticos;
- ambas têm as **15 respostas válidas e exatamente iguais**;
- têm data/hora de envio legível e intervalo de **até 15 minutos**;
- a submissão a excluir **não possui um pós-teste válido associado ao seu identificador**.

O formulário Kobo original **não é alterado automaticamente**. Na página *Qualidade dos Dados*, as repetições excluídas aparecem com o ID mantido e o ID excluído. A eliminação física — caso seja mesmo desejada — é individual e exige autenticação de administrador, cópia JSON, confirmação textual e nova verificação no servidor.

Uma submissão tardia com respostas diferentes não é eliminada como duplicado: pode representar uma segunda avaliação. Nomes idênticos com identificadores diferentes mas respostas diferentes também não são fundidos. Se houver três ou mais pré-testes do mesmo nome/instituição/edição, o caso exige revisão específica.

### B) Segundo pré-teste como pós-teste recuperado (após validação)

A V6 propõe candidatos quando:

- existem **exatamente dois pré-testes completos** para o mesmo nome, instituição e edição;
- a data do segundo é posterior à do primeiro, com pelo menos **30 minutos** de intervalo;
- não há qualquer pós-teste submetido sob nenhum dos dois identificadores;
- as duas submissões não são uma repetição técnica já excluída.

A existência de dois pré-testes, por si só, **não prova que o segundo tenha sido aplicado depois da formação**. Por isso o candidato **não entra nas médias de pós-teste até ser validado por um responsável**. O administrador tem de confirmar que a segunda avaliação ocorreu depois da formação, indicar o seu nome e uma justificação.

Ao aprovar, o segundo pré-teste passa a ser tratado **apenas na análise** como `Pós recuperado (2.º pré)` e o seu identificador de origem é preservado. A ficha individual, os resultados por pergunta, as médias comparativas e as exportações passam a usar esse registo como pós-teste recuperado. A base Kobo continua intacta.

### C) Como conservar as aprovações

As aprovações efetuadas na aplicação valem imediatamente **na sessão atual**. Para permanecerem após reiniciar a app, em *Qualidade dos Dados* descarrega `reconciliacoes.csv` em **Guardar decisões para GitHub (CSV)** e substitui o ficheiro `data/reconciliacoes.csv` no mesmo repositório GitHub da app. Não guardes este ficheiro com um nome diferente.

Também é possível importar um CSV de decisões através do painel, para aplicar as decisões apenas na sessão corrente. A cada leitura da base o sistema confirma que os registos continuam elegíveis (não aceita decisões obsoletas se surgir um pós real).

### D) Definição dos resultados

- **Pré-teste válido**: primeiro registo completo, por participante, depois das exclusões lógicas.
- **Pós-teste real**: submissão confirmada no formulário de pós-teste e ligada pelo identificador.
- **Pós recuperado**: segundo pré-teste expressamente validado por um responsável e associado ao primeiro pré-teste.
- **Pós pendente**: sem pós real ou recuperado validado.
- **Evolução**: percentagem de acertos no pós menos a percentagem no pré, apenas entre pares válidos.
- **Origem pós**: coluna explícita na exportação nominal para distinguir Kobo e recuperado.

## Como publicar

1. Faz cópia de segurança do repositório existente.
2. Substitui o `app.py`, `analysis.py`, `quality.py` e `individual.py`; adiciona **`reconciliacao.py`** e a pasta **`data/`**. É mais simples atualizar o repositório com o conteúdo completo deste ZIP, **sem apagar as Secrets configuradas no Streamlit Cloud**.
3. Mantém nas Secrets `KOBO_BASE_URL`, `KOBO_PRE_UID`, `KOBO_POS_UID`, `KOBO_TOKEN` e `DASHBOARD_PASSWORD`.
4. Deixa `ENABLE_KOBO_DELETE = false` até terminares a revisão. Ativa apenas se quiseres eliminar fisicamente as repetições técnicas já identificadas e após garantir o backup.
5. Em **Qualidade dos Dados**, primeiro vê as repetições excluídas, depois avalia os segundos pré-testes propostos. Aprova apenas os que efetivamente ocorreram após a formação.
6. Descarrega e conserva os relatórios de auditoria e o `reconciliacoes.csv`.

**Aviso de proteção:** como o pós-teste do Kobo utiliza a ligação dinâmica ao pré-teste, apagar uma submissão do pré-teste pode afetar a origem dessa ligação. Antes de uma exclusão física, guarda o backup; nunca apagues o registo escolhido como segundo pós recuperado.

## Testes locais

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
streamlit run app.py
```

A V6 preserva a lógica de pontuação por 15 perguntas (1 ponto por resposta correta). O gráfico de dificuldades continua a mostrar códigos P01–P15 com o enunciado completo no hover.
