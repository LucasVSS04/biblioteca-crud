"""Validações independentes do banco e convenção de datas civis."""
from datetime import date, datetime, timezone
import re


class RegraErro(ValueError):
    """Violação de regra de negócio ou entrada inválida."""


def texto(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise RegraErro(f'{campo} é obrigatório.')
    return valor.strip()


def genero_normalizado(valor):
    return texto(valor, 'Gênero').casefold()


def ano_valido(valor):
    try:
        ano = int(valor)
    except (ValueError, TypeError):
        raise RegraErro('Informe um ano inteiro.') from None
    if isinstance(valor, (float, bool)) or not 1 <= ano <= date.today().year:
        raise RegraErro(f'O ano deve estar entre 1 e {date.today().year}.')
    return ano


def email_valido(valor):
    valor = texto(valor, 'E-mail')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', valor):
        raise RegraErro('Informe um e-mail válido.')
    return valor


def dia(valor):
    """Converte data civil para meia-noite UTC (BSON Date)."""
    if isinstance(valor, str):
        try:
            valor = datetime.strptime(valor.strip(), '%d/%m/%Y').date()
        except ValueError:
            raise RegraErro('Data inválida. Utilize DD/MM/AAAA.') from None
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone(timezone.utc)
        valor = valor.date()
    if not isinstance(valor, date):
        raise RegraErro('Data inválida.')
    return datetime(valor.year, valor.month, valor.day, tzinfo=timezone.utc)


def hoje():
    return dia(date.today())


def datas_emprestimo(inicio, prazo, devolucao=None):
    inicio, prazo = dia(inicio), dia(prazo)
    devolucao = dia(devolucao) if devolucao is not None else None
    if inicio > hoje():
        raise RegraErro('O empréstimo não pode iniciar no futuro.')
    if prazo < inicio:
        raise RegraErro('O prazo não pode ser anterior ao empréstimo.')
    if devolucao is not None and not inicio <= devolucao <= hoje():
        raise RegraErro('A devolução deve ocorrer entre o empréstimo e hoje.')
    return inicio, prazo, devolucao


def situacao(emprestimo, referencia=None):
    referencia = hoje() if referencia is None else dia(referencia)
    if emprestimo['data_devolucao'] is not None:
        return 'Devolvido'
    return 'Atrasado' if dia(emprestimo['data_prevista']) < referencia else 'Ativo'


def formatar_data(valor):
    return dia(valor).strftime('%d/%m/%Y') if valor is not None else '—'
