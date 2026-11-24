import json
import unittest
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from regras import (RegraErro, texto, genero_normalizado, ano_valido, email_valido,
                    dia, hoje, datas_emprestimo, situacao, formatar_data)


class TestRegras(unittest.TestCase):
    def test_texto(self):
        self.assertEqual(texto(' livro ', 'Título'), 'livro')
        with self.assertRaises(RegraErro):
            texto('  ', 'Título')

    def test_genero(self):
        self.assertEqual(genero_normalizado(' FANTASIA '), 'fantasia')

    def test_ano(self):
        self.assertEqual(ano_valido('1999'), 1999)
        for valor in ('abc', '0', str(date.today().year + 1), 1.5, True):
            with self.subTest(valor=valor), self.assertRaises(RegraErro):
                ano_valido(valor)

    def test_email(self):
        self.assertEqual(email_valido(' a@example.com '), 'a@example.com')
        with self.assertRaises(RegraErro):
            email_valido('sem-arroba')

    def test_datas(self):
        self.assertEqual(dia('24/11/2026'), datetime(2026, 11, 24, tzinfo=timezone.utc))
        self.assertEqual(formatar_data(dia('01/02/2025')), '01/02/2025')
        self.assertEqual(formatar_data(None), '—')
        with self.assertRaises(RegraErro):
            dia('31/02/2026')

    def test_datas_emprestimo(self):
        inicio = hoje() - timedelta(days=5)
        self.assertEqual(datas_emprestimo(inicio, hoje(), hoje()), (inicio, hoje(), hoje()))
        for valores in [(hoje()+timedelta(days=1), hoje(), None),
                        (hoje(), inicio, None), (inicio, hoje(), inicio-timedelta(days=1)),
                        (inicio, hoje(), hoje()+timedelta(days=1))]:
            with self.subTest(valores=valores), self.assertRaises(RegraErro):
                datas_emprestimo(*valores)

    def test_situacao(self):
        ref = dia('24/11/2026')
        doc = {'data_prevista': ref, 'data_devolucao': None}
        self.assertEqual(situacao(doc, ref), 'Ativo')
        doc['data_prevista'] -= timedelta(days=1)
        self.assertEqual(situacao(doc, ref), 'Atrasado')
        doc['data_devolucao'] = ref
        self.assertEqual(situacao(doc, ref), 'Devolvido')

    def test_dados_exemplo(self):
        pasta = Path(__file__).resolve().parents[1] / 'dados'
        livros, leitores, emprestimos = [json.loads((pasta / f'{nome}.json').read_text(encoding='utf-8'))
                                        for nome in ('livros', 'leitores', 'emprestimos')]
        ids_livros = {x['_id']['$oid'] for x in livros}
        ids_leitores = {x['_id']['$oid'] for x in leitores}
        self.assertEqual(len(ids_livros), len(livros))
        self.assertEqual(len(ids_leitores), len(leitores))
        self.assertEqual(len({x['matricula'] for x in leitores}), len(leitores))
        ativos = []
        for doc in emprestimos:
            self.assertIn(doc['livro_id']['$oid'], ids_livros)
            self.assertIn(doc['leitor_id']['$oid'], ids_leitores)
            self.assertLessEqual(doc['data_emprestimo']['$date'], doc['data_prevista']['$date'])
            if doc['data_devolucao'] is None:
                ativos.append(doc['livro_id']['$oid'])
        self.assertEqual(len(ativos), len(set(ativos)))
        for livro in livros:
            self.assertEqual(livro['disponivel'], livro['_id']['$oid'] not in ativos)


if __name__ == '__main__':
    unittest.main()
