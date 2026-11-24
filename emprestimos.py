"""CRUD de empréstimos e devoluções. Operação local, um usuário por vez."""
from pymongo.errors import DuplicateKeyError
from database import obter, depois_da_gravacao
from regras import RegraErro, datas_emprestimo, hoje, situacao


def _campos(db, livro_id, leitor_id, inicio, prazo, devolucao=None, ignorar=None):
    livro = obter(db.livros, livro_id, 'Livro')
    leitor = obter(db.leitores, leitor_id, 'Leitor')
    inicio, prazo, devolucao = datas_emprestimo(inicio, prazo, devolucao)
    if devolucao is None:
        filtro = {'livro_id': livro['_id'], 'data_devolucao': None}
        if ignorar is not None:
            filtro['_id'] = {'$ne': ignorar}
        if db.emprestimos.find_one(filtro):
            raise RegraErro('O livro já possui um empréstimo pendente.')
    return {'livro_id': livro['_id'], 'leitor_id': leitor['_id'], 'data_emprestimo': inicio,
            'data_prevista': prazo, 'data_devolucao': devolucao}


def cadastrar(db, livro_id, leitor_id, inicio, prazo):
    doc = _campos(db, livro_id, leitor_id, inicio, prazo)
    livro = obter(db.livros, doc['livro_id'], 'Livro')
    if not livro['disponivel']:
        raise RegraErro('Livro indisponível. Se necessário, reinicie o sistema para reconciliar os dados.')
    try:
        identificador = db.emprestimos.insert_one(doc).inserted_id
    except DuplicateKeyError:
        raise RegraErro('O livro já possui um empréstimo pendente.') from None
    depois_da_gravacao(db, doc['livro_id'])
    return identificador


def detalhes(db, emprestimo, referencia=None):
    livro = db.livros.find_one({'_id': emprestimo['livro_id']})
    leitor = db.leitores.find_one({'_id': emprestimo['leitor_id']})
    return {**emprestimo, 'livro': livro['titulo'] if livro else '[livro não encontrado]',
            'leitor': leitor['nome'] if leitor else '[leitor não encontrado]',
            'matricula': leitor['matricula'] if leitor else '—',
            'situacao': situacao(emprestimo, referencia)}


def listar(db):
    return [detalhes(db, doc) for doc in db.emprestimos.find().sort('data_emprestimo', -1)]


def atualizar(db, identificador, livro_id, leitor_id, inicio, prazo, devolucao):
    antigo = obter(db.emprestimos, identificador, 'Empréstimo')
    doc = _campos(db, livro_id, leitor_id, inicio, prazo, devolucao, ignorar=antigo['_id'])
    try:
        db.emprestimos.update_one({'_id': antigo['_id']}, {'$set': doc})
    except DuplicateKeyError:
        raise RegraErro('O livro já possui um empréstimo pendente.') from None
    depois_da_gravacao(db, antigo['livro_id'], doc['livro_id'])


def devolver(db, identificador, data=None):
    doc = obter(db.emprestimos, identificador, 'Empréstimo')
    if doc['data_devolucao'] is not None:
        raise RegraErro('Este empréstimo já foi devolvido.')
    atualizar(db, doc['_id'], doc['livro_id'], doc['leitor_id'], doc['data_emprestimo'],
              doc['data_prevista'], hoje() if data is None else data)


def remover(db, identificador):
    doc = obter(db.emprestimos, identificador, 'Empréstimo')
    db.emprestimos.delete_one({'_id': doc['_id']})
    depois_da_gravacao(db, doc['livro_id'])
