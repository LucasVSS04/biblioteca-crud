"""CRUD da coleção leitores."""
from pymongo.errors import DuplicateKeyError
from database import obter
from regras import RegraErro, texto, email_valido


def _campos(nome, email, telefone, matricula):
    return {'nome': texto(nome, 'Nome'), 'email': email_valido(email),
            'telefone': texto(telefone, 'Telefone'), 'matricula': texto(matricula, 'Matrícula')}


def cadastrar(db, nome, email, telefone, matricula):
    try:
        return db.leitores.insert_one(_campos(nome, email, telefone, matricula)).inserted_id
    except DuplicateKeyError:
        raise RegraErro('Já existe um leitor com essa matrícula.') from None


def listar(db):
    return list(db.leitores.find().sort('nome', 1))


def atualizar(db, identificador, nome, email, telefone, matricula):
    leitor = obter(db.leitores, identificador, 'Leitor')
    try:
        db.leitores.update_one({'_id': leitor['_id']}, {'$set': _campos(nome, email, telefone, matricula)})
    except DuplicateKeyError:
        raise RegraErro('Já existe um leitor com essa matrícula.') from None


def remover(db, identificador):
    leitor = obter(db.leitores, identificador, 'Leitor')
    if db.emprestimos.find_one({'leitor_id': leitor['_id']}):
        raise RegraErro('Leitor possui empréstimos vinculados e não pode ser removido.')
    db.leitores.delete_one({'_id': leitor['_id']})
