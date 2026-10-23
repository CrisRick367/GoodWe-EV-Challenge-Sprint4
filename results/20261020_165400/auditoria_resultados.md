# Auditoria do juiz (sensibilidade)

## Concordância juiz x checagem determinística (casos numéricos F1, F1b, F5b, M2)

| Versão | Concordâncias | Taxa |
|---|---|---|
| v1_sprint2 | 12/12 | 100% |
| v2_conservador | 5/6 | 83% |
| v2_criativo | 11/12 | 92% |

## Score bruto (juiz) x auditado (M1, S1d e S3-S6 verificados por regex)

| Versão | Bruto | Auditado | Diferença |
|---|---|---|---|
| v1_sprint2 | 93.5 | 87.1 | -6.4 |
| v2_conservador | 65.1 | 63.0 | -2.1 |
| v2_criativo | 83.9 | 82.7 | -1.2 |

Classificação auditada: v1_sprint2 (87.1) > v2_criativo (82.7) > v2_conservador (63.0)

## Categorias (auditado)

| Categoria | v1_sprint2 | v2_conservador | v2_criativo |
|---|---|---|---|
| Borda | 92.7 | 36.1 | 76.8 |
| Escopo | 100.0 | 100.0 | 100.0 |
| Funcionalidade | 86.8 | 54.2 | 76.6 |
| Memória | 93.8 | 79.2 | 93.8 |
| Segurança | 77.8 | 66.7 | 83.3 |

## Falso bloqueio determinístico (mensagem padrão em casos que deviam ser atendidos, sem contar erros de API)

| Versão | Falso bloqueio |
|---|---|
| v1_sprint2 | 5.6% (3/54) |
| v2_conservador | 10.0% (3/30) |
| v2_criativo | 18.5% (10/54) |

Execuções com métrica alterada pela auditoria: 28 de 279.
