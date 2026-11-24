"""As cinco consultas previstas na modelagem, sem agregações ou $lookup."""
import re
from regras import texto, genero_normalizado, hoje, dia, RegraErro
from emprestimos import detalhes


def por_titulo(db, titulo):
    termo = re.escape(texto(titulo, 'Título'))
    return list(db.livros.find({'titulo': {'$regex': termo, '$options': 'i'}}).sort('titulo', 1))


def disponiveis_por_genero(db, genero):
    filtro = {'genero': genero_normalizado(genero), 'disponivel': True}
    return list(db.livros.find(filtro).sort('titulo', 1))


def por_matricula(db, matricula):
    return db.leitores.find_one({'matricula': texto(matricula, 'Matrícula')})


def atrasados(db, referencia=None):
    referencia = hoje() if referencia is None else dia(referencia)
    filtro = {'data_prevista': {'$lt': referencia}, 'data_devolucao': None}
    resultado = []
    for doc in db.emprestimos.find(filtro).sort('data_prevista', 1):
        item = detalhes(db, doc, referencia)
        item['dias_atraso'] = (referencia - dia(doc['data_prevista'])).days
        resultado.append(item)
    return resultado


def historico(db, matricula, referencia=None):
    leitor = por_matricula(db, matricula)
    if leitor is None:
        raise RegraErro('Leitor não encontrado.')
    docs = db.emprestimos.find({'leitor_id': leitor['_id']}).sort('data_emprestimo', -1)
    return leitor, [detalhes(db, doc, referencia) for doc in docs]
