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

def formatar_matriz_para_md(matriz):
    linhas_formatadas = []
    for linha in matriz:
        linhas_formatadas.append("[" + ", ".join(f"{valor:.6f}" for valor in linha) + "]")
    return "\n".join(linhas_formatadas)

# 1. MULTIPLICAÇÃO LOCAL (TOTALMENTE SERIAL)
def multiplicar_local_serial(A, B):
    linhas_A, colunas_A, colunas_B = len(A), len(A[0]), len(B[0])
    C = [[0.0 for _ in range(colunas_B)] for _ in range(linhas_A)]
    for i in range(linhas_A):
        for j in range(colunas_B):
            for k in range(colunas_A):
                C[i][j] += A[i][k] * B[k][j]
    return C

def enviar_tarefa_para_servidor(url_servidor, bloco_A, B, indice_inicio, modo_paralelo):
    """Envia a tarefa escolhendo a função do servidor com base no modo."""
    with xmlrpc.client.ServerProxy(url_servidor) as proxy:
        if modo_paralelo:
            return proxy.calcular_bloco_paralelo(bloco_A, B, indice_inicio)
        else:
            return proxy.calcular_bloco_serial(bloco_A, B, indice_inicio)

# 2 e 3. ORQUESTRADOR DISTRIBUÍDO (CHAMA O MODO SERIAL OU PARALELO DO ESCRAVO)
def multiplicar_distribuido(A, B, urls_servidores, modo_paralelo_no_servidor):
    linhas_A = len(A)
    num_nos = len(urls_servidores)
    tamanho_bloco = max(1, linhas_A // num_nos)
    
    tarefas = []
    for i, inicio in enumerate(range(0, linhas_A, tamanho_bloco)):
        bloco_A = A[inicio:inicio + tamanho_bloco]
        url = urls_servidores[i % num_nos]
        tarefas.append((url, bloco_A, B, inicio))
        
    C = [[0.0 for _ in range(len(B[0]))] for _ in range(linhas_A)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_nos) as executor:
        futuros = [
            executor.submit(enviar_tarefa_para_servidor, url, bloco, B, idx, modo_paralelo_no_servidor) 
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
    tempos_dist_serial = []
    tempos_dist_paralelo = []

    resultados_matrizes = []
    
    print(f"--- BATERIA DE COMPARAÇÃO TRIPLHA ({len(SERVIDORES_RPC)} nós) ---")
    
    for N in tamanhos_n:
        print(f"  > Executando testes para matriz {N}x{N}...")
        A = gerar_matriz(N, N)
        B = gerar_matriz(N, N)
        
        # Teste 1: Totalmente Serial Local
        inicio = time.perf_counter()
        C_serial = multiplicar_local_serial(A, B)
        t_serial = time.perf_counter() - inicio
        tempos_serial.append(t_serial)
        
        # Teste 2: Distribuído (Com Servidores rodando em Serial)
        inicio = time.perf_counter()
        C_dist_serial = multiplicar_distribuido(A, B, SERVIDORES_RPC, modo_paralelo_no_servidor=False)
        t_dist_serial = time.perf_counter() - inicio
        tempos_dist_serial.append(t_dist_serial)
        
        # Teste 3: Distribuído Híbrido (Com Servidores rodando em Paralelo)
        inicio = time.perf_counter()
        C_dist_paralelo = multiplicar_distribuido(A, B, SERVIDORES_RPC, modo_paralelo_no_servidor=True)
        t_dist_paralelo = time.perf_counter() - inicio
        tempos_dist_paralelo.append(t_dist_paralelo)

        resultados_matrizes.append({
            "N": N,
            "A": A,
            "B": B,
            "C_serial": C_serial,
            "C_dist_serial": C_dist_serial,
            "C_dist_paralelo": C_dist_paralelo,
        })
        
        print(f"    S: {t_serial:.4f}s | Dist-Serial: {t_dist_serial:.4f}s | Dist-Paralelo: {t_dist_paralelo:.4f}s")

    # Calcular os Speedups em relação ao Serial Puro Local
    speedups_dist_serial = [s / ds for s, ds in zip(tempos_serial, tempos_dist_serial)]
    speedups_dist_paralelo = [s / dp for s, dp in zip(tempos_serial, tempos_dist_paralelo)]

    # ==========================================
    # IMPRESSÃO DA TABELA COMPREENSIVA
    # ==========================================
    print("\n" + "="*85)
    print(" " * 30 + "TABELA COMPARATIVA DE DESEMPENHO")
    print("="*85)
    print(f"{'N':<6} | {'Serial Local':<14} | {'Dist. (Escravo S)':<18} | {'Dist. (Escravo P)':<18} | {'SPDP Escravo P'}")
    print("-" * 85)
    for i, N in enumerate(tamanhos_n):
        print(f"{N:<6} | {tempos_serial[i]:<12.4f}s | {tempos_dist_serial[i]:<16.4f}s | {tempos_dist_paralelo[i]:<16.4f}s | {speedups_dist_paralelo[i]:.2f}x")
    print("="*85)

    # ==========================================
    # GERAÇÃO DO ARQUIVO result.md COM MATRIZES
    # ==========================================
    print("\nGerando arquivo result.md com as matrizes e resultados...")
    with open("result.md", "w", encoding="utf-8") as arquivo:
        arquivo.write("# Resultados das Multiplicações\n\n")
        for item in resultados_matrizes:
            arquivo.write(f"## Matriz {item['N']}x{item['N']}\n\n")

            arquivo.write("### Matriz A\n\n")
            arquivo.write("```\n")
            arquivo.write(formatar_matriz_para_md(item["A"]))
            arquivo.write("\n```\n\n")

            arquivo.write("### Matriz B\n\n")
            arquivo.write("```\n")
            arquivo.write(formatar_matriz_para_md(item["B"]))
            arquivo.write("\n```\n\n")

            arquivo.write("### Resultado Serial Local\n\n")
            arquivo.write("```\n")
            arquivo.write(formatar_matriz_para_md(item["C_serial"]))
            arquivo.write("\n```\n\n")

            arquivo.write("### Resultado Distribuido (Escravo Serial)\n\n")
            arquivo.write("```\n")
            arquivo.write(formatar_matriz_para_md(item["C_dist_serial"]))
            arquivo.write("\n```\n\n")

            arquivo.write("### Resultado Distribuido (Escravo Paralelo)\n\n")
            arquivo.write("```\n")
            arquivo.write(formatar_matriz_para_md(item["C_dist_paralelo"]))
            arquivo.write("\n```\n\n")

        arquivo.write("\n")
    print("Arquivo result.md gerado com sucesso.")

    # ==========================================
    # GERAÇÃO DOS GRÁFICOS COMPARATIVOS
    # ==========================================
    print("\nGerando gráficos triplos...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Gráfico 1: Curvas de Tempo
    ax1.plot(tamanhos_n, tempos_serial, marker='o', color='red', label='Serial Local (1 núcleo)', linewidth=2)
    ax1.plot(tamanhos_n, tempos_dist_serial, marker='v', color='orange', linestyle='--', label='Distribuído (Escravo Serial)', linewidth=2)
    ax1.plot(tamanhos_n, tempos_dist_paralelo, marker='s', color='blue', label='Distribuído Híbrido (Escravo Paralelo)', linewidth=2)
    ax1.set_title('Comparação dos Tempos de Execução', fontsize=13)
    ax1.set_xlabel('Tamanho da Matriz (N)', fontsize=11)
    ax1.set_ylabel('Tempo (Segundos)', fontsize=11)
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(fontsize=10)

    # Gráfico 2: Curvas de Speedup Relativo
    ax2.plot(tamanhos_n, speedups_dist_serial, marker='v', color='orange', linestyle='--', label='Speedup Dist. (Escravo Serial)', linewidth=2)
    ax2.plot(tamanhos_n, speedups_dist_paralelo, marker='s', color='green', label='Speedup Dist. Híbrido (Escravo Paralelo)', linewidth=2)
    ax2.axhline(y=1, color='gray', linestyle=':', label='Baseline (Sem Ganho)')
    ax2.set_title('Ganho de Eficiência (Speedup Relativo ao Serial)', fontsize=13)
    ax2.set_xlabel('Tamanho da Matriz (N)', fontsize=11)
    ax2.set_ylabel('Fator de Aceleração (Vezes)', fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig('comparativo_computacao_distribuida.png', dpi=300)
    plt.show()
    print("Concluído! A imagem 'comparativo_computacao_distribuida.png' foi gerada com sucesso.")