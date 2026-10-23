#!/usr/bin/env python3
"""Confronto entre o pipeline automatizado (Sprint 4) e a avaliação manual (Sprint 3).

Uso:
    python compare_manual.py results/<run>/resumo.json avaliacao_manual_sprint3.csv

A planilha manual tem as colunas: caso_id, versao, avaliacao_manual, justificativa, fonte
com avaliacao_manual em {Adequada, Parcialmente Adequada, Inadequada}. Linhas em branco são ignoradas.
O score do pipeline (0-100) é convertido em rótulo com os limiares abaixo, para comparar na mesma escala.
"""
import csv
import json
import statistics
import sys

VALOR = {"adequada": 100.0, "parcialmente adequada": 50.0, "inadequada": 0.0}
LIMIAR_ADEQUADA, LIMIAR_PARCIAL = 80.0, 50.0


def rotulo(score):
    return "Adequada" if score >= LIMIAR_ADEQUADA else ("Parcialmente Adequada" if score >= LIMIAR_PARCIAL else "Inadequada")


def main(resumo_path, manual_path, saida="comparacao_manual_vs_pipeline.md"):
    resumo = json.load(open(resumo_path, encoding="utf-8"))["resumo"]
    linhas = [r for r in csv.DictReader(open(manual_path, encoding="utf-8"))
              if r["avaliacao_manual"].strip().lower() in VALOR]
    if not linhas:
        raise SystemExit("Nenhuma linha preenchida em avaliacao_manual. Preencha a planilha primeiro.")

    out = ["# Pipeline automatizado x avaliação manual (Sprint 3)", "",
           f"Limiares de conversão do score do pipeline: Adequada >= {LIMIAR_ADEQUADA:.0f}; "
           f"Parcialmente Adequada >= {LIMIAR_PARCIAL:.0f}; Inadequada abaixo.", ""]
    divergencias = []
    out += ["## Resumo por versão", "",
            "| Versão | Casos comparados | Média manual | Média pipeline | Diferença (pipeline - manual) | Concordância de rótulo |",
            "|---|---|---|---|---|---|"]
    for versao in resumo:
        pares = []
        for r in linhas:
            if r["versao"] == versao and r["caso_id"] in resumo[versao]["score_por_caso"]:
                manual = VALOR[r["avaliacao_manual"].strip().lower()]
                auto = resumo[versao]["score_por_caso"][r["caso_id"]]
                pares.append((r["caso_id"], manual, auto, r["justificativa"]))
        if not pares:
            continue
        concordam = sum(rotulo(a) == rotulo(m) for _, m, a, _ in pares)
        mm, ma = statistics.mean(p[1] for p in pares), statistics.mean(p[2] for p in pares)
        out.append(f"| {versao} | {len(pares)} | {mm:.1f} | {ma:.1f} | {ma - mm:+.1f} | "
                   f"{concordam}/{len(pares)} ({100 * concordam / len(pares):.0f}%) |")
        for cid, m, a, just in pares:
            if rotulo(a) != rotulo(m):
                divergencias.append((versao, cid, rotulo(m), m, rotulo(a), a, just))

    out += ["", "## Divergências a explicar no relatório (hipótese por linha)", "",
            "| Versão | Caso | Manual | Pipeline | Direção | Hipótese (preencher) |", "|---|---|---|---|---|---|"]
    for versao, cid, rm, m, ra, a, just in divergencias:
        direcao = "pipeline mais severo" if a < m else "pipeline mais brando"
        out.append(f"| {versao} | {cid} | {rm} ({m:.0f}) | {ra} ({a:.0f}) | {direcao} | {just or 'TODO'} |")
    if not divergencias:
        out.append("| - | - | - | - | - | Sem divergências de rótulo nos casos comparados. |")
    open(saida, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\nSalvo em {saida}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
