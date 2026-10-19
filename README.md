# Dashboard PCH · Formação FBP — v3 simplificada

**Objetivo:** acompanhar, durante a formação de aproximadamente **40 participantes**, quem concluiu o pré-teste, a qualidade dos registos e **quais as perguntas/temas que precisam de reforço**. No fim, comparar o pré-teste com o pós-teste.

## O que mudou

- **Apenas dois separadores**, sem o menu antigo de quatro páginas: **Durante o pré-teste** e **Resultados finais**.
- Painel principal orientado para decisões rápidas: completados vs. meta de 40, média, perguntas com menos de 50% de respostas certas, cinco perguntas mais difíceis e registos suspeitos.
- **Meta ajustável** na barra lateral. Importante: o número por completar é **estimativa** (meta menos pré-testes completos), não uma lista de nomes dos ausentes. O Kobo só conhece quem já respondeu.
- Lista de participantes, auditoria e exportações numa área secundária, sem poluir o painel.
- Antes de 5 pré-testes completos, mostra aviso de amostra pequena; não toma as tendências como firmes.
- Compara **só pares válidos** de pré/pós-testes pelo mesmo `participante_id`.
- O utilizador nunca vê a grelha de respostas certas no dashboard.
- **Sem modo demonstração na interface pública**.

## Publicar na mesma aplicação Streamlit

1. No repositório GitHub já ligado ao Streamlit, substitui `app.py`, `analysis.py`, `kobo_client.py`, `questionario.json`, `requirements.txt` e adiciona `monitor.py`. Mantém a pasta `assets/logo_pch.png`.
2. Faz *Commit changes*. O Streamlit Cloud atualizará a aplicação automaticamente.
3. Em **Manage app → Settings → Secrets**, confirma a configuração (não incluir o token no GitHub):

```toml
KOBO_BASE_URL = "https://kf.kobo.ucp-pch.org"
KOBO_PRE_UID = "a9UStPiv4QDyzfZeHiBzwu"
KOBO_POS_UID = "a2JXAwUZP7h3z3nUmpfchj"
KOBO_TOKEN = "COLOCAR_AQUI_NOVO_TOKEN"
DASHBOARD_PASSWORD = "ESCOLHER_UMA_PALAVRA_PASSE_FORTE"
```

A configuração `DASHBOARD_PASSWORD` é recomendada para proteger nomes e resultados individuais. Se não for configurada, o dashboard apresenta **apenas dados agregados**, sem tabelas nominativas ou exportações de identificação pessoal.

## Como usar durante a sessão

1. Antes de começar a recolha, definir **meta 40** e selecionar a edição `0001` (se houver várias edições).
2. Durante o pré-teste, clicar em **Atualizar dados Kobo** ou esperar até dois minutos pelo fim da cache.
3. Quando houver respostas suficientes (idealmente 5 ou mais), observar **as cinco perguntas com menor taxa de acertos** e priorizá-las nas explicações do formador.
4. Conferir alertas de registos duplicados ou notas divergentes em **Registos a verificar**.
5. Depois do pós-teste, abrir **Resultados finais** para ver a evolução média e os participantes ainda sem avaliação final.

## Definições dos indicadores

- **Pré-testes completos:** participantes com `participante_id` e 15 respostas válidas. Duplicados do mesmo ID são considerados uma só vez; possíveis nomes iguais com IDs diferentes são sinalizados, mas não fundidos automaticamente.
- **Pré-testes por completar:** `máximo(0, meta - pré-testes completos)`. A meta é aproximada. **Não é possível saber os nomes dos ausentes sem uma lista prévia de presenças.**
- **Média pré:** média de % de acertos de todos os pré-testes completos selecionados, **mesmo sem qualquer pós-teste**.
- **Perguntas com dificuldade:** percentagem de pré-testes completos com resposta correta menor que 50%; antes de 5 respostas, não há alerta classificativo.
- **Pós-testes associados:** pré e pós completos, `participante_id` igual e identidade confirmada.
- **Evolução média:** percentagem média pós menos percentagem média pré **dos mesmos participantes** (pontos percentuais).
- **Chave de correção:** preservada do formulário original, com 15 perguntas; recomenda-se a validação pedagógica pelo formador (particularmente a pergunta 2, que pode parecer ambígua).

## Segurança e atualização

- O token vai **só em Secrets**, nunca no código ou URL. Como foi partilhado na conversa, recomenda-se substituí-lo por um novo.
- O código faz pedidos exclusivamente de leitura à API Kobo.
- **Cache: até 2 minutos**. O botão de atualização força uma nova consulta.
- Dados reais precisam ser validados na instância instalada; a verificação local foi feita com dados de ensaio e testes automatizados.

## Testes locais

```bash
pip install -r requirements.txt pytest
python -m pytest -q tests
streamlit run app.py
```
