from xmlrpc.server import SimpleXMLRPCServer
import multiprocessing

def worker_calcular_bloco_linhas(bloco_A, B, indice_inicio):
    """Executado na máquina servidora para calcular um bloco da matriz."""
    linhas_bloco = len(bloco_A)
    colunas_A = len(bloco_A[0])
    colunas_B = len(B[0])
    bloco_C = [[0.0 for _ in range(colunas_B)] for _ in range(linhas_bloco)]
    
    for i in range(linhas_bloco):
        for j in range(colunas_B):
            for k in range(colunas_A):
                bloco_C[i][j] += bloco_A[i][k] * B[k][j]
    return indice_inicio, bloco_C

if __name__ == "__main__":
    porta = 8000
    server = SimpleXMLRPCServer(("0.0.0.0", porta), allow_none=True)
    server.register_function(worker_calcular_bloco_linhas, "calcular_bloco")
    
    print(f"Servidor RPC rodando e aguardando matrizes na porta {porta}...")
    server.serve_forever()