"""Conexão, índices e manutenção do campo de disponibilidade."""
import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
from bson import ObjectId
from bson.errors import InvalidId
from regras import RegraErro

URI = os.environ.get('MONGODB_URI', 'mongodb://127.0.0.1:27017/')
NOME_BANCO = 'biblioteca_db'
COLECOES = ('livros', 'leitores', 'emprestimos')


def conectar():
    cliente = MongoClient(URI, serverSelectionTimeoutMS=5000, tz_aware=True)
    try:
        cliente.admin.command('ping')
    except PyMongoError:
        cliente.close()
        raise
    return cliente


def preparar(db):
    existentes = db.list_collection_names()
    for nome in COLECOES:
        if nome not in existentes:
            db.create_collection(nome)
    db.leitores.create_index('matricula', unique=True)
    db.livros.create_index([('genero', ASCENDING), ('disponivel', ASCENDING), ('titulo', ASCENDING)])
    db.emprestimos.create_index([('data_devolucao', ASCENDING), ('data_prevista', ASCENDING)])
    db.emprestimos.create_index([('leitor_id', ASCENDING), ('data_emprestimo', DESCENDING)])
    # Um exemplar não pode ter dois empréstimos ainda não devolvidos.
    db.emprestimos.create_index('livro_id', name='um_emprestimo_pendente_por_livro',
                                unique=True, partialFilterExpression={'data_devolucao': None})


def object_id(valor):
    if isinstance(valor, ObjectId):
        return valor
    if not isinstance(valor, str):
        raise RegraErro('Identificador inválido. Copie o ID apresentado na listagem.')
    try:
        return ObjectId(valor.strip())
    except (InvalidId, TypeError):
        raise RegraErro('Identificador inválido. Copie o ID apresentado na listagem.') from None


def obter(colecao, identificador, nome):
    documento = colecao.find_one({'_id': object_id(identificador)})
    if documento is None:
        raise RegraErro(f'{nome} não encontrado(a).')
    return documento


def sincronizar_disponibilidade(db, *livros_ids):
    """Empréstimos pendentes são a fonte de verdade da disponibilidade."""
    for livro_id in set(livros_ids):
        pendente = db.emprestimos.find_one({'livro_id': livro_id, 'data_devolucao': None}, {'_id': 1})
        db.livros.update_one({'_id': livro_id}, {'$set': {'disponivel': pendente is None}})


def reconciliar(db):
    """Repara diferenças após interrupções entre operações em documentos."""
    pendentes = set(db.emprestimos.distinct('livro_id', {'data_devolucao': None}))
    for livro in db.livros.find({}, {'_id': 1, 'disponivel': 1}):
        esperado = livro['_id'] not in pendentes
        if livro.get('disponivel') != esperado:
            db.livros.update_one({'_id': livro['_id']}, {'$set': {'disponivel': esperado}})


def depois_da_gravacao(db, *livros_ids):
    try:
        sincronizar_disponibilidade(db, *livros_ids)
    except PyMongoError as erro:
        raise RegraErro('O empréstimo foi gravado, mas a disponibilidade não foi sincronizada. '
                        'Não repita a operação; reinicie a aplicação para reconciliar os dados.') from erro
