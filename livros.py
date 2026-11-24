"""CRUD da coleção livros."""
from database import obter
from regras import RegraErro, texto, genero_normalizado, ano_valido


def _campos(titulo, autor, genero, ano_publicacao):
    return {'titulo': texto(titulo, 'Título'), 'autor': texto(autor, 'Autor'),
            'genero': genero_normalizado(genero), 'ano_publicacao': ano_valido(ano_publicacao)}


def cadastrar(db, titulo, autor, genero, ano_publicacao):
    doc = _campos(titulo, autor, genero, ano_publicacao)
    doc['disponivel'] = True
    return db.livros.insert_one(doc).inserted_id


def listar(db):
    return list(db.livros.find().sort('titulo', 1))


def atualizar(db, identificador, titulo, autor, genero, ano_publicacao):
    livro = obter(db.livros, identificador, 'Livro')
    db.livros.update_one({'_id': livro['_id']}, {'$set': _campos(titulo, autor, genero, ano_publicacao)})


def remover(db, identificador):
    livro = obter(db.livros, identificador, 'Livro')
    if db.emprestimos.find_one({'livro_id': livro['_id']}):
        raise RegraErro('Livro possui empréstimos vinculados e não pode ser removido.')
    db.livros.delete_one({'_id': livro['_id']})
