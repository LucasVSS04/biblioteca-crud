"""Interface de linha de comando do BibliotecaCRUD."""
from pymongo.errors import PyMongoError
from database import conectar, preparar, reconciliar, obter, NOME_BANCO
from regras import RegraErro, formatar_data, hoje
import livros
import leitores
import emprestimos
import buscas


def ler(rotulo, atual=None):
    if atual is None:
        return input(f'{rotulo}: ').strip()
    resposta = input(f'{rotulo} [{atual}]: ').strip()
    return resposta or atual


def exibir(registros, tipo):
    if not registros:
        print('Nenhum registro encontrado.')
        return
    for doc in registros:
        print('-' * 55)
        print(f"ID: {doc['_id']}")
        if tipo == 'livros':
            print(f"Título: {doc['titulo']} | Autor: {doc['autor']}")
            print(f"Gênero: {doc['genero']} | Ano: {doc['ano_publicacao']}")
            print('Disponível:', 'Sim' if doc['disponivel'] else 'Não')
        elif tipo == 'leitores':
            print(f"Nome: {doc['nome']} | Matrícula: {doc['matricula']}")
            print(f"E-mail: {doc['email']} | Telefone: {doc['telefone']}")
        else:
            print(f"Livro: {doc['livro']} | Leitor: {doc['leitor']} ({doc['matricula']})")
            print(f"Empréstimo: {formatar_data(doc['data_emprestimo'])} | Prazo: {formatar_data(doc['data_prevista'])}")
            print(f"Devolução: {formatar_data(doc['data_devolucao'])} | Situação: {doc['situacao']}")
            if 'dias_atraso' in doc:
                print(f"Dias de atraso: {doc['dias_atraso']}")
    print(f'\nTotal: {len(registros)} registro(s).')


def escolher_id(db, tipo):
    mod = {'livros': livros, 'leitores': leitores, 'emprestimos': emprestimos}[tipo]
    registros = mod.listar(db)
    exibir(registros, tipo)
    if not registros:
        raise RegraErro('Não há registros para selecionar.')
    return ler('ID do registro (copie da listagem)')


def confirmar():
    return ler('Confirma a remoção? (s/N)').casefold() == 's'


def campos_livro(doc=None):
    doc = doc or {}
    return [ler(rotulo, doc.get(campo)) for campo, rotulo in (
        ('titulo', 'Título'), ('autor', 'Autor'), ('genero', 'Gênero'), ('ano_publicacao', 'Ano de publicação'))]


def campos_leitor(doc=None):
    doc = doc or {}
    return [ler(rotulo, doc.get(campo)) for campo, rotulo in (
        ('nome', 'Nome'), ('email', 'E-mail'), ('telefone', 'Telefone'), ('matricula', 'Matrícula'))]


def cadastrar_basico(db, modulo, campos):
    identificador = modulo.cadastrar(db, *campos())
    print(f'Registro cadastrado. ID: {identificador}')


def atualizar_basico(db, tipo, modulo, campos):
    identificador = escolher_id(db, tipo)
    doc = obter(db[tipo], identificador, 'Registro')
    modulo.atualizar(db, identificador, *campos(doc))
    print('Registro atualizado.')


def remover_registro(db, tipo, modulo):
    identificador = escolher_id(db, tipo)
    if confirmar():
        modulo.remover(db, identificador)
        print('Registro removido.')
    else:
        print('Operação cancelada.')


def cadastrar_emprestimo(db):
    disponiveis = [doc for doc in livros.listar(db) if doc['disponivel']]
    exibir(disponiveis, 'livros')
    if not disponiveis:
        raise RegraErro('Não há livros disponíveis.')
    livro_id = ler('ID do livro disponível')
    leitor_id = escolher_id(db, 'leitores')
    inicio = ler('Data do empréstimo (DD/MM/AAAA)', formatar_data(hoje()))
    prazo = ler('Prazo de devolução (DD/MM/AAAA)')
    identificador = emprestimos.cadastrar(db, livro_id, leitor_id, inicio, prazo)
    print(f'Empréstimo registrado. ID: {identificador}')


def atualizar_emprestimo(db):
    identificador = escolher_id(db, 'emprestimos')
    doc = obter(db.emprestimos, identificador, 'Empréstimo')
    exibir(livros.listar(db), 'livros')
    livro_id = ler('ID do livro', str(doc['livro_id']))
    exibir(leitores.listar(db), 'leitores')
    leitor_id = ler('ID do leitor', str(doc['leitor_id']))
    inicio = ler('Data do empréstimo (DD/MM/AAAA)', formatar_data(doc['data_emprestimo']))
    prazo = ler('Prazo (DD/MM/AAAA)', formatar_data(doc['data_prevista']))
    atual = formatar_data(doc['data_devolucao']) if doc['data_devolucao'] else '-'
    devolucao = ler('Data de devolução (DD/MM/AAAA; - para pendente)', atual)
    emprestimos.atualizar(db, identificador, livro_id, leitor_id, inicio, prazo,
                         None if devolucao == '-' else devolucao)
    print('Empréstimo atualizado.')


def devolver(db):
    identificador = escolher_id(db, 'emprestimos')
    data = ler('Data da devolução (DD/MM/AAAA)', formatar_data(hoje()))
    emprestimos.devolver(db, identificador, data)
    print('Devolução registrada.')


def busca_matricula(db):
    leitor = buscas.por_matricula(db, ler('Matrícula'))
    exibir([leitor] if leitor else [], 'leitores')


def busca_historico(db):
    leitor, historico = buscas.historico(db, ler('Matrícula'))
    print(f"Histórico de {leitor['nome']} ({leitor['matricula']})")
    exibir(historico, 'emprestimos')


def menu(titulo, opcoes, saida='Voltar'):
    while True:
        print('\n' + '=' * 45)
        print(titulo)
        print('=' * 45)
        for numero, (rotulo, _) in opcoes.items():
            print(f'{numero} - {rotulo}')
        print(f'0 - {saida}')
        opcao = ler('Selecione uma opção')
        if opcao == '0':
            return
        if opcao not in opcoes:
            print('Opção inválida.')
            continue
        try:
            opcoes[opcao][1]()
        except RegraErro as erro:
            print(f'Atenção: {erro}')
        except PyMongoError as erro:
            print(f'Erro de banco de dados ({type(erro).__name__}). Verifique o MongoDB. '
                  'Se houve uma gravação, confira os registros antes de repetir; reinicie para reconciliar a disponibilidade.')


def menu_basico(db, tipo, modulo, campos, singular):
    menu(f'GERENCIAR {tipo.upper()}', {
        '1': (f'Cadastrar {singular}', lambda: cadastrar_basico(db, modulo, campos)),
        '2': (f'Listar {tipo}', lambda: exibir(modulo.listar(db), tipo)),
        '3': (f'Atualizar {singular}', lambda: atualizar_basico(db, tipo, modulo, campos)),
        '4': (f'Remover {singular}', lambda: remover_registro(db, tipo, modulo)),
    })


def menu_emprestimos(db):
    menu('GERENCIAR EMPRÉSTIMOS', {
        '1': ('Registrar empréstimo', lambda: cadastrar_emprestimo(db)),
        '2': ('Listar empréstimos', lambda: exibir(emprestimos.listar(db), 'emprestimos')),
        '3': ('Atualizar empréstimo', lambda: atualizar_emprestimo(db)),
        '4': ('Remover empréstimo', lambda: remover_registro(db, 'emprestimos', emprestimos)),
        '5': ('Registrar devolução', lambda: devolver(db)),
    })


def menu_buscas(db):
    menu('REALIZAR BUSCAS', {
        '1': ('Pesquisar livros pelo título', lambda: exibir(buscas.por_titulo(db, ler('Título ou trecho')), 'livros')),
        '2': ('Buscar livros disponíveis por gênero', lambda: exibir(buscas.disponiveis_por_genero(db, ler('Gênero')), 'livros')),
        '3': ('Localizar leitor pela matrícula', lambda: busca_matricula(db)),
        '4': ('Listar empréstimos atrasados', lambda: exibir(buscas.atrasados(db), 'emprestimos')),
        '5': ('Consultar histórico de um leitor', lambda: busca_historico(db)),
    })


def main():
    cliente = None
    try:
        cliente = conectar()
        db = cliente[NOME_BANCO]
        preparar(db)
        reconciliar(db)
        menu('SISTEMA DE BIBLIOTECA', {
            '1': ('Gerenciar livros', lambda: menu_basico(db, 'livros', livros, campos_livro, 'livro')),
            '2': ('Gerenciar leitores', lambda: menu_basico(db, 'leitores', leitores, campos_leitor, 'leitor')),
            '3': ('Gerenciar empréstimos', lambda: menu_emprestimos(db)),
            '4': ('Realizar buscas', lambda: menu_buscas(db)),
        }, 'Sair do sistema')
        print('Sistema encerrado.')
        return 0
    except (EOFError, KeyboardInterrupt):
        print('\nSistema encerrado pelo usuário.')
        return 0
    except PyMongoError as erro:
        print(f'Não foi possível inicializar o banco ({type(erro).__name__}). '
              'Verifique o Docker Compose e os índices existentes. Consulte o README.')
        return 1
    finally:
        if cliente is not None:
            cliente.close()


if __name__ == '__main__':
    raise SystemExit(main())
