"""Importa a demonstração ou exporta dados em JSON estendido BSON.

Uso: python dados.py importar [--datas-originais]
     python dados.py exportar --pasta caminho
"""
import argparse
from datetime import date
from pathlib import Path
from bson import json_util
from pymongo.errors import PyMongoError
from database import conectar, preparar, reconciliar, NOME_BANCO, COLECOES
from regras import RegraErro, dia, hoje

PASTA = Path(__file__).resolve().parent / 'dados'
DATA_BASE = date(2026, 11, 24)


def importar(db, pasta=PASTA, ajustar_datas=True):
    if any(db[nome].count_documents({}) for nome in COLECOES):
        raise RegraErro('A importação exige as três coleções vazias. Nenhum dado foi alterado.')
    documentos = {nome: json_util.loads((pasta / f'{nome}.json').read_text(encoding='utf-8'))
                  for nome in COLECOES}
    if ajustar_datas:
        deslocamento = hoje() - dia(DATA_BASE)
        for doc in documentos['emprestimos']:
            for campo in ('data_emprestimo', 'data_prevista', 'data_devolucao'):
                if doc[campo] is not None:
                    doc[campo] = dia(doc[campo]) + deslocamento
    ids_livros = {doc['_id'] for doc in documentos['livros']}
    ids_leitores = {doc['_id'] for doc in documentos['leitores']}
    for doc in documentos['emprestimos']:
        if doc['livro_id'] not in ids_livros or doc['leitor_id'] not in ids_leitores:
            raise RegraErro('Dados de demonstração contêm referências inválidas.')
    # Em caso de falha de inserção, remove apenas os IDs do lote em banco inicialmente vazio.
    try:
        for nome in COLECOES:
            if documentos[nome]:
                db[nome].insert_many(documentos[nome])
        reconciliar(db)
    except PyMongoError:
        try:
            for nome in reversed(COLECOES):
                db[nome].delete_many({'_id': {'$in': [doc['_id'] for doc in documentos[nome]]}})
        except PyMongoError:
            print('A limpeza da importação falhou; confira o banco antes de tentar novamente.')
        raise
    return {nome: len(docs) for nome, docs in documentos.items()}


def exportar(db, pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    for nome in COLECOES:
        arquivo = pasta / f'{nome}.json'
        if arquivo.exists():
            raise RegraErro(f'Arquivo já existe: {arquivo}. Escolha uma pasta diferente.')
    for nome in COLECOES:
        (pasta / f'{nome}.json').write_text(json_util.dumps(list(db[nome].find()),
            json_options=json_util.CANONICAL_JSON_OPTIONS, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='acao', required=True)
    imp = sub.add_parser('importar')
    imp.add_argument('--pasta', type=Path, default=PASTA)
    imp.add_argument('--datas-originais', action='store_true', help='Não desloca as datas da demonstração.')
    exp = sub.add_parser('exportar')
    exp.add_argument('--pasta', type=Path, required=True)
    args = parser.parse_args()
    cliente = None
    try:
        cliente = conectar()
        db = cliente[NOME_BANCO]
        preparar(db)
        if args.acao == 'importar':
            contagens = importar(db, args.pasta, not args.datas_originais and args.pasta.resolve() == PASTA)
            print('Importação concluída:', contagens)
        else:
            exportar(db, args.pasta)
            print(f'Exportação concluída: {args.pasta}')
        return 0
    except (RegraErro, OSError, PyMongoError, ValueError) as erro:
        print(f'Operação não concluída: {erro}')
        return 1
    finally:
        if cliente is not None:
            cliente.close()


if __name__ == '__main__':
    raise SystemExit(main())
