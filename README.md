# BibliotecaCRUD

Sistema acadêmico de gerenciamento de biblioteca, desenvolvido para a disciplina de Banco de Dados. A aplicação utiliza Python, MongoDB e Docker Compose e é operada exclusivamente por menus no terminal. Não há interface gráfica, servidor web ou necessidade de instalar o MongoDB na máquina local.

## 1. Objetivos e tecnologias

- Operações CRUD completas nas três coleções: `livros`, `leitores` e `emprestimos`.
- Controle de empréstimos e devoluções de exemplares.
- Cinco buscas específicas, com filtros, ordenação, comparações de datas e referências entre documentos.
- Ambiente local reproduzível e persistente, com o mínimo de dependências.

| Tecnologia | Finalidade |
| --- | --- |
| Python 3.11 ou superior | Lógica, validações e menus CLI |
| MongoDB 8.0 | Banco de dados documental |
| Docker + Docker Compose v2 | Execução do banco em contêiner e persistência |
| PyMongo 4.x | Única dependência Python declarada diretamente |
| Biblioteca padrão do Python | Datas, expressões regulares, arquivos, terminal e testes |

Dependências transitivas do driver são instaladas pelo `pip`. Não é necessário Flask, Django, ORM ou MongoDB Compass.

## 2. Arquitetura

```text
Usuário -> Terminal -> Python + PyMongo
                             |
                    127.0.0.1:27017
                             |
                    Docker Compose
                    +-- MongoDB 8.0
                        +-- volume mongodb_data
```

- Banco: `biblioteca_db`.
- URI padrão: `mongodb://127.0.0.1:27017/`.
- A aplicação Python é executada no sistema operacional local; somente o MongoDB é conteinerizado.
- O volume nomeado preserva o banco ao remover ou recriar o contêiner, desde que o volume não seja removido.
- A porta é publicada apenas no loopback. Por simplicidade, não há autenticação: outros processos locais podem acessar o banco. Utilize apenas dados fictícios e não exponha a porta à rede nem use essa configuração em produção.

## 3. Estrutura dos arquivos

```text
biblioteca-crud/
├── main.py              # Menus e interface de terminal
├── database.py          # Conexão, coleções, índices e consistência
├── livros.py            # CRUD de livros
├── leitores.py          # CRUD de leitores
├── emprestimos.py       # CRUD, devoluções e referências
├── buscas.py            # Cinco consultas específicas
├── regras.py            # Validação de entradas e datas
├── dados.py             # Importação e exportação JSON estendido
├── compose.yaml         # MongoDB, healthcheck e volume
├── requirements.txt     # PyMongo
├── dados/
│   ├── livros.json
│   ├── leitores.json
│   └── emprestimos.json
├── tests/
│   ├── test_regras.py
│   └── test_integracao.py
├── .gitignore
└── README.md
```

## 4. Criação do ambiente e execução

### 4.1 Pré-requisitos

Instale [Python 3.11+](https://www.python.org/downloads/) e [Docker Desktop](https://docs.docker.com/desktop/) (Windows/macOS) ou [Docker Engine](https://docs.docker.com/engine/install/) com [Docker Compose v2](https://docs.docker.com/compose/install/) (Linux). No Windows, inicie o Docker Desktop; no Linux, certifique-se de que o serviço Docker está ativo e que seu usuário tem permissão para usá-lo.

Verifique no PowerShell (Windows):

```powershell
py -3 --version
docker --version
docker compose version
docker info
```

Ou Bash (Linux/macOS):

```bash
python3 --version
docker --version
docker compose version
docker info
```

### 4.2 Extrair e inicializar o MongoDB

Extraia o ZIP e abra um terminal dentro da pasta `biblioteca-crud`, onde está o `compose.yaml`. Execute:

```bash
docker compose config
docker compose up -d --wait
docker compose ps
docker compose exec mongodb mongosh --quiet --eval "db.adminCommand({ping: 1})"
```

O último comando deve retornar `ok: 1`. O primeiro uso requer internet para baixar a imagem oficial do MongoDB. Se o Compose não reconhecer `--wait`, use `docker compose up -d` e repita o comando de ping quando o banco estiver pronto.

### 4.3 Criar o ambiente virtual e instalar o driver

Windows (PowerShell):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Linux/macOS (Bash):

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

No Linux, se o módulo `venv` estiver indisponível, instale o pacote correspondente à distribuição (por exemplo, `python3-venv` no Debian/Ubuntu). Não é preciso ativar o ambiente virtual: os comandos usam diretamente seu executável. A instalação do PyMongo requer internet.

### 4.4 Carregar os dados de demonstração (opcional, recomendado)

Windows:

```powershell
.\.venv\Scripts\python.exe dados.py importar
```

Linux/macOS:

```bash
./.venv/bin/python dados.py importar
```

A importação cria as três coleções e seus índices, caso não existam, e carrega **8 livros, 3 leitores e 5 empréstimos**. Ela exige que todas as coleções estejam vazias, para não sobrescrever dados. As datas dos exemplos são deslocadas em relação ao dia da execução para manter empréstimos ativos, atrasados e devolvidos. Para preservar as datas originais, acrescente `--datas-originais`.

Caso queira começar com um banco vazio, ignore essa etapa: a aplicação criará as coleções e os índices automaticamente ao iniciar.

### 4.5 Executar a aplicação

Windows:

```powershell
.\.venv\Scripts\python.exe main.py
```

Linux/macOS:

```bash
./.venv/bin/python main.py
```

Menu inicial:

```text
=============================================
SISTEMA DE BIBLIOTECA
=============================================
1 - Gerenciar livros
2 - Gerenciar leitores
3 - Gerenciar empréstimos
4 - Realizar buscas
0 - Sair do sistema
```

Escolha a opção digitando seu número. Para atualizar ou excluir registros, copie o ID de 24 caracteres mostrado na listagem. Nas alterações, pressione Enter para manter o valor atual; na data de devolução de um empréstimo, use `-` para tornar o registro pendente (desde que não exista outro empréstimo pendente do mesmo exemplar). Datas são digitadas no formato `DD/MM/AAAA`.

## 5. Modelagem documental

O banco utiliza exatamente três coleções e dois campos de referência, ambos localizados em `emprestimos`. Cada livro representa um exemplar físico emprestável; autor e gênero são atributos, não coleções.

### `livros`

| Campo | Tipo BSON | Descrição |
| --- | --- | --- |
| `_id` | ObjectId | Identificador único |
| `titulo` | String | Título |
| `autor` | String | Autor |
| `genero` | String | Gênero normalizado em minúsculas |
| `ano_publicacao` | Int32 | Ano de publicação |
| `disponivel` | Boolean | Disponibilidade para empréstimo |

### `leitores`

| Campo | Tipo BSON | Descrição |
| --- | --- | --- |
| `_id` | ObjectId | Identificador único |
| `nome` | String | Nome |
| `email` | String | E-mail |
| `telefone` | String | Telefone |
| `matricula` | String | Matrícula única; preserva zeros à esquerda |

### `emprestimos`

| Campo | Tipo BSON | Descrição |
| --- | --- | --- |
| `_id` | ObjectId | Identificador único |
| `livro_id` | ObjectId | Referência a `livros._id` |
| `leitor_id` | ObjectId | Referência a `leitores._id` |
| `data_emprestimo` | Date | Início do empréstimo |
| `data_prevista` | Date | Prazo de devolução |
| `data_devolucao` | Date ou Null | Devolução efetiva, nula enquanto pendente |

```text
livros   (1) -------- (N) emprestimos (N) -------- (1) leitores
```

MongoDB não impõe chaves estrangeiras tradicionais; a aplicação valida a existência dos documentos relacionados. A situação do empréstimo é calculada dinamicamente, não armazenada em um campo adicional.

### Índices criados automaticamente

| Coleção | Campos | Finalidade |
| --- | --- | --- |
| Todas | `_id` | Identificação única automática |
| `leitores` | `matricula` | Índice único; busca 3 |
| `livros` | `genero`, `disponivel`, `titulo` | Busca 2 |
| `emprestimos` | `data_devolucao`, `data_prevista` | Busca 4 |
| `emprestimos` | `leitor_id`, `data_emprestimo` (desc.) | Busca 5 |
| `emprestimos` | `livro_id` (parcial, único) | Impede dois empréstimos pendentes do mesmo exemplar |

O índice parcial aplica a unicidade apenas aos empréstimos com `data_devolucao: null`. A busca textual por trecho com regex não se beneficia necessariamente de um índice convencional sobre título.

## 6. CRUD e regras de negócio

| Operação | Livros | Leitores | Empréstimos |
| --- | --- | --- | --- |
| Create | Cadastrar | Cadastrar | Registrar |
| Read | Listar | Listar | Listar com nomes e situação |
| Update | Editar | Editar | Editar e registrar devolução |
| Delete | Remover sem vínculos | Remover sem vínculos | Remover registro indevido |

- Campos obrigatórios são validados. O ano deve ser inteiro positivo, até o ano atual, e o e-mail deve ter formato básico válido.
- A matrícula não pode ser duplicada.
- Empréstimos exigem referências existentes, e um livro não pode ter dois empréstimos pendentes.
- A devolução não pode preceder o empréstimo, nem ocorrer no futuro. O prazo pode ser posterior ao dia atual, mas não anterior ao empréstimo.
- Livros e leitores que possuam empréstimos, inclusive devolvidos, não podem ser excluídos.
- O campo `disponivel` é controlado automaticamente pelos empréstimos, não editável diretamente no CRUD de livros.
- Uma devolução ou remoção recalcula a disponibilidade. Se um empréstimo mudar de livro, os dois exemplares são recalculados. Excluir um empréstimo antigo não libera um exemplar que possua outro empréstimo pendente.
- Datas civis são armazenadas à meia-noite UTC em BSON Date. O dia atual é o dia local da máquina, convertido para a mesma representação. Prazo para hoje não significa atraso.
- O sistema pressupõe uma execução por vez. MongoDB standalone não oferece transações multidocumento para este cenário. Empréstimos são gravados primeiro e a disponibilidade é atualizada em seguida. Se essa atualização falhar, o sistema avisa e a próxima inicialização reconcilia os livros a partir dos empréstimos pendentes. Não há garantia de atomicidade entre coleções.
- O CRUD garante a ausência de empréstimos pendentes simultâneos, não valida sobreposição retrospectiva de intervalos históricos em edições manuais de datas.

## 7. As cinco buscas

| Nº | Busca | Entrada | Implementação |
| --- | --- | --- | --- |
| 1 | Livros pelo título | Texto completo ou parcial | `find()` com `$regex`, `$options: i` e texto escapado; ordenação por título |
| 2 | Livros disponíveis por gênero | Gênero | `find()` com igualdade de gênero normalizado e `disponivel: true`; ordenação por título |
| 3 | Leitor pela matrícula | Matrícula exata | `find_one()` com igualdade de matrícula |
| 4 | Empréstimos atrasados | Nenhuma | `find()` com `data_prevista < hoje` (`$lt`) e devolução nula; ordenação pelo prazo e cálculo de dias de atraso |
| 5 | Histórico de empréstimos do leitor | Matrícula | `find_one()` para localizar leitor; `find()` por `leitor_id`, ordenado por data decrescente |

As buscas 4 e 5 consultam os documentos relacionados por `find_one()`, sem `$lookup`. A abordagem é simples e suficiente para o pequeno volume acadêmico. Em um banco maior, consultas em lote ou agregações poderiam reduzir o número de operações.

A situação exibida segue a regra: devolvido se houver data de devolução; atrasado se o prazo passou sem devolução; ativo nos demais casos.

### Roteiro de demonstração com os dados fornecidos

Depois de importar a demonstração em um banco vazio e antes de modificar os registros:

| Busca | Entrada | Resultado esperado |
| --- | --- | --- |
| 1 | `harry` | 2 livros da série Harry Potter |
| 2 | `Fantasia` | 3 exemplares disponíveis: os dois Harry Potter e O Senhor dos Anéis |
| 3 | `20260015` | João Silva |
| 4 | Sem entrada | O Hobbit (10 dias de atraso) e Dom Casmurro (4 dias) |
| 5 | `20260015` | 3 empréstimos de João: 1984 (ativo), O Hobbit (atrasado), O Pequeno Príncipe (devolvido) |

Os resultados de datas pressupõem a importação com ajuste automático e consulta no mesmo dia. Os leitores e seus contatos são fictícios.

## 8. Administração local do MongoDB

Acesse o banco pelo terminal usando o cliente `mongosh` que acompanha o contêiner:

```bash
docker compose exec mongodb mongosh biblioteca_db
```

Dentro do `mongosh`:

```javascript
show collections
db.livros.find()
db.leitores.find()
db.emprestimos.find()
db.emprestimos.getIndexes()
exit
```

| Comando no terminal do sistema | Finalidade |
| --- | --- |
| `docker compose ps` | Estado do serviço |
| `docker compose logs mongodb` | Logs do banco |
| `docker compose stop` | Interrompe preservando o contêiner e os dados |
| `docker compose start` | Reinicia o contêiner existente |
| `docker compose down` | Remove contêiner e rede, preservando o volume nomeado |
| `docker compose up -d --wait` | Inicializa novamente |

**Atenção:** `docker compose down -v` remove também o volume e apaga todo o banco. Utilize somente para reinicializar deliberadamente o ambiente, depois de exportar os dados que queira preservar.

## 9. Exportação e importação para entrega

O ZIP inclui os três arquivos JSON estendido com `ObjectId` e datas. O volume Docker não precisa ser enviado. Para exportar o banco após alterações, encerre a aplicação e mantenha o MongoDB em execução.

Windows:

```powershell
.\.venv\Scripts\python.exe dados.py exportar --pasta exportacao
```

Linux/macOS:

```bash
./.venv/bin/python dados.py exportar --pasta exportacao
```

O script preserva os tipos BSON em JSON estendido canônico e não sobrescreve arquivos existentes. A pasta escolhida deve ser nova ou não conter os três JSON de saída. Para importar essa exportação em um banco vazio:

Windows:

```powershell
.\.venv\Scripts\python.exe dados.py importar --pasta exportacao --datas-originais
```

Linux/macOS:

```bash
./.venv/bin/python dados.py importar --pasta exportacao --datas-originais
```

Os índices são recriados automaticamente; não fazem parte do JSON. Não use o importador simultaneamente com a aplicação. Para entregar um banco modificado, inclua os arquivos exportados juntamente ao código, mantendo apenas dados fictícios. Não envie `.venv`, caches Python, credenciais, imagens Docker ou volumes brutos.

## 10. Testes e verificação

Com o driver instalado e o MongoDB em execução, execute na raiz do projeto:

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux/macOS:

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

Os testes usam apenas `unittest` da biblioteca padrão. Os testes de integração criam bancos temporários com nomes aleatórios e os excluem ao terminar; não modificam `biblioteca_db`. Se o driver ou o servidor estiver indisponível, os testes de integração são ignorados (skipped), o que não equivale a aprovação desses testes.

Estado da validação nesta entrega: todos os módulos passaram pela compilação sintática; 8 testes locais de validação e integridade dos JSON passaram. Os 4 testes de integração foram ignorados porque o ambiente de geração não disponibilizou Docker/MongoDB nem PyMongo. A execução integrada, incluindo configuração do Compose e persistência real, deve ser confirmada na máquina de apresentação.

Checklist manual:

- [ ] Criar o ambiente seguindo a seção 4.
- [ ] Confirmar as três coleções e os índices no `mongosh`.
- [ ] Executar as cinco buscas conforme a seção 7.
- [ ] Cadastrar, atualizar, listar e excluir registros nas três coleções.
- [ ] Testar duplicidade de matrícula e empréstimo de livro indisponível.
- [ ] Registrar devolução e confirmar a disponibilidade.
- [ ] Confirmar bloqueio de exclusão de livros/leitores vinculados.
- [ ] Confirmar que `docker compose down` seguido de `docker compose up -d --wait` preserva os registros.
- [ ] Exportar e importar os dados em ambiente vazio de teste.

## 11. Solução de problemas

| Problema | Solução |
| --- | --- |
| Docker não está em execução | Inicie o serviço e verifique `docker info`. |
| MongoDB não responde | Consulte `docker compose ps`, os logs e o ping da seção 4. |
| Porta 27017 em uso | Encerre o serviço conflitante ou altere a porta publicada e a variável `MONGODB_URI` para a mesma porta. |
| `ModuleNotFoundError: pymongo` | Instale `requirements.txt` com o Python de `.venv` e execute o mesmo Python. |
| Importação recusada | As três coleções devem estar vazias; não sobrescreva registros. |
| Falha ao sincronizar disponibilidade | Não repita uma gravação sem verificar o registro; reinicie a aplicação para reconciliar os livros. |
| ID inválido | Copie o ObjectId completo da listagem. |

Se mudar a porta publicada para 27018, por exemplo, ajuste o mapeamento do Compose para `127.0.0.1:27018:27017` e defina a URI no terminal antes de iniciar o Python (`$env:MONGODB_URI = 'mongodb://127.0.0.1:27018/'` no PowerShell ou `export MONGODB_URI=mongodb://127.0.0.1:27018/` no Bash).

## 12. Escopo

Projeto acadêmico local, destinado a poucos registros e um usuário por vez. Não inclui autenticação, multas, reservas, notificações, interface gráfica, servidor web, hospedagem remota ou transações distribuídas. O foco é demonstrar modelagem documental, operações CRUD, integridade lógica, índices e consultas MongoDB.
