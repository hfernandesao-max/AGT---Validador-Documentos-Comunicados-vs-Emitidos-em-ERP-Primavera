"""Linha de comandos: lista os documentos comunicados à AGT e exporta-os com o detalhe.

Exemplos:
    python -m agt_consulta listar --de 2026-09-01 --ate 2026-09-30
    python -m agt_consulta detalhe "FT A/123"
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from .cliente import ClienteAGT, ErroAGT, extrair_documentos, numero_do_documento
from .config import Config, carregar_env


def achatar(obj, prefixo=""):
    """Transforma JSON aninhado em colunas (ex.: documentTotals.grossTotal)."""
    linha = {}
    if isinstance(obj, dict):
        for chave, valor in obj.items():
            linha.update(achatar(valor, f"{prefixo}{chave}."))
    elif isinstance(obj, list):
        linha[prefixo.rstrip(".")] = json.dumps(obj, ensure_ascii=False)
    else:
        linha[prefixo.rstrip(".")] = obj
    return linha


def escrever_csv(caminho, linhas):
    colunas = []
    for linha in linhas:
        for chave in linha:
            if chave not in colunas:
                colunas.append(chave)
    # utf-8-sig e ';' para abrir directamente no Excel em português
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)


def cmd_listar(cliente, args):
    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)

    resposta = cliente.listar_facturas(args.de, args.ate)
    documentos = extrair_documentos(resposta)
    print(f"{len(documentos)} documentos comunicados entre {args.de} e {args.ate}")

    detalhes, erros = [], []
    if not args.sem_detalhe:
        for i, doc in enumerate(documentos, 1):
            numero = numero_do_documento(doc)
            if not numero:
                continue
            print(f"[{i}/{len(documentos)}] {numero}")
            try:
                detalhes.append(cliente.consultar_factura(numero))
            except ErroAGT as e:
                erros.append({"documentNo": numero, "status": e.status, "erro": e.corpo})

    base = f"agt_{args.de}_{args.ate}"
    (pasta / f"{base}.json").write_text(
        json.dumps(
            {"lista": resposta, "detalhes": detalhes, "erros": erros},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    escrever_csv(pasta / f"{base}_lista.csv", [achatar(d) for d in documentos])
    if detalhes:
        escrever_csv(pasta / f"{base}_detalhe.csv", [achatar(d) for d in detalhes])
    print(f"Resultados em {pasta.resolve()}")
    if erros:
        print(f"{len(erros)} documentos falharam na consulta de detalhe (ver JSON)")


def cmd_detalhe(cliente, args):
    print(json.dumps(cliente.consultar_factura(args.documento), ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agt_consulta", description=__doc__.splitlines()[0])
    parser.add_argument("--env", default=".env", help="ficheiro com as credenciais (default: .env)")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_listar = sub.add_parser("listar", help="lista documentos de um período e o detalhe de cada um")
    p_listar.add_argument("--de", required=True, help="data inicial YYYY-MM-DD")
    p_listar.add_argument("--ate", required=True, help="data final YYYY-MM-DD")
    p_listar.add_argument("--saida", default="saida", help="pasta de resultados")
    p_listar.add_argument("--sem-detalhe", action="store_true", help="não chama consultarFactura")
    p_listar.set_defaults(func=cmd_listar)

    p_detalhe = sub.add_parser("detalhe", help="detalhe de um documento")
    p_detalhe.add_argument("documento", help="número do documento, ex.: 'FT A/123'")
    p_detalhe.set_defaults(func=cmd_detalhe)

    args = parser.parse_args(argv)
    carregar_env(args.env)
    cliente = ClienteAGT(Config.do_ambiente())
    try:
        args.func(cliente, args)
    except ErroAGT as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
