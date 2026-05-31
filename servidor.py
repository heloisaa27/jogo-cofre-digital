import argparse
import json
import random
import socket
import threading

HOST_PADRAO = "0.0.0.0"
PORTA_PADRAO = 5000
VALOR_POR_JOGADA = 2.0
PERCENTUAL_PREMIO = 0.60

CODIGO_FIXO = None

fundo_acumulado = 0.0
lock_fundo = threading.Lock()

def formatar_moeda(valor):
    return f"R$ {valor:.2f}".replace(".", ",")

def enviar_json(arquivo, dados):
    mensagem = json.dumps(dados, ensure_ascii=False) + "\n"
    arquivo.write(mensagem.encode("utf-8"))
    arquivo.flush()

def receber_json(arquivo):
    linha = arquivo.readline()
    if not linha:
        raise ValueError("nenhum dado recebido")
    return json.loads(linha.decode("utf-8"))

def validar_pedido(dados):
    if not isinstance(dados, dict):
        return None, None, "Pedido inválido: envie um objeto JSON."

    nome = dados.get("nome")
    aposta = dados.get("aposta")

    if not isinstance(nome, str) or not nome.strip():
        return None, None, "Pedido inválido: o nome deve ser um texto não vazio."

    if not isinstance(aposta, int) or not 0 <= aposta <= 999:
        return None, None, "Pedido inválido: a aposta deve ser um inteiro entre 0 e 999."

    return nome.strip(), aposta, None

def gerar_codigo():
    if CODIGO_FIXO is not None:
        return CODIGO_FIXO
    return random.randint(0, 999)

def registrar_log(endereco, nome, aposta, codigo, fundo_antes, fundo_depois, resultado):
    print(
        f"[{endereco[0]}:{endereco[1]}] "
        f"nome={nome!r} aposta={aposta} sorteado={codigo:03d} "
        f"fundo_antes={formatar_moeda(fundo_antes)} "
        f"fundo_depois={formatar_moeda(fundo_depois)} resultado={resultado}",
        flush=True,
    )

def atender_cliente(conexao, endereco):
    print(f"Cliente conectado: {endereco[0]}:{endereco[1]}", flush=True)

    try:
        with conexao:
            with conexao.makefile("rwb") as arquivo:
                try:
                    dados = receber_json(arquivo)
                except json.JSONDecodeError:
                    enviar_json(arquivo, {"mensagem": "Erro: JSON inválido."})
                    print(f"[{endereco[0]}:{endereco[1]}] JSON inválido recebido.", flush=True)
                    return
                except ValueError as erro:
                    enviar_json(arquivo, {"mensagem": f"Erro: {erro}."})
                    print(f"[{endereco[0]}:{endereco[1]}] {erro}.", flush=True)
                    return

                nome, aposta, erro = validar_pedido(dados)
                if erro:
                    enviar_json(arquivo, {"mensagem": erro})
                    print(f"[{endereco[0]}:{endereco[1]}] {erro}", flush=True)
                    return

                codigo = gerar_codigo()

                global fundo_acumulado
                with lock_fundo:
                    fundo_antes = fundo_acumulado
                    fundo_acumulado += VALOR_POR_JOGADA

                    if aposta == codigo:
                        premio = fundo_acumulado * PERCENTUAL_PREMIO
                        mensagem = f"Cofre aberto, {nome}! Ganhou {formatar_moeda(premio)}"
                        fundo_acumulado = 0.0
                        resultado = "acerto"
                    else:
                        mensagem = (
                            f"Código errado, {nome}. "
                            f"O cofre tem {formatar_moeda(fundo_acumulado)} acumulados."
                        )
                        resultado = "erro"

                    fundo_depois = fundo_acumulado

                enviar_json(arquivo, {"mensagem": mensagem})
                registrar_log(endereco, nome, aposta, codigo, fundo_antes, fundo_depois, resultado)
    except OSError as erro:
        print(f"Erro ao atender {endereco[0]}:{endereco[1]}: {erro}", flush=True)
    finally:
        print(f"Cliente desconectado: {endereco[0]}:{endereco[1]}", flush=True)

def iniciar_servidor(host, porta):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((host, porta))
        servidor.listen()

        print(f"Servidor escutando em {host}:{porta}", flush=True)

        while True:
            conexao, endereco = servidor.accept()
            thread = threading.Thread(
                target=atender_cliente,
                args=(conexao, endereco),
                daemon=True,
            )
            thread.start()

def ler_argumentos():
    parser = argparse.ArgumentParser(description="Servidor do Jogo do Cofre Digital")
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
    iniciar_servidor(argumentos.host, argumentos.porta)
