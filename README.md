# Jogo do Cofre Digital

Aplicação cliente/servidor em Python para a disciplina de Sistemas Distribuídos.
O jogo usa Socket TCP para que clientes enviem uma aposta ao servidor, enquanto o
servidor mantém um fundo acumulado compartilhado entre todos os jogadores.

## Objetivo

Cada cliente informa seu nome e uma aposta entre 0 e 999. Para cada jogada, o
servidor gera um código entre 0 e 999, adiciona R$ 2,00 ao fundo acumulado e
verifica se a aposta acertou o código.

Se o jogador errar, o fundo continua acumulado. Se acertar, ele recebe 60% do
fundo daquele momento e o fundo é zerado.

## Como executar

Primeiro, abra um terminal na pasta do projeto e inicie o servidor:

```bash
python servidor.py
```

Por padrão, o servidor escuta na porta TCP `5000`. Para escolher outra porta:

```bash
python servidor.py --porta 6000
```

Depois, abra outro terminal na mesma pasta e execute um cliente:

```bash
python cliente.py
```

Se o servidor estiver em outra porta:

```bash
python cliente.py --porta 6000
```

## Exemplo com terminais diferentes

Terminal 1, servidor:

```bash
python servidor.py
```

Terminal 2, primeiro cliente:

```bash
python cliente.py
Nome do jogador: Ana
Aposta (inteiro entre 0 e 999): 123
Código errado, Ana. O cofre tem R$ 2,00 acumulados.
```

Terminal 3, segundo cliente:

```bash
python cliente.py
Nome do jogador: Bruno
Aposta (inteiro entre 0 e 999): 456
Código errado, Bruno. O cofre tem R$ 4,00 acumulados.
```

## Onde o Socket TCP é usado

No arquivo `servidor.py`, o servidor cria um socket TCP com:

```python
socket.socket(socket.AF_INET, socket.SOCK_STREAM)
```

Ele chama `bind`, `listen` e `accept` para escutar conexões de clientes.

No arquivo `cliente.py`, o cliente também cria um socket TCP e usa `connect` para
se conectar ao servidor.

## Onde existe uma thread por cliente

No arquivo `servidor.py`, cada conexão aceita pelo `accept` cria uma nova thread:

```python
threading.Thread(target=atender_cliente, args=(conexao, endereco), daemon=True)
```

Assim, vários clientes podem jogar enquanto o servidor continua em execução.

## Por que o Lock é necessário

O fundo acumulado é uma variável global compartilhada por todas as threads do
servidor. Sem `threading.Lock`, duas threads poderiam ler e alterar o fundo ao
mesmo tempo, causando condição de corrida e valores incorretos.

Por isso, em `servidor.py`, toda leitura e alteração de `fundo_acumulado` ocorre
dentro de:

```python
with lock_fundo:
```

## Formato das mensagens JSON

O cliente envia um objeto JSON com nome e aposta:

```json
{"nome": "Nome do jogador", "aposta": 123}
```

O servidor responde com um objeto JSON contendo a mensagem para exibição:

```json
{"mensagem": "Código errado, Nome do jogador. O cofre tem R$ 2,00 acumulados."}
```

As mensagens são enviadas pelo socket em UTF-8, com uma quebra de linha no final.
Essa quebra de linha separa uma mensagem JSON da próxima dentro do fluxo TCP.

## Teste de vitória para demonstração

No arquivo `servidor.py`, existe a constante:

```python
CODIGO_FIXO = None
```

Ela existe apenas para demonstração e testes. Com `None`, o servidor usa
`random.randint(0, 999)`. Para forçar uma vitória, altere temporariamente para:

```python
CODIGO_FIXO = 123
```

Depois reinicie o servidor e execute o cliente apostando `123`.
