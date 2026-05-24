from xmlrpc.server import SimpleXMLRPCServer
import multiprocessing
import concurrent.futures

def worker_linha_individual(args):
    linha_A, B, indice_linha = args
    colunas_A = len(linha_A)
    colunas_B = len(B[0])
    linha_C = [0.0 for _ in range(colunas_B)]
    
    for j in range(colunas_B):
        for k in range(colunas_A):
            linha_C[j] += linha_A[k] * B[k][j]
    return indice_linha, linha_C

def calcular_bloco_serial(bloco_A, B, indice_inicio):
    """Calcula o bloco recebido usando apenas 1 núcleo."""
    linhas_bloco = len(bloco_A)
    colunas_A = len(bloco_A[0])
    colunas_B = len(B[0])
    bloco_C = [[0.0 for _ in range(colunas_B)] for _ in range(linhas_bloco)]
    
    for i in range(linhas_bloco):
        for j in range(colunas_B):
            for k in range(colunas_A):
                bloco_C[i][j] += bloco_A[i][k] * B[k][j]
    return indice_inicio, bloco_C

def calcular_bloco_paralelo(bloco_A, B, indice_inicio):
    """Calcula o bloco recebido dividindo as linhas entre os núcleos locais."""
    linhas_bloco = len(bloco_A)
    colunas_B = len(B[0])
    bloco_C = [[0.0 for _ in range(colunas_B)] for _ in range(linhas_bloco)]
    
    tarefas = []
    for i, linha in enumerate(bloco_A):
        tarefas.append((linha, B, i))
    
    nucleos = multiprocessing.cpu_count()
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=nucleos) as executor:
        resultados = executor.map(worker_linha_individual, tarefas)
        for indice_linha, linha_calculada in resultados:
            bloco_C[indice_linha] = linha_calculada
            
    return indice_inicio, bloco_C

if __name__ == "__main__":
    porta = 8000
    server = SimpleXMLRPCServer(("0.0.0.0", porta), allow_none=True, logRequests=False)
    
    # Registra as duas funções com nomes distintos no RPC
    server.register_function(calcular_bloco_serial, "calcular_bloco_serial")
    server.register_function(calcular_bloco_paralelo, "calcular_bloco_paralelo")
    
    print(f"Servidor Híbrido RPC pronto na porta {porta}...")
    print("Disponível: 'calcular_bloco_serial' e 'calcular_bloco_paralelo'")
    server.serve_forever()