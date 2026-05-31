import argparse
import json
import socket

HOST_PADRAO = "127.0.0.1"
PORTA_PADRAO = 5000

def enviar_json(arquivo, dados):
    mensagem = json.dumps(dados, ensure_ascii=False) + "\n"
    arquivo.write(mensagem.encode("utf-8"))
    arquivo.flush()

def receber_json(arquivo):
    linha = arquivo.readline()
    if not linha:
        raise ConnectionError("o servidor encerrou a conexão sem responder")
    return json.loads(linha.decode("utf-8"))

def pedir_nome():
    while True:
        nome = input("Nome do jogador: ").strip()
        if nome:
            return nome
        print("Informe um nome não vazio.")

def pedir_aposta():
    while True:
        texto = input("Aposta (inteiro entre 0 e 999): ").strip()
        try:
            aposta = int(texto)
        except ValueError:
            print("A aposta precisa ser um número inteiro.")
            continue

        if 0 <= aposta <= 999:
            return aposta

        print("A aposta precisa estar entre 0 e 999.")

def jogar(host, porta):
    nome = pedir_nome()
    aposta = pedir_aposta()
    pedido = {"nome": nome, "aposta": aposta}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
        cliente.connect((host, porta))
        with cliente.makefile("rwb") as arquivo:
            enviar_json(arquivo, pedido)
            resposta = receber_json(arquivo)

    print(resposta.get("mensagem", "Resposta inválida recebida do servidor."))

def ler_argumentos():
    parser = argparse.ArgumentParser(description="Cliente do Jogo do Cofre Digital")
    parser.add_argument("--host", default=HOST_PADRAO, help=f"host do servidor, padrão {HOST_PADRAO}")
    parser.add_argument(
        "--porta",
        type=int,
        default=PORTA_PADRAO,
        help=f"porta TCP do servidor, padrão {PORTA_PADRAO}",
    )
    return parser.parse_args()

if __name__ == "__main__":
    argumentos = ler_argumentos()
    try:
        jogar(argumentos.host, argumentos.porta)
    except ConnectionRefusedError:
        print("Não foi possível conectar ao servidor. Verifique se ele está em execução.")
    except OSError as erro:
        print(f"Erro de comunicação: {erro}")
    except json.JSONDecodeError:
        print("O servidor respondeu com JSON inválido.")
