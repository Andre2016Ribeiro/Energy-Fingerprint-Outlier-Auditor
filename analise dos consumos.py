
import pandas as pd
import holidays
import matplotlib
# Configuração obrigatória do motor gráfico nativo do Windows
matplotlib.use('TkAgg') 
import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. CARREGAR METADADOS E DADOS DO EXCEL
# ==========================================
ficheiro_excel = "Consumos_PT0002000116632716GH_20260609114521.xlsx"  # Substitua pelo nome real do seu ficheiro

df_meta = pd.read_excel(ficheiro_excel, nrows=8, header=None)
cpe_texto = str(df_meta.iloc[2, 1]).strip()      # Célula B3
periodo_texto = str(df_meta.iloc[6, 1]).strip()  # Célula B7

df = pd.read_excel(ficheiro_excel, skiprows=9, usecols=[0, 1, 2])
df.columns = ['Data', 'Hora', 'Consumo_Original']

df['Data_Hora'] = pd.to_datetime(df['Data'].astype(str) + ' ' + df['Hora'].astype(str))
df['Data_Apenas'] = df['Data_Hora'].dt.date
df['Consumo_15min'] = df['Consumo_Original'] / 4

# Consumo total absoluto do período
consumo_total_periodo_kwh = df['Consumo_15min'].sum()

# Filtrar Fins de Semana e Feriados de Portugal
feriados_pt = holidays.Portugal(years=df['Data_Hora'].dt.year.unique().tolist())
df_uteis = df[df['Data_Hora'].dt.dayofweek < 5].copy()
df_uteis = df_uteis[~df_uteis['Data_Apenas'].isin(feriados_pt)]

dias_semana_pt = {0: 'Segunda-feira', 1: 'Terca-feira', 2: 'Quarta-feira', 3: 'Quinta-feira', 4: 'Sexta-feira'}

df_uteis['Hora_DT'] = pd.to_datetime(df_uteis['Hora'].astype(str), format='%H:%M:%S', errors='coerce')
if df_uteis['Hora_DT'].isna().all():
    df_uteis['Hora_DT'] = pd.to_datetime(df_uteis['Hora'].astype(str), format='%H:%M', errors='coerce')
df_uteis['Periodo_Producao'] = (df_uteis['Hora_DT'].dt.hour >= 6) & (df_uteis['Hora_DT'].dt.hour < 18)

# --- NOVO: CÁLCULO ESTRICTO DO PERÍODO SOLAR (11:00 às 15:00) ---
df_uteis['Periodo_Solar'] = (df_uteis['Hora_DT'].dt.hour >= 9) & (df_uteis['Hora_DT'].dt.hour < 17)

# Energia total consumida neste horário ao longo de todo o mês analisado (kWh)
energia_solar_periodo_kwh = df_uteis[df_uteis['Periodo_Solar']]['Consumo_15min'].sum()

# Percentagem que este horário representa face ao consumo total absoluto do mês
pct_energia_solar = (energia_solar_periodo_kwh / consumo_total_periodo_kwh) * 100

# Potência média real consumida neste período solar (kW)
# Nota: 4 horas por dia × número de dias úteis no ficheiro
total_horas_solares = len(df_uteis[df_uteis['Periodo_Solar']]) * 0.25
potencia_media_solar_kw = (energia_solar_periodo_kwh / total_horas_solares) * 4 if total_horas_solares > 0 else 0.0


# ==========================================
# 2. DEFINIR O PERFIL TÍPICO E MANCHA (90% DOS DIAS)
# ==========================================
consumo_diario_total = df_uteis.groupby('Data_Apenas')['Consumo_15min'].sum().reset_index()
q_inf, q_sup = consumo_diario_total['Consumo_15min'].quantile([0.05, 0.95])
dias_tipicos_ids = consumo_diario_total[(consumo_diario_total['Consumo_15min'] >= q_inf) & (consumo_diario_total['Consumo_15min'] <= q_sup)]['Data_Apenas']

df_dias_tipicos = df_uteis[df_uteis['Data_Apenas'].isin(dias_tipicos_ids)]
perfil_horario = df_dias_tipicos.groupby(df_dias_tipicos['Hora'].astype(str))['Consumo_15min'].agg(['median', 'std']).reset_index()
perfil_horario.columns = ['Hora', 'Consumo_Tipico_Hora', 'Desvio_Padrao_Hora']
total_kwh_perfil_tipico = perfil_horario['Consumo_Tipico_Hora'].sum()

perfil_horario['Hora_DT'] = pd.to_datetime(perfil_horario['Hora'], format='%H:%M:%S', errors='coerce')
if perfil_horario['Hora_DT'].isna().all():
    perfil_horario['Hora_DT'] = pd.to_datetime(perfil_horario['Hora'], format='%H:%M', errors='coerce')
Filtro_Producao = (perfil_horario['Hora_DT'].dt.hour >= 6) & (perfil_horario['Hora_DT'].dt.hour < 18)

# Construção da Mancha: Mediana Histórica +/- Margem Estatística
perfil_horario['Limite_Sup'] = perfil_horario['Consumo_Tipico_Hora'] + (1.5 * perfil_horario['Desvio_Padrao_Hora'])
perfil_horario['Limite_Inf'] = np.where(Filtro_Producao, perfil_horario['Consumo_Tipico_Hora'] - (0.3 * perfil_horario['Desvio_Padrao_Hora']), perfil_horario['Consumo_Tipico_Hora'] - (1.5 * perfil_horario['Desvio_Padrao_Hora']))
perfil_horario['Limite_Inf'] = perfil_horario['Limite_Inf'].clip(lower=0)

# Energia que está contida de forma acumulada dentro da zona normal
energia_contida_zona_normal = perfil_horario['Consumo_Tipico_Hora'].sum()

# ==========================================
# 3. TRATAMENTO MATEMÁTICO DOS OUTLIERS
# ==========================================
consumo_diurno_tipico = df_dias_tipicos[df_dias_tipicos['Periodo_Producao']].groupby('Data_Apenas')['Consumo_15min'].sum().mean()
df_analise = df_uteis.merge(perfil_horario[['Hora', 'Consumo_Tipico_Hora', 'Limite_Inf', 'Limite_Sup']], on='Hora', how='left')

df_analise['Abaixo_Limite'] = (df_analise['Consumo_15min'] < df_analise['Limite_Inf'])
df_analise['Acima_Limite'] = (df_analise['Consumo_15min'] > df_analise['Limite_Sup'])
df_analise['Dentro_Limite'] = (~df_analise['Abaixo_Limite']) & (~df_analise['Acima_Limite'])

# Calcular a percentagem de tempo total que todas as leituras úteis passaram dentro da mancha cinzenta
pct_tempo_dentro_mancha = (df_analise['Dentro_Limite'].sum() / len(df_analise)) * 100
# Multiplica o número de blocos dentro do limite pelo consumo real de cada um
energia_total_dentro_mancha = df_analise[df_analise['Dentro_Limite']]['Consumo_15min'].sum()

resumo_dias = df_analise.groupby('Data_Apenas').agg(
    Consumo_Total_Diurno=('Consumo_15min', lambda x: x[df_analise.loc[x.index, 'Periodo_Producao']].sum()),
    Total_kWh_Dia=('Consumo_15min', 'sum'),
    Intervalos_Abaixo=('Abaixo_Limite', 'sum'),
    Intervalos_Acima=('Acima_Limite', 'sum')
).reset_index()

resumo_dias['Status_Dia'] = 'Normal'
filtro_perfil_reduzido = resumo_dias['Consumo_Total_Diurno'] < (consumo_diurno_tipico * 0.90)
filtro_outro_outlier = (~filtro_perfil_reduzido) & ((resumo_dias['Intervalos_Abaixo'] >= 4) | (resumo_dias['Intervalos_Acima'] >= 6))

resumo_dias.loc[filtro_perfil_reduzido, 'Status_Dia'] = 'Perfil Atividade Reduzida'
resumo_dias.loc[filtro_outro_outlier, 'Status_Dia'] = 'Outro Outlier'

dias_alertas_df = resumo_dias[resumo_dias['Status_Dia'] != 'Normal'].copy()
dias_alertas_df = dias_alertas_df.sort_values(by='Total_kWh_Dia', ascending=True)

dias_reduzidos_ids = resumo_dias[resumo_dias['Status_Dia'] == 'Perfil Atividade Reduzida']['Data_Apenas'].tolist()

tem_segunda_mediana = len(dias_reduzidos_ids) >= 1
if tem_segunda_mediana:
    df_dias_reduzidos = df_uteis[df_uteis['Data_Apenas'].isin(dias_reduzidos_ids)]
    perfil_reduzido = df_dias_reduzidos.groupby(df_dias_reduzidos['Hora'].astype(str))['Consumo_15min'].median().reset_index()
    perfil_reduzido.columns = ['Hora', 'Consumo_Reduzido_Hora']
    total_kwh_perfil_reduzido = perfil_reduzido['Consumo_Reduzido_Hora'].sum()

# ==========================================
# 4. RENDERIZAÇÃO DO GRÁFICO (SHOW)
# ==========================================
plt.figure(figsize=(16, 9))
horas_x = perfil_horario['Hora']
# ==========================================
# 4. RENDERIZAÇÃO DO GRÁFICO (COM ZONA SOLAR)
# ==========================================
fig, ax = plt.subplots(figsize=(16, 9)) # Usamos fig e ax para permitir o sombreamento vertical
horas_x = perfil_horario['Hora']

# --- NOVO: MARCAÇÃO DA PRODUÇÃO SOLAR A AMARELO (Ex: 11h às 15h) ---
# Encontra a posição dos índices no eixo X para as horas escolhidas
hora_inicio_solar = "09:00:00"
hora_fim_solar = "17:00:00"

# Caso o seu Excel não tenha os segundos no texto, tenta o formato HH:MM
if hora_inicio_solar not in horas_x.values:
    hora_inicio_solar = "09:00"
    hora_fim_solar = "17:00"

try:
    idx_inicio = horas_x[horas_x == hora_inicio_solar].index[0]
    idx_fim = horas_x[horas_x == hora_fim_solar].index[0]
    # Desenha a barra amarela vertical no fundo do gráfico
    ax.axvspan(idx_inicio, idx_fim, color='gold', alpha=0.15, label=f'Zona de Maior Produção Solar (09:00 - 17:00) | Total energia solar: {energia_solar_periodo_kwh:.1f} kWh {pct_energia_solar:.1f}% do total mensal')
except IndexError:
    # Caso as horas exatas não batam certo (ex: 11:15), procura por aproximação
    horas_str = horas_x.astype(str)
    indices_solar = horas_str[horas_str.str.startswith(('11', '12', '13', '14'))].index
    if len(indices_solar) > 0:
        ax.axvspan(indices_solar[0], indices_solar[-1], color='gold', alpha=0.15, label='Zona de Maior Produção Solar (09h - 17h)')

# REQUISITO: Primeira linha com consumo mensal e percentagem de estabilidade temporal na mancha
plt.plot([], [], ' ', label=f'TOTAL Consumo Electrico (1 MES): {consumo_total_periodo_kwh:.1f} kWh | ESTABILIDADE NA ZONA CINZENTA: {pct_tempo_dentro_mancha:.1f}% do tempo')
plt.plot([], [], ' ', label=f'Energia consumida dentro area cinza: {energia_total_dentro_mancha:.1f} KWh')
# Explicação estatística integrada da mancha cinzenta
label_mancha = f'Zona Consumo Normal (90% dos dias centrais) | Energia Interna Contida: {energia_contida_zona_normal:.1f} kWh/dia'
plt.fill_between(horas_x, perfil_horario['Limite_Inf'] * 4, perfil_horario['Limite_Sup'] * 4, color='blue', alpha=0.1, label=label_mancha)

plt.plot(horas_x, perfil_horario['Consumo_Tipico_Hora'] * 4, color='black', linewidth=3.5, 
         label=f'PERFIL TIPICO MEDIANA 1 -- {total_kwh_perfil_tipico:.1f} kWh/dia')

if tem_segunda_mediana:
    plt.plot(horas_x, perfil_reduzido['Consumo_Reduzido_Hora'] * 4, color='forestgreen', linestyle='-', linewidth=4,
             label=f'PERFIL ATIVIDADE REDUZIDA MEDIANA 2 -- {total_kwh_perfil_reduzido:.1f} kWh/dia ---')

marcador_legenda_colocado = False
offset_texto = 1.5

for _, row in dias_alertas_df.iterrows():
    dia = row['Data_Apenas']
    total_kwh_dia = row['Total_kWh_Dia']
    status = row['Status_Dia']
    int_abaixo = row['Intervalos_Abaixo']
    
    data_formatada = dia.strftime('%Y-%m-%d') if hasattr(dia, 'strftime') else str(dia)
    num_dia_semana = dias_semana_pt.get(pd.to_datetime(dia).dayofweek, '')
    
    df_dia = df_analise[df_analise['Data_Apenas'] == dia].sort_values('Hora')
    pontos_fora = df_dia[df_dia['Abaixo_Limite'] | df_dia['Acima_Limite']]
    
    # REQUISITO: Correção Cirúrgica e Blindada dos kW Médios por linha
    df_dia_quebra = df_dia[df_dia['Abaixo_Limite']]
    if not df_dia_quebra.empty:
        # Média simples e direta da diferença ponto a ponto (multiplicado por 4 para passar de kWh/15min para kW)
        queda_med_inst = ((df_dia_quebra['Consumo_Tipico_Hora'] - df_dia_quebra['Consumo_15min']).mean()) * 4
    else:
        queda_med_inst = 0.0
        
    if status == 'Perfil Atividade Reduzida':
        cor = 'forestgreen'
        estilo = '--'
        prefixo = "Talvez menos maquinas de injeção a trabalhar"
        horas_reais_quebra = int_abaixo * 0.25 # 1 bloco = 15 min = 0.25h
        texto_analise = f" | Queda Media: -{queda_med_inst:.1f} kW (durante {horas_reais_quebra:.2f}h)"
        
        idx_meio = len(df_dia) // 2
        plt.text(df_dia['Hora'].iloc[idx_meio], (df_dia['Consumo_15min'].iloc[idx_meio] * 4) + offset_texto, 
                 f"{data_formatada}", color='forestgreen', fontsize=8, weight='bold')
        offset_texto += 1.5
    else:
        cor = 'purple'
        estilo = ':'
        prefixo = "dias que saiu do consumo tipico"
        texto_analise = f" | Desvio: {total_kwh_dia - total_kwh_perfil_tipico:+.1f} kWh"
        
    label_legenda = f"{prefixo:<20} | {data_formatada} ({num_dia_semana:<12}) | Consumo Diario: {total_kwh_dia:.1f} kWh{texto_analise}"
    plt.plot(df_dia['Hora'].astype(str), df_dia['Consumo_15min'] * 4, linestyle=estilo, alpha=0.5, color=cor, label=label_legenda)
    
    if not pontos_fora.empty:
        label_ponto = "Consumos instantaneos fora do intervalo" if not marcador_legenda_colocado else ""
        plt.scatter(pontos_fora['Hora'].astype(str), pontos_fora['Consumo_15min'] * 4, color='red', marker='.', s=15, zorder=5, label=label_ponto)
        marcador_legenda_colocado = True

plt.title(f'CPE: {cpe_texto} | Periodo: {periodo_texto}\nFingerprint Energetico Avancado com Diferenciacao de Perfis', 
          fontsize=13, fontweight='bold', pad=15)
plt.xlabel('Hora do Dia (Intervalos de 15 min)', fontsize=12)
plt.ylabel('Consumo Instantaneo Real (kW)', fontsize=12)
plt.xticks(horas_x[::4], rotation=45)
plt.grid(True, linestyle=':', alpha=0.4)

plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8.5, frameon=True)
plt.tight_layout()

# Retenção estrita e bloqueante da janela no Windows
plt.show(block=True)