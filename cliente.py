import time
import random
import concurrent.futures
import xmlrpc.client
import matplotlib.pyplot as plt

SERVIDORES_RPC = [
    "http://localhost:8000", 
    # "http://IP_DA_OUTRA_MAQUINA:8000" 
]

def gerar_matriz(linhas, colunas):
    return [[random.random() for _ in range(colunas)] for _ in range(linhas)]

def multiplicar_serial(A, B):
    linhas_A, colunas_A, colunas_B = len(A), len(A[0]), len(B[0])
    C = [[0.0 for _ in range(colunas_B)] for _ in range(linhas_A)]
    for i in range(linhas_A):
        for j in range(colunas_B):
            for k in range(colunas_A):
                C[i][j] += A[i][k] * B[k][j]
    return C

def enviar_tarefa_para_servidor(url_servidor, bloco_A, B, indice_inicio):
    """Envia um bloco da matriz para ser calculado em outra máquina via rede."""
    with xmlrpc.client.ServerProxy(url_servidor) as proxy:
        return proxy.calcular_bloco(bloco_A, B, indice_inicio)

def multiplicar_distribuido(A, B, urls_servidores):
    """(Metodologia de Foster: Mapeamento e Particionamento Distribuído)."""
    linhas_A = len(A)
    num_nos = len(urls_servidores)
    tamanho_bloco = max(1, linhas_A // num_nos)
    
    tarefas = []
    for i, inicio in enumerate(range(0, linhas_A, tamanho_bloco)):
        bloco_A = A[inicio:inicio + tamanho_bloco]
        url = urls_servidores[i % num_nos] # Balanceia a carga entre os nós
        tarefas.append((url, bloco_A, B, inicio))
        
    C = [[0.0 for _ in range(len(B[0]))] for _ in range(linhas_A)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_nos) as executor:
        futuros = [
            executor.submit(enviar_tarefa_para_servidor, url, bloco, B, idx) 
            for url, bloco, B, idx in tarefas
        ]
        
        for futuro in concurrent.futures.as_completed(futuros):
            indice_inicio, bloco_C = futuro.result()
            for i, linha in enumerate(bloco_C):
                C[indice_inicio + i] = linha
    return C

if __name__ == '__main__':
    tamanhos_n = [50, 100, 150, 200, 250, 300] 
    
    tempos_serial = []
    tempos_distribuido = []
    speedups = []
    
    print(f"--- BATERIA DE TESTES: DISTRIBUIÇÃO ({len(SERVIDORES_RPC)} nós) ---")
    
    for N in tamanhos_n:
        print(f"  > Matriz {N}x{N}...", end="", flush=True)
        A = gerar_matriz(N, N)
        B = gerar_matriz(N, N)
        
        inicio = time.perf_counter()
        _ = multiplicar_serial(A, B)
        t_serial = time.perf_counter() - inicio
        tempos_serial.append(t_serial)
        
        inicio = time.perf_counter()
        _ = multiplicar_distribuido(A, B, SERVIDORES_RPC)
        t_distribuido = time.perf_counter() - inicio
        tempos_distribuido.append(t_distribuido)
        
        speedup = t_serial / t_distribuido if t_distribuido > 0 else 0
        speedups.append(speedup)
        print(f" OK! (Serial: {t_serial:.2f}s | Rede: {t_distribuido:.2f}s)")

    print("\n" + "="*60)
    print(" " * 15 + "RESUMO DE DESEMPENHO")
    print("="*60)
    print(f"{'Tamanho (N)':<15} | {'Tempo Serial':<15} | {'Tempo Distribuído':<15} | {'Speedup'}")
    print("-" * 60)
    for i, N in enumerate(tamanhos_n):
        print(f"{N}x{N:<10} | {tempos_serial[i]:<13.4f}s | {tempos_distribuido[i]:<13.4f}s | {speedups[i]:.2f}x")
    print("="*60)
    print("\nGerando gráficos...")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    ax1.plot(tamanhos_n, tempos_serial, marker='o', color='red', label='Serial (1 núcleo)', linewidth=2)
    ax1.plot(tamanhos_n, tempos_distribuido, marker='o', color='blue', label=f'Distribuído ({len(SERVIDORES_RPC)} nós)', linewidth=2)
    ax1.set_title('Tempo de Execução por Tamanho da Matriz', fontsize=14)
    ax1.set_xlabel('Tamanho da Matriz (N)', fontsize=12)
    ax1.set_ylabel('Tempo (Segundos)', fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend(fontsize=12)

    ax2.plot(tamanhos_n, speedups, marker='s', color='green', linewidth=2)
    ax2.axhline(y=1, color='gray', linestyle='--', label='Baseline (Sem Ganho)')
    ax2.set_title('Ganho de Eficiência (Speedup)', fontsize=14)
    ax2.set_xlabel('Tamanho da Matriz (N)', fontsize=12)
    ax2.set_ylabel('Vezes Mais Rápido (X)', fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend(fontsize=12)

    plt.tight_layout()
    plt.savefig('grafico_desempenho_matrizes.png', dpi=300)
    plt.show()
    print("Concluído! A imagem 'grafico_desempenho_matrizes.png' foi salva no diretório.")