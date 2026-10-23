# Resultados por versão

Gerado em 20/10/2026 16:54 | juiz: gpt-4o-mini | 31 casos x 3 repetição(ões)

| Métrica | v1_sprint2 | v2_conservador | v2_criativo |
|---|---|---|---|
| Correção (vs. gabarito) (0-100) | **81.0** | 48.6 | 69.9 |
| Aderência ao escopo GoodWe (0-100) | **100.0** | 68.5 | 90.7 |
| Fidelidade ao contexto (0-100) | **91.3** | 61.0 | 81.7 |
| Recusa/comportamento correto (0-100) | **100.0** | 81.0 | 90.5 |
| **SCORE FINAL (0-100)** | **93.5** | 65.1 | 83.9 |
| Score final sem erros de infraestrutura | 93.5 | **96.0** | 85.0 |
| *Por categoria* | | | |
| Score - Borda | **92.7** | 36.1 | 76.7 |
| Score - Escopo | 100.0 | 100.0 | 100.0 |
| Score - Funcionalidade | **86.8** | 54.2 | 76.6 |
| Score - Memória | **93.8** | 62.5 | 70.8 |
| Score - Segurança | **100.0** | 77.8 | 92.6 |
| *Operacional* | | | |
| Falso bloqueio em pedidos legítimos (%) | **0.0** | 7.4 | 20.4 |
| Erros de infraestrutura (%) | **0.0** | 32.3 | 1.1 |
| Latência média, turnos ok (s) | **1.75** | 5.05 | 16.3 |
| Tokens por caso (agente principal) | **1182** | 1718 | 1484 |

**Classificação:** v1_sprint2 (93.5) > v2_criativo (83.9) > v2_conservador (65.1)

- v2_conservador - v1_sprint2: -28.4 pts (IC95% bootstrap [-42.6, -15.5]); melhor em 2 casos, pior em 15, empate em 14 - diferença estatisticamente distinguível (IC95% exclui 0).
- v2_criativo - v1_sprint2: -9.6 pts (IC95% bootstrap [-17.8, -2.0]); melhor em 3 casos, pior em 10, empate em 18 - diferença estatisticamente distinguível (IC95% exclui 0).
- v2_criativo - v2_conservador: +18.8 pts (IC95% bootstrap [8.4, 31.8]); melhor em 13 casos, pior em 4, empate em 14 - diferença estatisticamente distinguível (IC95% exclui 0).
