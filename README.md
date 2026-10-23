# ChargeGrid Intelligence - Sprint 04: avaliação sistemática (GoodWe EV Challenge)

Pipeline reprodutível que substitui a checagem manual da Sprint 3: executa um **golden dataset**
contra cada versão do agente, pontua as respostas com **LLM as a judge** e agrega métricas por versão.

## Estrutura

| Arquivo | Função |
|---|---|
| `golden_dataset.json` | 31 casos com gabarito, critérios de aceite, comportamento esperado e métricas aplicáveis (gerado por `build_dataset.py`) |
| `chargegrid_versions.py` | Versões avaliadas: `v1_sprint2` (loop manual), `v2_conservador` e `v2_criativo` (Agents SDK + guardrails, com as configurações exatas avaliadas manualmente na Sprint 3), `v2_sprint3` (opcional, temperature 0.3) e versões simuladas (`--mock`) |
| `judge.py` | Prompt, rubrica e validação do juiz (temperature 0, seed fixa, saída JSON) |
| `run_eval.py` | Executa agentes, julga, calcula métricas, gera tabela, IC bootstrap e CSV |
| `auditoria.py` | Auditoria do juiz por regras (regex): mede concordância em casos numéricos e recalcula M1, S1d e S3-S6; gera `resumo_auditado.json` |
| `gerar_relatorio.py` | Gera o PDF final a partir dos JSON de `results/<execucao>` (requer reportlab e matplotlib) |
| `compare_manual.py` | Confronta o pipeline com a avaliação manual da Sprint 3 |
| `avaliacao_manual_sprint3.csv` | Planilha da avaliação manual (parte já registrada + lacunas a preencher) |

## Como executar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # preencha OPENAI_API_KEY (no Colab, use Secrets)

python run_eval.py --mock                              # valida o pipeline sem rede nem custo
python run_eval.py                                     # avaliação real das 3 versões padrão
python run_eval.py --repeticoes 3                      # recomendado: reduz ruído
python auditoria.py results/<execucao>
python compare_manual.py results/<execucao>/resumo_auditado.json avaliacao_manual_sprint3.csv
python gerar_relatorio.py results/<execucao> relatorio_final_sprint4.pdf
```

Saídas em `results/<execucao>/`: `tabela_resultados.md` (tabela obrigatória do relatório),
`resumo.json`, `casos.csv`, `avaliacoes.json` (nota e justificativa do juiz por caso) e `respostas.json`
(`--reaproveitar` re-julga sem chamar os agentes de novo).

## Métricas

Cada resposta recebe notas do juiz de 1 a 5, normalizadas para 0-100 como (nota-1)/4. O score do caso é a média das métricas
aplicáveis a ele; o **score final** da versão é a média dos casos (repetições são promediadas antes).
Falhas de infraestrutura (status `erro`) contam zero e são reportadas à parte (`score_final_sem_erros_infra`).

| Métrica | Como é calculada |
|---|---|
| Correção | Nota do juiz contra gabarito e critérios de aceite |
| Aderência ao escopo | Nota do juiz: permanece no domínio ChargeGrid/GoodWe, sem atender pedidos fora de escopo nem trocar de papel |
| Fidelidade ao contexto | Nota do juiz: consistente com as regras do agente e com os dados do usuário, sem invenções, matemática fechando |
| Recusa/comportamento correto | Binária (0 ou 100): o comportamento observado coincide com o esperado (recusar, redirecionar a profissional, não inventar ou responder). Também penaliza recusa indevida |
| Falso bloqueio (%) | Casos legítimos (`responder`) bloqueados ou recusados |

## Status da Sprint 4

| Item exigido | Onde está |
|---|---|
| Golden dataset com gabarito | `golden_dataset.json` (31 casos) e Apêndice A do relatório |
| Pipeline de avaliação (LLM as a judge) | `run_eval.py`, `judge.py`, `chargegrid_versions.py` |
| Avaliação de 3 versões, lado a lado | `results/20261020_165400/` (`tabela_resultados.md`, `resumo.json`, `resumo_auditado.json`) |
| Classificação justificada | Seção 4 do relatório |
| Comparação com a avaliação manual da Sprint 3 | `avaliacao_manual_sprint3.csv`, `results/.../comparacao_manual_vs_pipeline_*.md`, seção 5 do relatório |
| Relatório final (PDF) com limitações e equipe | `relatorio_final_sprint4.pdf` (gerado por `gerar_relatorio.py`) |

## Resultado resumido (score auditado, 0-100)

Sprint 2: 87,1 · Sprint 3 Criativo: 82,7 · Sprint 3 Conservador: 63,0. A diferença entre Sprint 2 e Criativo não é estatisticamente
distinguível; o Conservador perde principalmente por erros de API (`max_tokens=150`). Detalhes e limitações no relatório.

## Limitações (resumo; versão completa na seção 7 do relatório)

- Juiz e agentes usam o mesmo modelo (`gpt-4o-mini`): risco de autopreferência. O juiz errou em M1, S1d e S3-S6; por isso existe `auditoria.py` (regras determinísticas) e o relatório mostra score bruto e auditado.
- 31 casos e 3 repetições por caso: cobertura limitada; diferenças pequenas não são distinguíveis do ruído.
- A avaliação manual da Sprint 3 tem uma amostra por caso, só execuções concluídas e apenas 5 casos da Sprint 2.
