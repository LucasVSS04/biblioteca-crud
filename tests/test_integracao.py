"""Testes reais em banco temporário; nunca modificam biblioteca_db."""
import unittest
from datetime import timedelta
from uuid import uuid4
from tempfile import TemporaryDirectory
from pathlib import Path
from regras import hoje, RegraErro

try:
    from database import conectar, preparar, reconciliar
    import livros
    import leitores
    import emprestimos
    import buscas
    import dados
    from pymongo.errors import PyMongoError, DuplicateKeyError
    DRIVER = True
except ModuleNotFoundError as erro:
    if erro.name not in ('pymongo', 'bson'):
        raise
    DRIVER = False


@unittest.skipUnless(DRIVER, 'PyMongo não instalado')
class TestMongoDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.cliente = conectar()
        except PyMongoError as erro:
            raise unittest.SkipTest(f'MongoDB indisponível: {type(erro).__name__}')

    @classmethod
    def tearDownClass(cls):
        cls.cliente.close()

    def setUp(self):
        self.db = self.cliente['biblioteca_teste_' + uuid4().hex]
        self.addCleanup(self.cliente.drop_database, self.db.name)
        preparar(self.db)
        self.livro = livros.cadastrar(self.db, 'O Hobbit', 'Tolkien', 'Fantasia', 1937)
        self.leitor = leitores.cadastrar(self.db, 'Ana', 'ana@example.com', '0000', '001')
        self.inicio = hoje() - timedelta(days=10)

    def test_crud_livros_leitores(self):
        self.assertEqual(set(self.db.list_collection_names()), {'livros', 'leitores', 'emprestimos'})
        livros.atualizar(self.db, self.livro, 'Hobbit', 'Tolkien', 'Fantasia', 1937)
        leitores.atualizar(self.db, self.leitor, 'Ana Silva', 'ana@example.com', '1234', '001')
        self.assertEqual(livros.listar(self.db)[0]['titulo'], 'Hobbit')
        self.assertEqual(leitores.listar(self.db)[0]['nome'], 'Ana Silva')
        with self.assertRaises(RegraErro):
            leitores.cadastrar(self.db, 'Outra', 'outra@example.com', '0000', '001')
        livros.remover(self.db, self.livro)
        leitores.remover(self.db, self.leitor)
        self.assertEqual(livros.listar(self.db), [])
        self.assertEqual(leitores.listar(self.db), [])

    def test_emprestimos_e_integridade(self):
        e = emprestimos.cadastrar(self.db, self.livro, self.leitor, self.inicio, hoje())
        self.assertFalse(self.db.livros.find_one({'_id': self.livro})['disponivel'])
        with self.assertRaises(RegraErro):
            emprestimos.cadastrar(self.db, self.livro, self.leitor, self.inicio, hoje())
        duplicado = self.db.emprestimos.find_one({'_id': e}); duplicado.pop('_id')
        with self.assertRaises(DuplicateKeyError):
            self.db.emprestimos.insert_one(duplicado)
        with self.assertRaises(RegraErro):
            livros.remover(self.db, self.livro)
        with self.assertRaises(RegraErro):
            leitores.remover(self.db, self.leitor)
        self.assertEqual(emprestimos.listar(self.db)[0]['situacao'], 'Ativo')
        self.db.livros.update_one({'_id': self.livro}, {'$set': {'disponivel': True}})
        reconciliar(self.db)
        self.assertFalse(self.db.livros.find_one({'_id': self.livro})['disponivel'])
        emprestimos.devolver(self.db, e)
        self.assertTrue(self.db.livros.find_one({'_id': self.livro})['disponivel'])
        novo = emprestimos.cadastrar(self.db, self.livro, self.leitor, hoje(), hoje())
        emprestimos.remover(self.db, e)
        self.assertFalse(self.db.livros.find_one({'_id': self.livro})['disponivel'])
        outro = livros.cadastrar(self.db, 'Outro', 'Autor', 'Romance', 2000)
        emprestimos.atualizar(self.db, novo, outro, self.leitor, hoje(), hoje(), None)
        self.assertTrue(self.db.livros.find_one({'_id': self.livro})['disponivel'])
        self.assertFalse(self.db.livros.find_one({'_id': outro})['disponivel'])
        emprestimos.remover(self.db, novo)
        self.assertTrue(self.db.livros.find_one({'_id': outro})['disponivel'])

    def test_cinco_buscas(self):
        outro = livros.cadastrar(self.db, 'A [aventura]', 'Autor', 'Fantasia', 2000)
        emprestimos.cadastrar(self.db, self.livro, self.leitor, self.inicio, hoje()-timedelta(days=1))
        emprestimos.cadastrar(self.db, outro, self.leitor, self.inicio, hoje())
        self.assertEqual(buscas.por_titulo(self.db, 'HOB')[0]['_id'], self.livro)
        self.assertEqual(buscas.por_titulo(self.db, '[')[0]['_id'], outro)
        self.assertEqual(buscas.disponiveis_por_genero(self.db, 'FANTASIA'), [])
        livre = livros.cadastrar(self.db, 'Livre', 'Autor', 'Fantasia', 2000)
        self.assertEqual(buscas.disponiveis_por_genero(self.db, 'fantasia')[0]['_id'], livre)
        self.assertEqual(buscas.por_matricula(self.db, '001')['_id'], self.leitor)
        self.assertIsNone(buscas.por_matricula(self.db, 'inexistente'))
        self.assertEqual(len(buscas.atrasados(self.db)), 1)
        self.assertEqual(buscas.atrasados(self.db)[0]['dias_atraso'], 1)
        leitor, historico = buscas.historico(self.db, '001')
        self.assertEqual(leitor['_id'], self.leitor)
        self.assertEqual({x['situacao'] for x in historico}, {'Ativo', 'Atrasado'})

    def test_importar_exportar(self):
        self.db.livros.delete_many({}); self.db.leitores.delete_many({})
        self.assertEqual(dados.importar(self.db), {'livros': 8, 'leitores': 3, 'emprestimos': 5})
        with self.assertRaises(RegraErro):
            dados.importar(self.db)
        self.assertEqual(len(buscas.atrasados(self.db)), 2)
        with TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            dados.exportar(self.db, pasta)
            self.db.emprestimos.delete_many({}); self.db.livros.delete_many({}); self.db.leitores.delete_many({})
            self.assertEqual(dados.importar(self.db, pasta, ajustar_datas=False)['emprestimos'], 5)


if __name__ == '__main__':
    unittest.main()
