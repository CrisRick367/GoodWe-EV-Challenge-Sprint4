#!/usr/bin/env python3
"""Pipeline de avaliação do ChargeGrid Intelligence (Sprint 4).

Fluxo:  golden_dataset.json  ->  executa cada versão  ->  LLM as a judge  ->  métricas  ->  relatório

Exemplos:
    python run_eval.py --mock                                  # teste do pipeline sem rede/custo
    python run_eval.py --versoes v1_sprint2 v2_sprint3         # avaliação real (usa OPENAI_API_KEY)
    python run_eval.py --versoes v1_sprint2 v2_sprint3 --repeticoes 3
    python run_eval.py --reaproveitar results/<run>/respostas.json   # só re-julga, sem chamar os agentes
"""
import argparse
import csv
import json
import os
import random
import statistics
import time
from collections import defaultdict
from datetime import datetime

from chargegrid_versions import SYSTEM_PROMPT_SPRINT3, criar_versoes
import judge as judge_mod

METRICAS = ["correcao", "aderencia_escopo", "fidelidade", "recusa_correta"]
ROTULO = {
    "correcao": "Correção (vs. gabarito)",
    "aderencia_escopo": "Aderência ao escopo GoodWe",
    "fidelidade": "Fidelidade ao contexto",
    "recusa_correta": "Recusa/comportamento correto",
}


# ---------------------------------------------------------------- execução dos agentes
def executar_agentes(versoes, casos, repeticoes, pausa):
    respostas = []
    for v in versoes:
        for caso in casos:
            for rep in range(1, repeticoes + 1):
                sessao = v.nova_sessao()  # sessão nova por caso e repetição: sem vazamento entre testes
                turnos = []
                for msg in caso["turnos"]:
                    time.sleep(pausa)
                    t = v.perguntar(sessao, msg)
                    turnos.append({"mensagem": msg, **t})
                print(f"  [{v.nome}] {caso['id']:<5} rep {rep}  -> {turnos[-1]['status']}")
                if turnos[-1]["status"] == "erro":
                    print("      motivo:", turnos[-1]["resposta"][:300].replace("\n", " "))
                respostas.append({"versao": v.nome, "caso_id": caso["id"], "rep": rep, "turnos": turnos})
    return respostas


# ---------------------------------------------------------------- julgamento
def norm_nota(n):
    return (n - 1) / 4 * 100


def avaliar(respostas, casos, juiz):
    por_id = {c["id"]: c for c in casos}
    avaliacoes = []
    for r in respostas:
        caso = por_id[r["caso_id"]]
        status_final = r["turnos"][-1]["status"]
        erro_infra = any(t["status"] == "erro" for t in r["turnos"])
        item = {"versao": r["versao"], "caso_id": caso["id"], "rep": r["rep"], "categoria": caso["categoria"],
                "status_final": status_final, "erro_infra": erro_infra,
                "latencia_s": statistics.mean(t["latencia_s"] for t in r["turnos"]),
                "tokens": sum(t["tokens"] for t in r["turnos"]), "metricas": {}, "juiz": None}
        if erro_infra:  # falha de infraestrutura: conta zero, mas é sinalizada e reportada à parte
            item["metricas"] = {m: 0.0 for m in caso["metricas"]}
        else:
            transcricao = [(t["mensagem"], t["resposta"]) for t in r["turnos"]]
            saida, modelo_juiz = juiz.julgar(caso, transcricao, SYSTEM_PROMPT_SPRINT3)
            item["juiz"], item["modelo_juiz"] = saida, modelo_juiz
            for m in caso["metricas"]:
                item["metricas"][m] = (100.0 if saida["atendeu_comportamento_esperado"] else 0.0) \
                    if m == "recusa_correta" else norm_nota(saida[m]["nota"])
            item["recusou"] = saida["recusou"]
        item["score_caso"] = statistics.mean(item["metricas"].values())
        item["bloqueado"] = status_final.startswith("bloqueado")
        avaliacoes.append(item)
    return avaliacoes


# ---------------------------------------------------------------- agregação
def media_por_caso(itens):
    """Média das repetições de cada caso (cada caso pesa igual)."""
    por_caso = defaultdict(list)
    for i in itens:
        por_caso[i["caso_id"]].append(i)
    return {cid: reps for cid, reps in por_caso.items()}


def agregar(avaliacoes, casos):
    por_id = {c["id"]: c for c in casos}
    versoes = sorted({a["versao"] for a in avaliacoes}, key=lambda v: [a["versao"] for a in avaliacoes].index(v))
    resumo = {}
    for v in versoes:
        itens = [a for a in avaliacoes if a["versao"] == v]
        casos_v = media_por_caso(itens)
        score_casos = {cid: statistics.mean(r["score_caso"] for r in reps) for cid, reps in casos_v.items()}
        sem_erro = [r for r in itens if not r["erro_infra"]]
        casos_sem_erro = media_por_caso(sem_erro)
        por_metrica = {}
        for m in METRICAS:
            vals = [statistics.mean(r["metricas"][m] for r in reps) for cid, reps in casos_v.items() if m in por_id[cid]["metricas"]]
            por_metrica[m] = round(statistics.mean(vals), 1) if vals else None
        por_categoria = {}
        for cat in sorted({c["categoria"] for c in casos}):
            vals = [s for cid, s in score_casos.items() if por_id[cid]["categoria"] == cat]
            por_categoria[cat] = round(statistics.mean(vals), 1) if vals else None
        deve_responder = [r for r in itens if por_id[r["caso_id"]]["comportamento_esperado"] in ("responder",)]
        falso_bloqueio = [r for r in deve_responder if r["bloqueado"] or (r.get("recusou") and not r["erro_infra"])]
        ok = [r for r in itens if r["status_final"] == "ok"]
        resumo[v] = {
            "score_final": round(statistics.mean(score_casos.values()), 1),
            "score_final_sem_erros_infra": round(statistics.mean(
                statistics.mean(x["score_caso"] for x in reps) for reps in casos_sem_erro.values()), 1) if casos_sem_erro else None,
            "por_metrica": por_metrica,
            "por_categoria": por_categoria,
            "taxa_falso_bloqueio_pct": round(100 * len(falso_bloqueio) / len(deve_responder), 1) if deve_responder else None,
            "taxa_erro_infra_pct": round(100 * sum(r["erro_infra"] for r in itens) / len(itens), 1),
            "latencia_media_ok_s": round(statistics.mean(r["latencia_s"] for r in ok), 2) if ok else None,
            "tokens_medio_por_caso": round(statistics.mean(r["tokens"] for r in ok)) if ok else None,
            "n_casos": len(casos_v), "n_execucoes": len(itens),
            "score_por_caso": {cid: round(s, 1) for cid, s in score_casos.items()},
        }
    return resumo


def ic_bootstrap(diffs, n=2000, seed=7):
    rnd = random.Random(seed)
    medias = sorted(statistics.mean(rnd.choices(diffs, k=len(diffs))) for _ in range(n))
    return round(medias[int(0.025 * n)], 1), round(medias[int(0.975 * n)], 1)


def comparar_pares(resumo):
    versoes = list(resumo)
    pares = []
    for i in range(len(versoes)):
        for j in range(i + 1, len(versoes)):
            a, b = versoes[i], versoes[j]
            comuns = sorted(set(resumo[a]["score_por_caso"]) & set(resumo[b]["score_por_caso"]))
            diffs = [resumo[b]["score_por_caso"][c] - resumo[a]["score_por_caso"][c] for c in comuns]
            lo, hi = ic_bootstrap(diffs)
            pares.append({"a": a, "b": b, "diferenca_media_b_menos_a": round(statistics.mean(diffs), 1),
                          "ic95": [lo, hi], "casos_b_melhor": sum(d > 0 for d in diffs),
                          "casos_a_melhor": sum(d < 0 for d in diffs), "empates": sum(d == 0 for d in diffs),
                          "significativo": not (lo <= 0 <= hi)})
    return pares


# ---------------------------------------------------------------- relatório
def tabela_markdown(resumo, pares):
    vs = list(resumo)
    melhor = lambda vals, maior=True: (max if maior else min)(v for v in vals if v is not None) if any(v is not None for v in vals) else None
    def linha(rotulo, getter, maior=True, fmt="{}"):
        vals = [getter(resumo[v]) for v in vs]
        alvo = melhor(vals, maior)
        cel = [("**" + fmt.format(x) + "**") if (x is not None and x == alvo and len(set(vals)) > 1) else
               ("-" if x is None else fmt.format(x)) for x in vals]
        return f"| {rotulo} | " + " | ".join(cel) + " |"
    L = ["| Métrica | " + " | ".join(vs) + " |", "|---|" + "---|" * len(vs)]
    for m in METRICAS:
        L.append(linha(ROTULO[m] + " (0-100)", lambda r, m=m: r["por_metrica"][m]))
    L.append(linha("**SCORE FINAL (0-100)**", lambda r: r["score_final"]))
    L.append(linha("Score final sem erros de infraestrutura", lambda r: r["score_final_sem_erros_infra"]))
    L.append("| *Por categoria* |" + " |" * len(vs))
    for cat in resumo[vs[0]]["por_categoria"]:
        L.append(linha(f"Score - {cat}", lambda r, cat=cat: r["por_categoria"][cat]))
    L.append("| *Operacional* |" + " |" * len(vs))
    L.append(linha("Falso bloqueio em pedidos legítimos (%)", lambda r: r["taxa_falso_bloqueio_pct"], False))
    L.append(linha("Erros de infraestrutura (%)", lambda r: r["taxa_erro_infra_pct"], False))
    L.append(linha("Latência média, turnos ok (s)", lambda r: r["latencia_media_ok_s"], False))
    L.append(linha("Tokens por caso (agente principal)", lambda r: r["tokens_medio_por_caso"], False))
    texto = "\n".join(L)
    ranking = sorted(vs, key=lambda v: -resumo[v]["score_final"])
    texto += "\n\n**Classificação:** " + " > ".join(f"{v} ({resumo[v]['score_final']})" for v in ranking) + "\n"
    for p in pares:
        sig = "diferença estatisticamente distinguível (IC95% exclui 0)" if p["significativo"] else \
              "diferença NÃO distinguível de zero (IC95% inclui 0)"
        texto += (f"\n- {p['b']} - {p['a']}: {p['diferenca_media_b_menos_a']:+} pts (IC95% bootstrap "
                  f"[{p['ic95'][0]}, {p['ic95'][1]}]); melhor em {p['casos_b_melhor']} casos, pior em "
                  f"{p['casos_a_melhor']}, empate em {p['empates']} - {sig}.")
    return texto + "\n"


def salvar(pasta, casos, respostas, avaliacoes, resumo, pares, meta):
    os.makedirs(pasta, exist_ok=True)
    json.dump({"meta": meta, "respostas": respostas}, open(f"{pasta}/respostas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(avaliacoes, open(f"{pasta}/avaliacoes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"meta": meta, "resumo": resumo, "comparacoes": pares}, open(f"{pasta}/resumo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(f"{pasta}/tabela_resultados.md", "w", encoding="utf-8") as f:
        f.write(f"# Resultados por versão\n\nGerado em {meta['gerado_em']} | juiz: {meta['modelo_juiz']} | "
                f"{meta['n_casos']} casos x {meta['repeticoes']} repetição(ões)\n\n" + tabela_markdown(resumo, pares))
    vs = list(resumo)
    with open(f"{pasta}/casos.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["caso_id", "categoria"] + [f"score_{v}" for v in vs])
        for c in casos:
            w.writerow([c["id"], c["categoria"]] + [resumo[v]["score_por_caso"].get(c["id"], "") for v in vs])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--versoes", nargs="+", default=["v1_sprint2", "v2_conservador", "v2_criativo"])
    ap.add_argument("--repeticoes", type=int, default=1)
    ap.add_argument("--juiz-modelo", default=None)
    ap.add_argument("--dataset", default="golden_dataset.json")
    ap.add_argument("--casos", nargs="*", help="ids específicos (ex.: F1 S3)")
    ap.add_argument("--pausa", type=float, default=0.5, help="segundos entre chamadas (rate limit)")
    ap.add_argument("--mock", action="store_true", help="agentes e juiz simulados (sem rede)")
    ap.add_argument("--reaproveitar", help="respostas.json de uma execução anterior (apenas re-julga)")
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()

    casos = json.load(open(a.dataset, encoding="utf-8"))["casos"]
    if a.casos:
        casos = [c for c in casos if c["id"] in a.casos]
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + ("_mock" if a.mock else "")
    pasta = a.saida or os.path.join("results", run_id)

    if a.reaproveitar:
        respostas = json.load(open(a.reaproveitar, encoding="utf-8"))["respostas"]
        respostas = [r for r in respostas if r["caso_id"] in {c["id"] for c in casos}]
        a.repeticoes = max(r["rep"] for r in respostas)
    else:
        versoes = criar_versoes(a.versoes, mock=a.mock)
        print(f"Executando {len(casos)} casos x {len(versoes)} versões x {a.repeticoes} repetição(ões)...")
        respostas = executar_agentes(versoes, casos, a.repeticoes, 0 if a.mock else a.pausa)

    juiz = judge_mod.JuizMock() if a.mock else judge_mod.Juiz(a.juiz_modelo)
    print("Julgando respostas...")
    avaliacoes = avaliar(respostas, casos, juiz)
    resumo = agregar(avaliacoes, casos)
    pares = comparar_pares(resumo)
    meta = {"gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"), "modelo_juiz": juiz.modelo,
            "n_casos": len(casos), "repeticoes": a.repeticoes, "mock": a.mock, "versoes": list(resumo)}
    salvar(pasta, casos, respostas, avaliacoes, resumo, pares, meta)
    print("\n" + tabela_markdown(resumo, pares))
    print(f"Arquivos salvos em: {pasta}/")


if __name__ == "__main__":
    main()
