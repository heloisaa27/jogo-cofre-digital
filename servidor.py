import argparse
import json
import random
import socket
import threading
from typing import Optional, Tuple, Any

HOST_PADRAO = "0.0.0.0"
PORTA_PADRAO = 5000
VALOR_POR_JOGADA = 2.0
PERCENTUAL_PREMIO = 0.60

CODIGO_FIXO = None

class Cofre:
    def __init__(self) -> None:
        self.fundo_acumulado: float = 0.0
        self.codigos_por_jogador: dict = {}
        self.lock = threading.Lock()

    def registrar_jogada(self, nome: str, aposta: int) -> Tuple[float, float, bool, float, int]:
        with self.lock:
            if nome not in self.codigos_por_jogador:
                self.codigos_por_jogador[nome] = gerar_codigo()
            
            codigo = self.codigos_por_jogador[nome]

            fundo_antes = self.fundo_acumulado
            self.fundo_acumulado += VALOR_POR_JOGADA
            fundo_depois = self.fundo_acumulado
            
            venceu = (aposta == codigo)
            premio = 0.0
            
            if venceu:
                premio = self.fundo_acumulado * PERCENTUAL_PREMIO
                self.fundo_acumulado = 0.0
                del self.codigos_por_jogador[nome]
                
            return fundo_antes, fundo_depois, venceu, premio, codigo

cofre_digital = Cofre()

def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")

def enviar_json(arquivo, dados: dict) -> None:
    mensagem = json.dumps(dados, ensure_ascii=False) + "\n"
    arquivo.write(mensagem.encode("utf-8"))
    arquivo.flush()

def receber_json(arquivo) -> Any:
    linha = arquivo.readline()
    if not linha:
        raise ValueError("nenhum dado recebido")
    return json.loads(linha.decode("utf-8"))

def validar_pedido(dados: Any) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    if not isinstance(dados, dict):
        return None, None, "Pedido inválido: envie um objeto JSON."

    nome = dados.get("nome")
    aposta = dados.get("aposta")

    if not isinstance(nome, str) or not nome.strip():
        return None, None, "Pedido inválido: o nome deve ser um texto não vazio."

    if type(aposta) is not int or not 0 <= aposta <= 999:
        return None, None, "Pedido inválido: a aposta deve ser um inteiro entre 0 e 999."

    return nome.strip(), aposta, None

def gerar_codigo() -> int:
    if CODIGO_FIXO is not None:
        return CODIGO_FIXO
    return random.randint(0, 999)

def registrar_log(endereco: Tuple[str, int], nome: str, aposta: int, codigo: int, fundo_antes: float, fundo_depois: float, resultado: str) -> None:
    print(
        f"[{endereco[0]}:{endereco[1]}] "
        f"nome={nome!r} aposta={aposta} sorteado={codigo:03d} "
        f"fundo_antes={formatar_moeda(fundo_antes)} "
        f"fundo_depois={formatar_moeda(fundo_depois)} resultado={resultado}",
        flush=True,
    )

def atender_cliente(conexao: socket.socket, endereco: Tuple[str, int]) -> None:
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
                if erro or nome is None or aposta is None:
                    enviar_json(arquivo, {"mensagem": erro})
                    print(f"[{endereco[0]}:{endereco[1]}] {erro}", flush=True)
                    return

                fundo_antes, fundo_depois, venceu, premio, codigo = cofre_digital.registrar_jogada(nome, aposta)

                if venceu:
                    mensagem = f"Cofre aberto, {nome}! Ganhou {formatar_moeda(premio)}"
                    resultado = "acerto"
                else:
                    mensagem = (
                        f"Código errado, {nome}. "
                        f"O cofre tem {formatar_moeda(fundo_depois)} acumulados."
                    )
                    resultado = "erro"

                enviar_json(arquivo, {"mensagem": mensagem})
                registrar_log(endereco, nome, aposta, codigo, fundo_antes, fundo_depois, resultado)
    except OSError as erro:
        print(f"Erro ao atender {endereco[0]}:{endereco[1]}: {erro}", flush=True)
    finally:
        print(f"Cliente desconectado: {endereco[0]}:{endereco[1]}", flush=True)

def iniciar_servidor(host: str, porta: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((host, porta))
        servidor.listen()

        print(f"Servidor escutando em {host}:{porta}", flush=True)

        try:
            while True:
                conexao, endereco = servidor.accept()
                thread = threading.Thread(
                    target=atender_cliente,
                    args=(conexao, endereco),
                    daemon=True,
                )
                thread.start()
        except KeyboardInterrupt:
            print("\nServidor encerrado pelo usuário (Graceful Shutdown).", flush=True)

def ler_argumentos() -> argparse.Namespace:
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
